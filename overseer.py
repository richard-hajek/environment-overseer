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
path_status = f"{path_home}/status"
path_timers = f"{path_home}/timers"
path_reverse_timers = f"{path_home}/rev_timers"
path_scripts_enable = f"{path_home}/exec/enable"
path_scripts_disable = f"{path_home}/exec/disable"
path_scripts_status = f"{path_home}/exec/status"
path_scripts_trackers = f"{path_home}/exec/trackers"
path_pid = f"/run/overseer.pid"
reset_phrase = "I am an addicted idiot and need to reset the timers."
phrase_override_env = "OVERSEER_PHRASE_OVERRIDE"


def sigusr(_, __):
    bump()


def sigusr2(_, __):
    reset_timers()


def link_enable(act_name):
    if not os.path.islink(f"{path_status}/{act_name}"):
        os.symlink(f"{path_definitions}/{act_name}", f"{path_status}/{act_name}")


def link_disable(act_name):
    if os.path.islink(f"{path_status}/{act_name}"):
        os.remove(f"{path_status}/{act_name}")


def reset_timers():
    for name in os.listdir(f"{path_timers}"):
        os.remove(f"{path_timers}/{name}")

    for name in os.listdir(f"{path_status}"):
        os.remove(f"{path_status}/{name}")
        run_disable(name)

    for activity in os.listdir(f"{path_definitions}"):
        name = activity.split(".")[0]
        update_time(name, 0)

    bump()


def bump(force_run=False):
    """
    Searches for newly enabled / disabled activities
    Searches for activities which ran out of time

    Updates files for usage activities

    :param force_run: Forces bump to run disable or enable scripts of all activities
    """

    global bumped_at
    global last_bump_active_names

    # --------------------------------------------
    # - PRELIMINARY TIMER PREPARATIONS           -
    # --------------------------------------------
    for event in timer.queue:  # Remove any interfering bumps
        timer.cancel(event)

    print("----Bumping----")
    create_all_records()

    activities = parse_activities()

    directory_active = [activities[act_path.split(".")[0]] for act_path in os.listdir(path_status)]
    to_enable = []  # Were disabled, now are enabled
    to_disable = []  # Were enabled, now are disabled

    # --------------------------------------------
    # - FIND NEWLY ENABLED / DISABLED ACTIVITIES -
    # --------------------------------------------

    for activity in directory_active:
        if not last_bump_active_names.__contains__(activity["name"]):
            to_enable.append(activity)

    for act_name in last_bump_active_names:
        activity = activities[act_name]
        if not directory_active.__contains__(activity):
            to_disable.append(activity)

    # --------------------------------------------
    # - FIND ACTIVITIES SCHEDULED START / STOP   -
    # --------------------------------------------

    prev_time = datetime.datetime.fromtimestamp(bumped_at).time()
    now_time = datetime.datetime.now().time()

    for activity in activities.values():

        if not activity.__contains__("AutoStart"):
            continue

        start_time = datetime.datetime.strptime(activity["AutoStart"], "%H:%M").time()

        if prev_time < start_time <= now_time:
            if not directory_active.__contains__(activity):
                to_enable.append(activity)

    for activity in activities.values():

        if not activity.__contains__("AutoStop"):
            continue

        stop_time = datetime.datetime.strptime(activity["AutoStop"], "%H:%M").time()
        if prev_time < stop_time <= now_time:
            if not directory_active.__contains__(activity):
                to_enable.append(activity)

    # -----------------------------------------------------------------
    # - CHECK STATUS SCRIPTS -> FIND IF ANY ACTIVS. STOPPED / STARTED -
    # -----------------------------------------------------------------

    for activity in activities.values():

        if status_script_exists(activity):

            activity_real_status = status_script_run(activity)

            if directory_active.__contains__(activity):
                if not activity_real_status:
                    to_enable.append(activity)
            else:
                if activity_real_status:
                    to_disable.append(activity)

    # --------------------------------------------
    # - CALCULATING NEW TIMES                    -
    # --------------------------------------------

    time_passed = time.time() - bumped_at
    for act_name in last_bump_active_names:
        activity_time = get_activity_time(act_name) + time_passed
        update_time(act_name, activity_time)

    for activity in activities.values():

        if not activity.__contains__("Limit"):
            continue

        act_name = activity["name"]
        activity_time = get_activity_time(act_name)

        time_left = activity["Limit"] - activity_time

        if time_left <= 0:
            time_left = 0

        update_rev_time(act_name, time_left)

        if time_left == 0:
            to_disable.append(activity)

    bumped_at = time.time()

    # --------------------------------------------
    # - RUNNING ENABLE / DISABLE SCRIPTS         -
    # --------------------------------------------

    # Remove duplicates
    # Add forced runs
    for activity in activities.values():
        if to_enable.__contains__(activity) and to_disable.__contains__(activity):
            to_enable.remove(activity)
            to_disable.remove(activity)

    if force_run:
        for activity in activities.values():
            if directory_active.__contains__(activity) and not to_enable.__contains__(activity):
                to_enable.append(activity)
            if not directory_active.__contains__(activity) and not to_disable.__contains__(activity):
                to_disable.append(activity)

    for activity in to_enable:
        run_enable(activity["name"])
        link_enable(activity["name"])

        if not directory_active.__contains__(activity):
            directory_active.append(activity)

    for activity in to_disable:
        run_disable(activity["name"])
        link_disable(activity["name"])

        if directory_active.__contains__(activity):
            directory_active.remove(activity)

    # --------------------------------------------
    # - EXECUTE TRACKERS                         -
    # --------------------------------------------

    for tracker in os.listdir(path_scripts_trackers):
        os.system(f"{path_scripts_trackers}/{tracker}")

    # --------------------------------------------
    # - SCHEDULING NEXT BUMP                     -
    # --------------------------------------------

    last_bump_active_names = [activity["name"] for activity in directory_active]

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


