#!/usr/bin/python

import argparse
import os
import sched
import signal
import time
import psutil
import json
import datetime
import subprocess


def die(reason):
    print(exit_codes[reason][1])
    exit(exit_codes[reason][0])


class STATUS:
    ENABLED = "enabled"
    DISABLED = "disabled"
    READY = "ready"


# --------------------------------------------
# - DEFINE APP VARIABLES                     -
# --------------------------------------------

exit_codes = {
    "success": (0, "Success"),
    "daemon_running": (1, "Daemon is running"),
    "daemon_not_running": (2, "Daemon is not running"),
    "root": (3, "Must be ran as root"),
    "misconfiguration": (4, "Overseer is misconfigured")
}

path_home = "/etc/overseer"

path_definitions = f"{path_home}/activities"
path_enabled = f"{path_home}/enabled"
path_ready = f"{path_home}/ready"
path_trackers = f"{path_home}/trackers"
path_reverse_trackers = f"{path_home}/reverse-trackers"

path_scripts_enable = f"{path_home}/scripts/enable"
path_scripts_disable = f"{path_home}/scripts/disable"
path_scripts_managers = f"{path_home}/scripts/managers"

path_scripts_extensions = f"{path_home}/scripts/extensions"

path_pid = f"/run/overseer.pid"

reset_phrase = "I am an addicted idiot and need to reset the timers."
phrase_override_env = "OVERSEER_PHRASE_OVERRIDE"


def sigusr(_, __):
    bump()


def sigusr2(_, __):
    reset_timers()


def link_enable(act_name):
    if not os.path.islink(f"{path_enabled}/{act_name}"):
        os.symlink(f"{path_definitions}/{act_name}.json", f"{path_enabled}/{act_name}")

    if os.path.islink(f"{path_ready}/{act_name}"):
        os.remove(f"{path_ready}/{act_name}")


def link_disable(act_name):
    if os.path.islink(f"{path_enabled}/{act_name}"):
        os.remove(f"{path_enabled}/{act_name}")

    if os.path.islink(f"{path_ready}/{act_name}"):
        os.remove(f"{path_ready}/{act_name}")


def link_ready(act_name):
    if not os.path.islink(f"{path_ready}/{act_name}"):
        os.symlink(f"{path_definitions}/{act_name}.json", f"{path_ready}/{act_name}")

    if os.path.islink(f"{path_enabled}/{act_name}"):
        os.remove(f"{path_enabled}/{act_name}")


def reset_timers():
    for name in os.listdir(f"{path_trackers}"):
        os.remove(f"{path_trackers}/{name}")

    for name in os.listdir(f"{path_enabled}"):
        os.remove(f"{path_enabled}/{name}")
        run_disable(name)

    for activity in os.listdir(f"{path_definitions}"):
        name = activity.split(".")[0]
        update_time(name, 0)

    bump()


