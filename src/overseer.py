#!/usr/bin/python

import argparse
import os
import sched
import signal
import time
import psutil
import json
import datetime


def die(reason):
    print(exit_codes[reason][1])
    exit(exit_codes[reason][0])


class STATUS:
    ENABLED = "enabled"
    DISABLED = "disabled"
    READY = "ready"


class ACTION:
    IDLE = "idle"
    ENABLE = "enable"
    DISABLE = "disable"


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
path_scripts_checks = f"{path_home}/scripts/checks"

path_scripts_extensions = f"{path_home}/scripts/extensions"

path_pid = f"/run/overseer.pid"

reset_phrase = "I am an addicted idiot and need to reset the trackers."
phrase_override_env = "OVERSEER_PHRASE_OVERRIDE"


def sigusr(_, __):
    bump()


def sigusr2(_, __):
    reset_timers()


def sigterm(_, __):  # Disable all activities prior to shutdown
    for name in os.listdir(f"{path_enabled}"):
        os.remove(f"{path_enabled}/{name}")

    bump()


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

    # --------------------------------------------
    # - PRELIMINARY TIMER PREPARATIONS           -
    # --------------------------------------------
    print("----Bumping----")
    create_all_records()
    for event in timer.queue:  # Remove any interfering bumps
        timer.cancel(event)

    activities = parse_activities()
    prev_time = int(bumped_at)
    now_time = int(time.time())

    for activity in activities.values():

        # --------------------------------------------
        # - COLLECT ALL DATA ABOUT AN ACTIVITY       -
        # --------------------------------------------

        activity_name = activity["name"]

        first_run = False

        if last_states.__contains__(activity_name):
            previous_state = last_states[activity_name]
        else:
            first_run = True
            previous_state = STATUS.DISABLED

        if os.path.isfile(f"{path_scripts_checks}/{activity_name}"):
            check_return_code = run_script(f"{path_scripts_checks}/{activity_name}")

            if check_return_code == 0:
                previous_state = STATUS.ENABLED
            elif check_return_code == 1:
                previous_state = STATUS.DISABLED

        decisions = []
        activity_time = get_activity_time(activity_name)
        limit = None

        if activity.__contains__("Limit"):
            limit = activity["Limit"]

        recharge_time = None

        if activity.__contains__("Recharge"):
            recharge_time = activity["Limit"]

        link_enabled = os.path.islink(f"{path_enabled}/{activity_name}")

        manager_return_code = None
        if os.path.isfile(f"{path_scripts_managers}/{activity_name}"):
            manager_return_code = run_script(f"{path_scripts_managers}/{activity_name}")

        auto_start = None
        if activity.__contains__("AutoStart"):
            auto_start = activity["AutoStart"]

        auto_stop = None
        if activity.__contains__("AutoStop"):
            auto_stop = activity["AutoStop"]

        # --------------------------------------------
        # - PROCESS THE ACTIVITY                     -
        # --------------------------------------------

        decision, current_state, decisions, new_activity_time = process_activity(prev_time, now_time, previous_state,
                                                                                 activity_time, limit, recharge_time,
                                                                                 link_enabled, decisions,
                                                                                 manager_return_code, auto_start,
                                                                                 auto_stop, first_run)

        # Update time
        if new_activity_time != activity_time:
            update_time(activity_name, new_activity_time)
            time_left = limit - activity_time
            update_rev_time(activity_name, time_left)

        # Run enable / disable scripts
        if decision == ACTION.ENABLE:
            run_enable(activity_name)
        elif decision == ACTION.DISABLE:
            run_disable(activity_name)
        elif decision == ACTION.IDLE:
            pass

        # Update links
        if current_state == STATUS.ENABLED:
            link_enable(activity_name)
        elif current_state == STATUS.DISABLED:
            link_disable(activity_name)
        elif current_state == STATUS.READY:
            link_ready(activity_name)

        # Print status
        print(f"[STATUS] {activity_name}", end=" ")

        if current_state == previous_state:
            print(f"stayed in {current_state} state", end=", ")
        else:
            print(f"changed from {previous_state} to {current_state}", end=", ")

        print(f"decisions based on: {', '.join(decisions)}", end="\n\n")

        last_states[activity_name] = current_state

    # --------------------------------------------
    # - EXECUTE EXTENSIONS                       -
    # --------------------------------------------

    for extension in os.listdir(path_scripts_extensions):
        code = os.system(f"{path_scripts_extensions}/{extension} > /dev/null 2>&1")
        code = int(int(code) / 256)
        print(f"[EXTENSION] {extension} returned {code}")

    # --------------------------------------------
    # - PREPARE FOR NEXT BUMP                    -
    # --------------------------------------------

    bumped_at = time.time()
    next_bump = 60
    print(f"Scheduling next bump in {next_bump} seconds")
    timer.enter(next_bump, 1, bump)