def status_script_exists(act_name):
    return os.listdir(path_scripts_status).__contains__(act_name)


def status_script_run(act_name):
    script = subprocess.run(f"{path_scripts_status}/{act_name}", stdout=subprocess.PIPE)
    return script.returncode != 0


def activity_exists(act_name):
    return os.path.isfile(f"{path_definitions}/{act_name}.json")


def get_activity_time(act_name):
    path = f"{path_timers}/{act_name}"
    with open(path, 'r') as content_file:
        time_spent = content_file.read()
    time_spent = float(time_spent)
    return time_spent


def create_all_records():
    for activity in os.listdir(path_definitions):
        activity = activity.split('.')[0]
        create_record_if_non_existent(activity)


def create_record_if_non_existent(act_name):
    path = f"{path_timers}/{act_name}"

    if os.path.isfile(path):
        return

    with open(path, 'w') as content_file:
        content_file.write('0')


def update_time(act_name, seconds):
    with open(f"{path_timers}/{act_name}", 'w') as file:
        file.write(str(int(seconds)))


def update_rev_time(act_name, seconds):
    with open(f"{path_reverse_timers}/{act_name}", 'w') as file:
        file.write(str(int(seconds)))


def create_folders_if_non_existent():
    if not os.path.isdir(path_home):
        os.makedirs(path_home)
    if not os.path.isdir(path_definitions):
        os.makedirs(path_definitions)
    if not os.path.isdir(path_status):
        os.makedirs(path_status)
    if not os.path.isdir(path_timers):
        os.makedirs(path_timers)
    if not os.path.isdir(path_reverse_timers):
        os.makedirs(path_reverse_timers)
    if not os.path.isdir(path_scripts_enable):
        os.makedirs(path_scripts_enable)
    if not os.path.isdir(path_scripts_disable):
        os.makedirs(path_scripts_disable)
    if not os.path.isdir(path_scripts_status):
        os.makedirs(path_scripts_status)
    if not os.path.isdir(path_scripts_trackers):
        os.makedirs(path_scripts_trackers)


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
    bumped_at = time.time()
    timer = sched.scheduler(time.time, time.sleep)

    parser = argparse.ArgumentParser(description="Controls the environment overseer")
    parser.add_argument('-e', '--enable', nargs='+', help='Enables an activity')
    parser.add_argument('-d', '--disable', nargs='+', help='Disables an activity')
    parser.add_argument('-l', '--list', action='store_true', help='List usage activities')
    parser.add_argument('-r', '--reset', action='store_true', help='Reset all timers and disables everything')
    parser.add_argument('-c', '--create', action='store_true', help='Creates the file structure')
    parser.add_argument('-b', '--bump', action='store_true', help='Bumps the daemon')
    parser.epilog = "Exit Codes: " + " ".join([f"{exit_codes[pair][0]}:{exit_codes[pair][1]}" for pair in exit_codes])
    args = parser.parse_args()

    start_daemon = not args.enable and \
                   not args.disable and \
                   not args.reset and \
                   not args.list and \
                   not args.create and \
                   not args.bump

    if args.list:
        activities = parse_activities()
        enabled = os.listdir(path_status)

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

    if args.create:
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
        bump(force_run=True)
        with open(path_pid, "w") as pidf:
            pidf.write(str(os.getpid()))
            pidf.close()
        timer.run()