def bump():
    global bumped_at
    global last_states
    global last_bump_active_names

    # --------------------------------------------
    # - PRELIMINARY TIMER PREPARATIONS           -
    # --------------------------------------------
    for event in timer.queue:  # Remove any interfering bumps
        timer.cancel(event)

    print("----Bumping----")
    create_all_records()

    activities = parse_activities()
    enabled_directory = os.listdir(path_enabled)
    semi_enabled_directory = os.listdir(path_ready)

    prev_time = datetime.datetime.fromtimestamp(bumped_at).time()
    now_time = datetime.datetime.now().time()
    time_passed = time.time() - bumped_at

    for activity in activities.values():

        activity_name = activity["name"]

        if last_states.__contains__(activity_name):
            previous_state = last_states[activity_name]
        else:
            run_disable(activity_name)
            previous_state = STATUS.DISABLED

        current_state = STATUS.DISABLED

        # --------------------------------------------
        # - CHECK IF ENABLED / SEMI ENABLED          -
        # --------------------------------------------
        if enabled_directory.__contains__(activity_name):
            current_state = STATUS.ENABLED

        if semi_enabled_directory.__contains__(activity_name):
            current_state = STATUS.READY

        # --------------------------------------------
        # - CHECK IF ACTIVITY HAS A SCHEDULED ACTION -
        # --------------------------------------------

        if activity.__contains__("AutoStart"):
            start_time = datetime.datetime.strptime(activity["AutoStart"], "%H:%M").time()

            if prev_time < start_time <= now_time:
                current_state = STATUS.ENABLED

        if activity.__contains__("AutoStop"):
            stop_time = datetime.datetime.strptime(activity["AutoStop"], "%H:%M").time()

            if prev_time < stop_time <= now_time:
                current_state = STATUS.DISABLED

        # --------------------------------------------
        # - CHECK ACTIVITY MANAGER                   -
        # --------------------------------------------

        if os.path.isfile(f"{path_scripts_managers}/{activity_name}"):
            path = f"{path_scripts_managers}/{activity_name}"
            result = run_script(path)

            if result == 0:
                current_state = STATUS.ENABLED
            elif result == 1:
                current_state = STATUS.READY

        # --------------------------------------------
        # - CHECK ACTIVITY LIMIT                     -
        # --------------------------------------------

        activity_time = get_activity_time(activity_name) + time_passed
        update_time(activity_name, activity_time)

        if activity.__contains__("Limit"):
            time_left = activity["Limit"] - activity_time

            if time_left <= 0:
                time_left = 0

            update_rev_time(activity_name, time_left)

            if time_left == 0:
                current_state = STATUS.DISABLED

        if current_state == STATUS.ENABLED and previous_state == STATUS.DISABLED:
            run_enable(activity_name)

        elif current_state == STATUS.READY and previous_state == STATUS.DISABLED:
            run_enable(activity_name)

        elif current_state == STATUS.DISABLED and previous_state != STATUS.DISABLED:
            run_disable(activity_name)

        if current_state == STATUS.ENABLED:
            link_enable(activity_name)

        if current_state == STATUS.READY:
            link_ready(activity_name)

        if current_state == STATUS.DISABLED:
            link_disable(activity_name)

        last_states[activity_name] = current_state

    # --------------------------------------------
    # - EXECUTE EXTENSIONS                       -
    # --------------------------------------------

    for extension in os.listdir(path_scripts_extensions):
        os.system(f"{path_scripts_extensions}/{extension}")

    # --------------------------------------------
    # - PREPARE FOR NEXT BUMP                    -
    # --------------------------------------------

    bumped_at = time.time()
    next_bump = 60
    print(f"Scheduling next bump in {next_bump} seconds")
    timer.enter(next_bump, 1, bump)


def parse_activities():
    names = os.listdir(path_definitions)
    activities = {}
    for name in names:
        with open(f"{path_definitions}/{name}", 'r') as f:
            activity = json.load(f)
        activity["name"] = name.split(".")[0]
        activities[activity['name']] = activity

    for activity in activities.values():
        limit_raw = activity["Limit"]
        limit = 0

        try:
            limit = int(limit_raw[:-1])
        except ValueError:
            print(f"Could not parse limit \"{limit_raw}\" of activity {activity['name']}")
            die("misconfiguration")

        unit = limit_raw[-1:]

        if unit.lower() == 'h':
            limit = limit * 3600
        elif unit.lower() == 'm':
            limit = limit * 60
        elif unit.lower() == 's':
            limit = limit
        else:
            print(f"Unknown time unit '{unit}' in activity {activity['name']}")
            die("misconfiguration")

        activity["Limit"] = limit

    return activities


def run_enable(act_name):
    print(f"Running enable for {act_name}")
    os.system(f"{path_scripts_enable}/{act_name}")


def run_disable(act_name):
    print(f"Running disable for {act_name}")
    os.system(f"{path_scripts_disable}/{act_name}")


def run_script(script_path):
    script = subprocess.run(script_path, stdout=subprocess.PIPE)
    return script.returncode


def activity_exists(act_name):
    return os.path.isfile(f"{path_definitions}/{act_name}.json")


def get_activity_time(act_name):
    path = f"{path_trackers}/{act_name}"
    with open(path, 'r') as content_file:
        time_spent = content_file.read()
    time_spent = float(time_spent)
    return time_spent


def create_all_records():
    for activity in os.listdir(path_definitions):
        activity = activity.split('.')[0]
        create_record_if_non_existent(activity)


def create_record_if_non_existent(act_name):
    path = f"{path_trackers}/{act_name}"

    if os.path.isfile(path):
        return

    with open(path, 'w') as content_file:
        content_file.write('0')


def update_time(act_name, seconds):
    with open(f"{path_trackers}/{act_name}", 'w') as file:
        file.write(str(int(seconds)))


def update_rev_time(act_name, seconds):
    with open(f"{path_reverse_trackers}/{act_name}", 'w') as file:
        file.write(str(int(seconds)))


