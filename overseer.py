#!/usr/bin/python

import argparse
import itertools
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


parser = argparse.ArgumentParser(description="Controls the environment overseer")
parser.add_argument('-e', '--enable', nargs='+', help='Enables an activity')
parser.add_argument('-d', '--disable', nargs='+', help='Disables an activity')
parser.add_argument('-l', '--list', action='store_true', help='List usage activities')
parser.add_argument('-r', '--reset', action='store_true', help='Reset all timers')
parser.add_argument('-p', '--prepare', action='store_true', help='Prepares file structure')

exit_codes = {
    "success": (0, "Success"),
    "daemon_running": (1, "Daemon is running"),
    "daemon_not_running": (2, "Daemon is not running"),
    "root": (3, "Must be ran as root"),
    "misconfiguration": (4, "Overseer is misconfigured")
}

parser.epilog = "Exit Codes: " + " ".join([f"{exit_codes[pair][0]}:{exit_codes[pair][1]}" for pair in exit_codes])

args = parser.parse_args()

enabled_activities = []
bumped_at = time.time()
timer = sched.scheduler(time.time, time.sleep)

path_home = "/etc/overseer"

path_definitions = f"{path_home}/activities"  # Stores activity definitions
path_status = f"{path_home}/status"  # Stores which activities are currently used, contains symlinks to path_activities
path_timers = f"{path_home}/timers"  # Stores activity usage times

path_scripts_enable = f"{path_home}/exec/enable"
path_scripts_disable = f"{path_home}/exec/disable"
path_scripts_status = f"{path_home}/exec/status"

path_pid = f"/run/overseer.pid"


def sigusr(_, __):
    bump()


def sigusr2(_, __):
    reset_timers()


def link_enable(name):
    if not os.path.islink(f"{path_status}/{name}"):
        os.symlink(f"{path_definitions}/{name}", f"{path_status}/{name}")


def link_disable(name):
    if os.path.islink(f"{path_status}/{name}"):
        os.remove(f"{path_status}/{name}")


def reset_timers():
    for name in os.listdir(f"{path_timers}"):
        os.remove(f"{path_timers}/{name}")

    for name in os.listdir(f"{path_status}"):
        os.remove(f"{path_status}/{name}")
        run_disable(name)

    for name in os.listdir(f"{path_definitions}"):
        update_time(name, 0)


