#!/usr/bin/env python3

import argparse
import datetime as dt
import sched
import signal
import sys
import time

from overseer import utils
from overseer.config import *
from overseer.filesystem import *
from overseer.modules.auto_trigger import AutoTrigger
from overseer.modules.forbid import ForbidActivity
from overseer.modules.forced_activity import ForcedActivity
from overseer.modules.global_forbid import GlobalForbid
from overseer.modules.interrupt import Interrupt
from overseer.modules.limit import Limit
from overseer.modules.manager import Manager
from overseer.modules.pre_check import PreCheck
from overseer.modules.recharge import Recharge
# --------------------------------------------
# - DEFINE APP VARIABLES                     -
# --------------------------------------------
from overseer.resetter import Resetter
from overseer.utils import decide

verbose = False
forbid_reset = False

modules = [
    AutoTrigger(),
    Manager(),
    Limit(),
    ForcedActivity(),
    Interrupt(),
    Recharge(),
    ForbidActivity(),
    GlobalForbid()
]


# --------------------------------------------
# - IPC                                     -
# --------------------------------------------

def remote(n: signal.Signals):
    with open(path_pid, 'r') as content_file:
        pid = content_file.read()
        pid = int(pid)
        os.kill(pid, n)


def remote_tick():
    remote(signal.SIGUSR1)


def remote_reset():
    remote(signal.SIGUSR2)


def sigterm(_, __):  # Disable all activities and shutdown
    for name in os.listdir(f"{path_activity_status}"):
        os.remove(f"{path_activity_status}/{name}")

    tick()
    die("success")


def sigusr(_, __):
    tick()


def sigusr2(_, __):
    global activity_trackers

    if forbid_reset:
        return

    activities = parse_activities()
    [module.reset(activities) for module in modules]
    activity_trackers = {}


def is_busy():
    if not is_daemon_running() or not os.path.isfile(path_busy):
        return False

    with open(path_busy, 'r') as f:
        busy = f.read()
        return busy == "1"


def set_busy(busy: bool):
    with open(path_busy, 'w') as f:
        f.write("1" if busy else "0")


# --------------------------------------------
# - CORE / PROCESSING                        -
# --------------------------------------------

def tick():
    global previous_time
    global previous_states

    set_busy(True)
    create_all_records(path_trackers)
    for event in timer.queue:
        timer.cancel(event)

    activities = parse_activities()

    current_time = int(time.time())
    delta = current_time - previous_time

    if utils.just_happened(previous_time, current_time, "04:00"):
        resetter.write()

    status_printed = False
    for activity in activities.values():

        # --------------------------------------------
        # - PROCESS ACTIVITY                         -
        # --------------------------------------------

        decisions = []
        activity_name = activity["name"]
        previous_state = previous_states.get(activity["name"]) or STATUS.DISABLED
        misc = {"verbose": verbose, "dry_run": False}

        if PreCheck().applicable(activity):
            previous_state, decisions = PreCheck().run(activity, current_time, previous_time, delta,
                                                       previous_state, decisions, misc)

        status, decisions = decide(STATUS.DISABLED, "default", decisions)

        # - CHECKING STATUS FILE

        current_state = read_activity_status(path_activity_status, activity_name)
        decisions.append(f"[{current_state}] (Status File)")

        # - PROCESS ALL MODULES
        for module in modules:
            if module.applicable(activity):
                current_state, decisions = module.run(activity, current_time, previous_time, delta,
                                                      current_state, decisions, misc)

        # - PROCESS DECISIONS & RETURN RESULTS
        first_run = activity_name not in previous_states
        base_status = STATUS.base[current_state]
        previous_base_status = STATUS.base[previous_state]
        decision = process_decision(base_status, previous_base_status, first_run)

        # - PERFORM DECISIONS
        if decision == ACTION.ENABLE:
            run("ENABLE", path_scripts_enable, activity_name, verbose)
            run("ENABLE", path_scripts_dual, activity_name, verbose, "enable")
        elif decision == ACTION.DISABLE:
            run("DISABLE", path_scripts_disable, activity_name, verbose)
            run("DISABLE", path_scripts_dual, activity_name, verbose, "disable")
        elif decision == ACTION.IDLE:
            pass

        # --------------------------------------------
        # - PRINT STATUS                             -
        # --------------------------------------------
        state_changed = activity_name not in previous_states or current_state != previous_states[activity_name]
        if verbose or state_changed:
            if not status_printed:
                print(f"Processing tick at {dt.datetime.utcfromtimestamp(current_time).strftime('%Y-%m-%d %H:%M:%S')}")
                status_printed = True

            if state_changed:
                print(f"[STATUS] {activity_name} changed from {previous_state} to {current_state}, ", end='')
            else:
                print(f"[STATUS] {activity_name} stayed in {current_state}, ", end='')

            print(', '.join(decisions))

        # --------------------------------------------
        # - UPDATE FILESYSTEM                        -
        # --------------------------------------------
        set_activity_status(path_activity_status, activity_name, current_state)
        previous_states[activity_name] = current_state

    # --------------------------------------------
    # - EXECUTE EXTENSIONS                       -
    # --------------------------------------------

    for extension in os.listdir(path_scripts_extensions):
        code = os.system(f"{path_scripts_extensions}/{extension} > /dev/null 2>&1")
        code = int(int(code) / 256)

        if verbose:
            print(f"[EXTENSION] {extension} returned {code}")

    # --------------------------------------------
    # - PREPARE FOR NEXT TICK                    -
    # --------------------------------------------

    previous_time = current_time
    next_tick = 60

    if verbose:
        print(f"Scheduling next tick in {next_tick} seconds")

    timer.enter(next_tick, 1, tick)
    set_busy(False)