def process_activity(previous_time, current_time, previous_status, activity_time, limit, recharge_time, link_enabled,
                     decisions, manager_return_code=None, auto_start=None, auto_stop=None, first_run=False):

    current_status = STATUS.DISABLED
    decisions.append("DISABLE (default)")

    if link_enabled:
        current_status = STATUS.ENABLED
        decisions.append("ENABLE (File link)")

    # --------------------------------------------
    # - CHECK IF ACTIVITY HAS A SCHEDULED ACTION -
    # --------------------------------------------

    if auto_start is not None:
        if process_auto_trigger(previous_time, current_time, auto_start):
            current_status = STATUS.ENABLED
            decisions.append("ENABLE (AutoStart)")

    if auto_stop is not None:
        if process_auto_trigger(previous_time, current_time, auto_stop):
            current_status = STATUS.DISABLED
            decisions.append("DISABLE (AutoStop)")

    # --------------------------------------------
    # - CHECK ACTIVITY MANAGER                   -
    # --------------------------------------------

    if manager_return_code is not None:
        if manager_return_code == 0:
            current_status = STATUS.ENABLED
            decisions.append("ENABLE (Manager script)")
        elif manager_return_code == 1:
            current_status = STATUS.READY
            decisions.append("READY (Manager script)")

    # --------------------------------------------
    # - CHECK ACTIVITY LIMIT                     -
    # --------------------------------------------

    if limit is not None:
        activity_time, activity_still_available = process_limit(current_time - previous_time, activity_time, limit,
                                                                current_status)

        if not activity_still_available:
            current_status = STATUS.DISABLED
            decisions.append("DISABLE (Limit)")

    # --------------------------------------------
    # - CHECK ACTIVITY RECHARGE                  -
    # --------------------------------------------

    if limit is not None and recharge_time is not None:
        activity_time = process_recharge(current_time - previous_time, current_status, activity_time, recharge_time, limit)

    # --------------------------------------------
    # - PROCESS DECISIONS & RETURN RESULTS       -
    # --------------------------------------------

    decision = process_decision(current_status, previous_status, first_run)
    return decision, current_status, decisions, activity_time


def process_auto_trigger(previous_time, current_time, trigger_at):
    trigger_time = datetime.datetime.strptime(trigger_at, "%H:%M").time()

    if previous_time < trigger_time <= current_time:
        return True
    return False


def process_limit(time_delta, activity_time, limit, current_status):
    if current_status == STATUS.ENABLED:
        activity_time = activity_time + time_delta

    if activity_time >= limit:
        activity_time = limit
        return activity_time, False

    return activity_time, True


def process_recharge(time_delta, current_status, activity_time, recharge_time, limit):
    if current_status == STATUS.ENABLED:
        return 0

    recharge = 1 / recharge_time * time_delta * limit
    recharge = int(recharge)
    
    activity_time -= recharge

    if activity_time <= 0:
        activity_time = 0

    return activity_time