def bump(force_run=False):
    """
    Searches for newly enabled / disabled activities
    Searches for activities which ran out of time

    Updates files for usage activities

    :param force_run: Forces bump to run disable or enable scripts of all activities
    """

    global bumped_at

    # --------------------------------------------
    # - PRELIMINARY TIMER PREPARATIONS           -
    # --------------------------------------------
    for event in timer.queue:  # Remove any interfering bumps
        timer.cancel(event)

    print("----Bumping----")
    create_all_records()

    activities = parse_activities()

    names_active = os.listdir(path_status)
    names_just_enabled = []
    names_just_disabled = []

    # --------------------------------------------
    # - FIND NEWLY ENABLED / DISABLED ACTIVITIES -
    # --------------------------------------------
    for activity_name in names_active:
        if not enabled_activities.__contains__(activity_name):
            names_just_enabled.append(activity_name)
            enabled_activities.append(activity_name)

    for activity in enabled_activities:
        if not names_active.__contains__(activity["name"]):
            names_just_disabled.append(activity["name"])
            enabled_activities.remove(activity)

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
            if not enabled_activities.__contains__(activity):
                names_just_enabled.append(activity)

    for activity in activities.values():

        if not activity.__contains__("AutoStop"):
            continue

        stop_time = datetime.datetime.strptime(activity["AutoStop"], "%H:%M").time()
        if prev_time < stop_time <= now_time:
            if enabled_activities.__contains__(activity):
                names_just_disabled.append(activity)

    # -----------------------------------------------------------------
    # - CHECK STATUS SCRIPTS -> FIND IF ANY ACTIVS. STOPPED / STARTED -
    # -----------------------------------------------------------------

    for activity in activities.values():

        if status_script_exists(activity):

            activity_status = status_script_run(activity)

            if enabled_activities.__contains__(activity):
                if not activity_status:
                    names_just_enabled.append(activity)
            else:
                if activity_status:
                    names_just_disabled.append(activity)

    # --------------------------------------------
    # - CALCULATING NEW TIMES                    -
    # --------------------------------------------

    time_passed = time.time() - bumped_at
    for activity in itertools.chain(enabled_activities, names_just_disabled):

        if activity is str:
            activity = activities[activity]

        if names_just_enabled.__contains__(activity["name"]):
            continue

        activity_time = get_activity_time(activity) + time_passed
        update_time(activity, activity_time)

    for activity in enabled_activities:
        if activity["Limit"] != 0 and get_activity_time(activity) > activity["Limit"]:
            names_just_disabled.append(activity["name"])
            enabled_activities.remove(activity)

    bumped_at = time.time()

    # --------------------------------------------
    # - RUNNING ENABLE / DISABLE SCRIPTS         -
    # --------------------------------------------
    for activity in activities:
        act_name = activity["name"]
        if names_just_enabled.__contains__(act_name) and names_just_disabled.__contains__(act_name):
            names_just_enabled.remove(act_name)
            names_just_disabled.remove(act_name)
        if not names_just_enabled.__contains__(act_name) and not names_just_disabled.__contains__(act_name) and force_run:
            names_just_disabled.append(act_name)

    for activity in names_just_enabled:
        run_enable(activities[activity])
        link_enable(activities[activity])

    for activity in names_just_disabled:
        run_enable(activities[activity])
        link_disable(activities[activity])

    # --------------------------------------------
    # - SCHEDULING NEXT BUMP                     -
    # --------------------------------------------
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


def run_enable(activity):
    activity = activity["name"]
    print(f"Running enable for {activity}")
    os.system(f"{path_scripts_enable}/{activity}")


def run_disable(activity):
    activity = activity["name"]
    print(f"Running disable for {activity}")
    os.system(f"{path_scripts_disable}/{activity}")


def status_script_exists(activity):
    return os.listdir(path_scripts_status).__contains__(activity["name"])


def status_script_run(activity):
    script = subprocess.run(f"{path_scripts_status}/{activity['name']}", stdout=subprocess.PIPE)
    return script.returncode != 0


def activity_exists(activity):
    return os.path.isfile(f"{path_definitions}/{activity}.json")


def get_activity_time(activity):
    path = f"{path_timers}/{activity['name']}"
    with open(path, 'r') as content_file:
        time_spent = content_file.read()
    time_spent = float(time_spent)
    return time_spent


def create_all_records():
    for activity in os.listdir(path_definitions):
        activity = activity.split('.')[0]
        create_record_if_non_existent(activity)


def create_record_if_non_existent(activity):
    path = f"{path_timers}/{activity}"

    if os.path.isfile(path):
        return

    with open(path, 'w') as content_file:
        content_file.write('0')


def update_time(activity, seconds):
    with open(f"{path_timers}/{activity}", 'w') as file:
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
    if not os.path.isdir(path_scripts_enable):
        os.makedirs(path_scripts_enable)
    if not os.path.isdir(path_scripts_disable):
        os.makedirs(path_scripts_disable)
    if not os.path.isdir(path_scripts_status):
        os.makedirs(path_scripts_status)


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
    start_daemon = not args.enable and \
                   not args.disable and \
                   not args.reset and \
                   not args.list and \
                   not args.prepare

    if args.list:
        activities = parse_activities()
        enabled = os.listdir(path_status)

        for ls_activity in activities:
            print(ls_activity["name"], end='\t')
            if enabled.__contains__(ls_activity["name"]):
                print("Enabled", end='\t')
            else:
                print("Disabled", end='\t')
            print("\n")
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

    if args.reset:
        print("Resetting limits...")
        os.chdir(path_home)
        remote_reset()

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