def process_decision(current_status, previous_status, first_run):
    invert = {
        STATUS.ENABLED: STATUS.DISABLED,
        STATUS.DISABLED: STATUS.ENABLED
    }

    if first_run:
        previous_status = invert[current_status]

    decisions = {
        f"{STATUS.ENABLED}:{STATUS.DISABLED}": ACTION.DISABLE,
        f"{STATUS.ENABLED}:{STATUS.ENABLED}": ACTION.IDLE,
        f"{STATUS.DISABLED}:{STATUS.ENABLED}": ACTION.ENABLE,
        f"{STATUS.DISABLED}:{STATUS.DISABLED}": ACTION.DISABLE
    }

    return decisions[f"{previous_status}:{current_status}"]


def match_activities(patterns, activities):
    import re

    found = []

    for pattern in patterns:
        for activity in activities:
            result = re.match(pattern, activity)
            if result is not None:
                found.append(activity)

    found = list(set(found))

    return found


def prepare():
    for module in modules:
        module.prepare()
    create_folders_if_non_existent(directories)


if __name__ == "__main__":

    previous_states = {}

    previous_time = int(time.time())
    timer = sched.scheduler(time.time, time.sleep)

    parser = argparse.ArgumentParser(description="Controls the environment overseer")
    parser.add_argument('-e', '--enable', nargs='+', help='Enables an activity')
    parser.add_argument('-d', '--disable', nargs='+', help='Disables an activity')
    parser.add_argument('-l', '--list', action='store_true', help='List usage activities')
    parser.add_argument('-r', '--reset', action='store_true', help='Reset all timers and disables everything')
    parser.add_argument('-p', '--prepare', action='store_true', help='Prepares the file structure')
    parser.add_argument('-t', '--tick', action='store_true', help='Forces a daemon to process a tick')
    parser.add_argument('-v', '--verbose', action='store_true', help='Makes daemon be extra verbose')
    parser.add_argument('-f', '--forbidreset', action='store_true', help='Makes the deamon ignore reset requests')
    parser.add_argument('-s', '--stop', action='store_true', help='Gracefully stop and wait for the daemon to stop')
    parser.epilog = "Exit Codes: " + " ".join([f"{exit_codes[pair][0]}:{exit_codes[pair][1]}" for pair in exit_codes])
    args = parser.parse_args()

    start_daemon = not (
                args.enable or args.disable or args.reset or args.list or args.prepare or args.tick or args.stop)
    verbose = args.verbose
    forbid_reset = args.forbidreset

    if sys.stdout.isatty():
        os.system("tabs -15")

    if args.list:
        activities = parse_activities()

        if activities.__len__() == 0:
            print("No currently configured activities! See README.md for guide")

        if not is_daemon_running():
            print("Daemon is not running")

        if is_busy():
            print("Daemon currently busy")

        ls_activity: dict
        for ls_activity in activities.values():

            if args.verbose:
                for p in ls_activity.keys():
                    print(f"{p}: {ls_activity[p]}", end='\t')
                print()
                continue

            print(ls_activity["name"], end='\t')

            status = read_activity_status(path_activity_status, ls_activity["name"])
            print(status, end='')
            print("!" if STATUS.base[status] == STATUS.ENABLED else "", end="\t")

            if os.path.isfile(f"{path_scripts_managers}/{ls_activity['name']}"):
                print("Managed", end='\t')
            else:
                print("Unmanaged", end='\t')

            if "Limit" in ls_activity:
                print(dt.timedelta(seconds=int(read_path(path_trackers, ls_activity["name"]))), end='\t')
                print("out of", end='\t')
                print(dt.timedelta(seconds=int(ls_activity["Limit"])), end='\t')

            if "InterruptFor" in ls_activity:
                print("continuous:", end='\t')
                print(dt.timedelta(seconds=int(read_path(path_continuous, ls_activity["name"]))), end='\t')
                print("interrupt_for:", end='\t')
                print(dt.timedelta(seconds=int(ls_activity["InterruptAfter"])), end='\t')
                print("interrupt:", end='\t')
                print(dt.timedelta(seconds=int(read_path(path_interrupts, ls_activity["name"]))), end='\t')

            if ls_activity.__contains__("Recharge"):
                print("Rechargable", end='\t')

            print()

        if sys.stdout.isatty():
            os.system("tabs -8")

        exit(0)

    if args.prepare:
        print(f"Creating folder structure in {path_home}, preparing modules...")
        prepare()
        exit(0)

    if start_daemon and is_daemon_running():
        die("daemon_running")

    if os.getuid() != 0:
        die("root")

    if not start_daemon and not is_daemon_running():
        die("daemon_not_running")

    if args.tick:
        print("Signaling tick to daemon...")
        remote_tick()
        while is_busy():
            time.sleep(0.5)

    if args.reset:

        if os.environ.__contains__(phrase_override_env):
            print("Resetting limits...")
            remote_reset()
            exit(0)

        print(f"Please type: \"{reset_phrase}\"")
        phrase = input()

        print("Note, that if daemon was started with --forbidreset it will ignore reset request")

        if phrase == reset_phrase:
            print("Resetting limits...")
            remote_reset()
        else:
            print("Failed to type the phrase correctly!")

    if args.enable:
        print("Enabling activities...")
        os.chdir(path_home)
        activities = match_activities(args.enable, get_all_activities(path_activities))
        for a in activities:
            print(a)
            if activity_exists(path_activities, a):
                set_activity_status(path_activity_status, a, STATUS.ENABLED)

                if os.path.isfile(f"{path_scripts_managers}/{a}"):
                    print(f"Activity {a} is managed by {path_scripts_managers}/{a}, "
                          "your decision to enable it will be overridden in around a minute.")

            else:
                print(f"Did not find '{a}' activity")
        remote_tick()
        while is_busy(): time.sleep(0.5)

    if args.disable:
        print("Disabling activities...")
        os.chdir(path_home)
        activities = match_activities(args.disable, get_all_activities(path_activities))
        for a in activities:
            print(a)
            if activity_exists(path_activities, a):
                set_activity_status(path_activity_status, a, STATUS.DISABLED)

                if os.path.isfile(f"{path_scripts_managers}/{a}"):
                    print(f"Activity {a} is managed by {path_scripts_managers}/{a}, "
                          "your decision to disable it will be overridden in around a minute.")

            else:
                print(f"Did not find '{a}' activity")
        remote_tick()
        while is_busy(): time.sleep(0.5)

    if start_daemon:
        print("Starting as daemon...")
        create_folders_if_non_existent(directories)
        os.chdir(path_home)
        os.environ['PATH'] = f"{path_helpers}:{os.environ['PATH']}"
        os.environ['DATA'] = path_tmp
        prepare()

        signal.signal(signal.SIGUSR1, sigusr)
        signal.signal(signal.SIGUSR2, sigusr2)
        signal.signal(signal.SIGTERM, sigterm)
        tick()
        with open(path_pid, "w") as pidf:
            pidf.write(str(os.getpid()))
            pidf.close()

        resetter = Resetter()
        resetter.scan()
        timer.run()

    if args.stop:
        print("Stopping daemon...")
        remote(signal.SIGTERM)
        time.sleep(0.1)
        while is_busy(): time.sleep(0.5)