def create_folders_if_non_existent():
    if not os.path.isdir(path_home):
        os.makedirs(path_home)
    if not os.path.isdir(path_definitions):
        os.makedirs(path_definitions)
    if not os.path.isdir(path_enabled):
        os.makedirs(path_enabled)
    if not os.path.isdir(path_ready):
        os.makedirs(path_ready)
    if not os.path.isdir(path_trackers):
        os.makedirs(path_trackers)
    if not os.path.isdir(path_reverse_trackers):
        os.makedirs(path_reverse_trackers)
    if not os.path.isdir(path_scripts_enable):
        os.makedirs(path_scripts_enable)
    if not os.path.isdir(path_scripts_disable):
        os.makedirs(path_scripts_disable)
    if not os.path.isdir(path_scripts_managers):
        os.makedirs(path_scripts_managers)
    if not os.path.isdir(path_scripts_extensions):
        os.makedirs(path_scripts_extensions)


def remote_bump():
    with open(path_pid, 'r') as content_file:
        pid = content_file.read()
        pid = int(pid)
        os.kill(pid, signal.SIGUSR1)


def remote_reset():
    with open(path_pid, 'r') as content_file:
        pid = content_file.read()
        pid = int(pid)
        os.kill(pid, signal.SIGUSR2)


def is_daemon_running():
    if not os.path.isfile(path_pid):
        return False

    with open(path_pid, 'r') as content_file:
        pid = content_file.read()
        pid = int(pid)

        if psutil.pid_exists(pid):
            return True
        else:
            return False


def is_privileged():
    return os.getuid() == 0


if __name__ == "__main__":

    last_bump_active_names = []

    last_states = {}

    bumped_at = time.time()
    timer = sched.scheduler(time.time, time.sleep)

    parser = argparse.ArgumentParser(description="Controls the environment overseer")
    parser.add_argument('-e', '--enable', nargs='+', help='Enables an activity')
    parser.add_argument('-d', '--disable', nargs='+', help='Disables an activity')
    parser.add_argument('-l', '--list', action='store_true', help='List usage activities')
    parser.add_argument('-r', '--reset', action='store_true', help='Reset all timers and disables everything')
    parser.add_argument('-p', '--prepare', action='store_true', help='Prepares the file structure')
    parser.add_argument('-b', '--bump', action='store_true', help='Bumps the daemon')
    parser.epilog = "Exit Codes: " + " ".join([f"{exit_codes[pair][0]}:{exit_codes[pair][1]}" for pair in exit_codes])
    args = parser.parse_args()

    start_daemon = not args.enable and \
                   not args.disable and \
                   not args.reset and \
                   not args.list and \
                   not args.prepare and \
                   not args.bump

    if args.list:
        activities = parse_activities()
        enabled = os.listdir(path_enabled)

        if activities.__len__() == 0:
            print("No currently configured activities! See README.md for guide")

        for ls_activity in activities.values():
            print(ls_activity["name"], end='\t')
            if enabled.__contains__(ls_activity["name"]):
                print("Enabled!", end='\t')
            else:
                print("Disabled", end='\t')

            print(datetime.timedelta(seconds=get_activity_time(ls_activity["name"])), end='\t')
            print("out of", end='\t')
            print(datetime.timedelta(seconds=ls_activity["Limit"]), end='\t')

            print()
        exit(0)

    if args.prepare:
        print(f"Creating folder structure in {path_home}")
        create_folders_if_non_existent()
        exit(0)

    if start_daemon and is_daemon_running():
        die("daemon_running")

    if not is_privileged():
        die("root")

    if not start_daemon and not is_daemon_running():
        die("daemon_not_running")

    if args.bump:
        print("Bumping daemon...")
        remote_bump()

    if args.reset:

        if os.environ.__contains__(phrase_override_env):
            print("Resetting limits...")
            remote_reset()
            exit(0)

        print(f"Please type: \"{reset_phrase}\"")
        phrase = input()

        if phrase == reset_phrase:
            print("Resetting limits...")
            remote_reset()
        else:
            print("Failed to type the phrase correctly!")

    if args.enable:
        print("Enabling activities...")
        os.chdir(path_home)
        for a in args.enable:
            if activity_exists(a):
                link_enable(a)
            else:
                print(f"Did not find '{a}' activity")
        remote_bump()

    if args.disable:
        print("Disabling activities...")
        os.chdir(path_home)
        for a in args.disable:
            if activity_exists(a):
                link_disable(a)
            else:
                print(f"Did not find '{a}' activity")
        remote_bump()

    if start_daemon:
        print("Starting as daemon...")
        create_folders_if_non_existent()
        os.chdir(path_home)
        create_all_records()

        signal.signal(signal.SIGUSR1, sigusr)
        signal.signal(signal.SIGUSR2, sigusr2)
        bump()
        with open(path_pid, "w") as pidf:
            pidf.write(str(os.getpid()))
            pidf.close()
        timer.run()