def process_decision(current_status, previous_status, first_run):
    if current_status == STATUS.ENABLED and previous_status == STATUS.DISABLED:
        return ACTION.ENABLE

    elif current_status == STATUS.READY and previous_status == STATUS.DISABLED:
        return ACTION.ENABLE

    elif current_status == STATUS.DISABLED and previous_status != STATUS.DISABLED:
        return ACTION.DISABLE

    elif first_run:
        if current_status == STATUS.ENABLED or current_status == STATUS.READY:
            return ACTION.ENABLE
        elif current_status == STATUS.DISABLED:
            return ACTION.DISABLE

    return ACTION.IDLE


def parse_activities():
    names = os.listdir(path_definitions)
    activities = {}

    for name in names:
        with open(f"{path_definitions}/{name}", 'r') as f:
            activity = json.load(f)

        activity["name"] = name.split(".")[0]
        activities[activity['name']] = activity

    for activity in activities.values():

        if activity.__contains__("Limit"):
            limit_raw = activity["Limit"]
            limit = parse_time(limit_raw, activity["name"])
            activity["Limit"] = limit

        if activity.__contains__("Recharge"):
            recharge_raw = activity["Recharge"]
            recharge = parse_time(recharge_raw, activity["name"])
            activity["Recharge"] = recharge

    return activities


def parse_time(time_raw, act_name):
    time_parsed = 0
    unit = ''
    time = 0

    try:
        time = int(time_raw[:-1])
        unit = time_raw[-1:]
    except ValueError:
        print(f'Could not parse time "{time_raw}" of activity {act_name}')
        die("misconfiguration")

    if unit.lower() == 'h':
        time_parsed = time * 3600
    elif unit.lower() == 'm':
        time_parsed = time * 60
    elif unit.lower() == 's':
        time_parsed = time
    else:
        print(f"Unknown time unit '{unit}' in activity {act_name}")
        die("misconfiguration")

    return time_parsed


def run_enable(act_name):
    code = os.system(f"{path_scripts_enable}/{act_name} > /dev/null 2>&1")
    code = int(int(code) / 256)
    print(f"[ENABLE] {act_name}, returned {code}")


def run_disable(act_name):
    code = os.system(f"{path_scripts_disable}/{act_name} > /dev/null 2>&1")
    code = int(int(code) / 256)
    print(f"[DISABLE] {act_name}, returned {code}")


def run_script(script_path):
    code = os.system(f"{script_path} > /dev/null 2>&1")
    code = int(int(code) / 256)
    print(f"[SCRIPT] {script_path}, returned {code}")
    return code


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
    if not os.path.isdir(path_scripts_checks):
        os.makedirs(path_scripts_checks)
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

    last_states = {}

    bumped_at = int(time.time())
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
        ready = os.listdir(path_ready)

        if activities.__len__() == 0:
            print("No currently configured activities! See README.md for guide")

        for ls_activity in activities.values():
            print(ls_activity["name"], end='\t')
            if enabled.__contains__(ls_activity["name"]):
                print("Enabled!", end='\t')
            elif ready.__contains__(ls_activity["name"]):
                print("Standby!", end='\t')
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

                if os.path.isfile(f"{path_scripts_managers}/{a}"):
                    print(f"Activity {a} is managed by {path_scripts_managers}/{a}, "
                          "your decision to enable it will be overridden in around a minute.")

            else:
                print(f"Did not find '{a}' activity")
        remote_bump()

    if args.disable:
        print("Disabling activities...")
        os.chdir(path_home)
        for a in args.disable:
            if activity_exists(a):
                link_disable(a)

                if os.path.isfile(f"{path_scripts_managers}/{a}"):
                    print(f"Activity {a} is managed by {path_scripts_managers}/{a}, "
                          "your decision to disable it will be overridden in around a minute.")

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
        signal.signal(signal.SIGTERM, sigterm)
        bump()
        with open(path_pid, "w") as pidf:
            pidf.write(str(os.getpid()))
            pidf.close()
        timer.run()
