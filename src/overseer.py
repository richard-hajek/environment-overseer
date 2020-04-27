#!/usr/bin/python

import argparse
import os
import sched
import signal
import time
import psutil
import json
import datetime as dt
from pathlib import Path


# --------------------------------------------
# - PREPARATION                              -
# --------------------------------------------

def die(reason):
    print(exit_codes[reason][1])
    exit(exit_codes[reason][0])


# --------------------------------------------
# - DEFINE APP VARIABLES                     -
# --------------------------------------------

class STATUS:
    ENABLED = "enabled"
    DISABLED = "disabled"
    READY = "ready"
    INTERRUPTED = "interrupted"


class ACTION:
    IDLE = "idle"
    ENABLE = "enable"
    DISABLE = "disable"
    INTERRUPT = "interrupt"


exit_codes = {
    "success": (0, "Success"),
    "daemon_running": (1, "Daemon is running"),
    "daemon_not_running": (2, "Daemon is not running"),
    "root": (3, "Must be ran as root"),
    "misconfiguration": (4, "Overseer is misconfigured")
}

path_home = "/etc/overseer"

path_activities = f"{path_home}/activities"
path_enabled = f"{path_home}/status/enabled"
path_ready = f"{path_home}/status/ready"
path_trackers = f"{path_home}/status/trackers"
path_trackers_reverse = f"{path_home}/status/reverse"
path_continuous = f"{path_home}/status/continuous"
path_interrupts = f"{path_home}/status/interrupts"

path_scripts_enable = f"{path_home}/scripts/enable"
path_scripts_disable = f"{path_home}/scripts/disable"
path_scripts_managers = f"{path_home}/scripts/managers"
path_scripts_checks = f"{path_home}/scripts/checks"

path_scripts_extensions = f"{path_home}/scripts/extensions"

path_pid = f"/run/overseer.pid"

reset_phrase = "I am an addicted idiot and need to reset the trackers."
phrase_override_env = "OVERSEER_PHRASE_OVERRIDE"


# --------------------------------------------
# - FILESYSTEM FUNCTIONS                     -
# --------------------------------------------

def create_folders_if_non_existent():
    for path in [path_home, path_activities, path_enabled, path_ready, path_trackers, path_trackers_reverse,
                 path_continuous, path_interrupts, path_scripts_enable, path_scripts_disable,
                 path_scripts_managers, path_scripts_checks, path_scripts_extensions]:
        if not os.path.isdir(path):
            os.makedirs(path)


def create_all_records():
    for activity in os.listdir(path_activities):
        activity = activity.split('.')[0]
        zero_activity_time_if_non_existent(activity)


def run_enable(act_name):
    code = os.system(f"{path_scripts_enable}/{act_name} > /dev/null 2>&1")
    code = int(int(code) / 256)

    if verbose:
        print(f"[ENABLE] {act_name}, returned {code}")


def run_disable(act_name):
    code = os.system(f"{path_scripts_disable}/{act_name} > /dev/null 2>&1")
    code = int(int(code) / 256)

    if verbose:
        print(f"[DISABLE] {act_name}, returned {code}")


def run_script(script_path):
    code = os.system(f"{script_path} > /dev/null 2>&1")
    code = int(int(code) / 256)

    if verbose:
        print(f"[SCRIPT] {script_path}, returned {code}")

    return code


def activity_exists(act_name):
    return os.path.isfile(f"{path_activities}/{act_name}.json")


def read_activity_time(act_name):
    path = f"{path_trackers}/{act_name}"

    if not os.path.isfile(path):
        return 0

    with open(path, 'r') as content_file:
        time_spent = content_file.read()

    try:
        time_spent = float(time_spent) / 1000
    except():
        time_spent = 0

    return time_spent


def write_activity_time(act_name, seconds):
    with open(f"{path_trackers}/{act_name}", 'w') as file:
        file.write(str(int(seconds * 1000)))


def write_reverse_time(act_name, seconds):
    with open(f"{path_trackers_reverse}/{act_name}", 'w') as file:
        file.write(str(int(seconds * 1000)))


def zero_activity_time_if_non_existent(act_name):
    path = f"{path_trackers}/{act_name}"

    if os.path.isfile(path):
        return

    with open(path, 'w') as content_file:
        content_file.write('0')


def read_activity_continuous_time(act_name):
    path = f"{path_continuous}/{act_name}"

    if not os.path.isfile(path):
        return 0

    with open(path, 'r') as content_file:
        time_spent = content_file.read()

    time_spent = float(time_spent) / 1000

    try:
        time_spent = float(time_spent) / 1000
    except():
        time_spent = 0

    return time_spent


def write_continuous_time(act_name, seconds):
    with open(f"{path_continuous}/{act_name}", 'w') as file:
        file.write(str(int(seconds * 1000)))


def delete_continuous_time(act_name):
    os.remove(f"{path_continuous}/{act_name}")


def read_interrupted_time(act_name):
    path = f"{path_interrupts}/{act_name}"

    if not os.path.isfile(path):
        return 0

    with open(path, 'r') as content_file:
        time_spent = content_file.read()

    try:
        time_spent = float(time_spent) / 1000
    except():
        time_spent = 0

    return time_spent


def write_interrupted_time(act_name, seconds):
    with open(f"{path_interrupts}/{act_name}", 'w') as file:
        file.write(str(int(seconds * 1000)))


def delete_interrupted_time(act_name):
    os.remove(f"{path_interrupts}/{act_name}")


def link_enable(act_name):
    if not os.path.islink(f"{path_enabled}/{act_name}"):
        os.symlink(f"{path_activities}/{act_name}.json", f"{path_enabled}/{act_name}")

    if os.path.islink(f"{path_ready}/{act_name}"):
        os.remove(f"{path_ready}/{act_name}")


def link_disable(act_name):
    if os.path.islink(f"{path_enabled}/{act_name}"):
        os.remove(f"{path_enabled}/{act_name}")

    if os.path.islink(f"{path_ready}/{act_name}"):
        os.remove(f"{path_ready}/{act_name}")


def link_ready(act_name):
    if not os.path.islink(f"{path_ready}/{act_name}"):
        os.symlink(f"{path_activities}/{act_name}.json", f"{path_ready}/{act_name}")

    if os.path.islink(f"{path_enabled}/{act_name}"):
        os.remove(f"{path_enabled}/{act_name}")


def reset_timers():
    activities = parse_activities()

    for activity in activities.values():

        name = activity["name"]

        if not activity.__contains__("Recharge"):
            write_activity_time(name, 0)

        if os.path.islink(f"{path_enabled}/{name}"):
            os.remove(f"{path_enabled}/{name}")

    tick()


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


def get_all_activities():
    return [".".join(x.split(".")[:-1]) for x in os.listdir(path_activities)]

# --------------------------------------------
# - SIGNALING METHODS                        -
# --------------------------------------------


def remote_tick():
    with open(path_pid, 'r') as content_file:
        pid = content_file.read()
        pid = int(pid)
        os.kill(pid, signal.SIGUSR1)


def remote_reset():
    with open(path_pid, 'r') as content_file:
        pid = content_file.read()
        pid = int(pid)
        os.kill(pid, signal.SIGUSR2)


def sigterm(_, __):  # Disable all activities and shutdown
    for name in os.listdir(f"{path_enabled}"):
        os.remove(f"{path_enabled}/{name}")

    tick()
    die("success")


def sigusr(_, __):
    tick()


def sigusr2(_, __):
    reset_timers()
    global activity_trackers
    activity_trackers = {}


# --------------------------------------------
# - CORE / PROCESSING                        -
# --------------------------------------------

def tick():
    global last_tick_at
    global last_states

    create_all_records()
    for event in timer.queue:
        timer.cancel(event)

    activities = parse_activities()
    previous_time = int(last_tick_at)
    current_time = int(time.time())
    time_delta = current_time - previous_time

    print(f"Processing tick at {dt.datetime.utcfromtimestamp(current_time).strftime('%Y-%m-%d %H:%M:%S')}")
    for activity in activities.values():

        # --------------------------------------------
        # - PROCESS ACTIVITY                         -
        # --------------------------------------------

        decisions = []
        activity_name = activity["name"]
        previous_state = STATUS.DISABLED

        if last_states.__contains__(activity_name):
            previous_state = last_states[activity_name]

        if os.path.isfile(f"{path_scripts_checks}/{activity_name}"):
            check_return_code = run_script(f"{path_scripts_checks}/{activity_name}")
            if check_return_code == 0:
                decisions.append("PREV ENABLED (Check)")
                previous_state = STATUS.ENABLED
            elif check_return_code == 1:
                decisions.append("PREV DISABLED (Check)")
                previous_state = STATUS.DISABLED

        activity_tick_data_pack = dict(activity=activity, previous_time=previous_time, current_time=current_time,
                                       delta_time=time_delta, previous_state=previous_state)

        current_status = STATUS.DISABLED
        decisions.append("DISABLE (default)")

        # - CHECKING FILE LINK
        link_enabled = os.path.islink(f"{path_enabled}/{activity_name}")
        if link_enabled:
            current_status = STATUS.ENABLED
            decisions.append("ENABLE (File link)")

        # - PROCESS ALL MODULES
        current_status, decisions = module_auto_trigger(activity_tick_data_pack, current_status, decisions)
        current_status, decisions = module_manager(activity_tick_data_pack, current_status, decisions)
        current_status, decisions = module_limit(activity_tick_data_pack, current_status, decisions)
        current_status, decisions = module_interrupts(activity_tick_data_pack, current_status, decisions)
        current_status, decisions = module_recharge(activity_tick_data_pack, current_status, decisions)
        current_status, decisions = module_reset(activity_tick_data_pack, current_status, decisions)

        # - PROCESS DECISIONS & RETURN RESULTS
        first_run = not last_states.__contains__(activity_name)
        decision = process_decision(current_status, previous_state, first_run)

        # - PERFORM DECISIONS
        if decision == ACTION.ENABLE:
            run_enable(activity_name)
        elif decision == ACTION.DISABLE:
            run_disable(activity_name)
        elif decision == ACTION.IDLE:
            pass

        # --------------------------------------------
        # - PRINT STATUS                             -
        # --------------------------------------------
        message = f"[STATUS] {activity_name} "

        if current_status == previous_state:
            message += f"stayed in {current_status} state, "
        else:
            message += f"changed from {previous_state} to {current_status}, "

        message += f"decisions based on: {', '.join(decisions)}"

        if verbose or not last_states.__contains__(activity_name) or current_status != last_states[activity_name]:
            print(message)

        # --------------------------------------------
        # - UPDATE FILESYSTEM                        -
        # --------------------------------------------
        if current_status == STATUS.ENABLED:
            link_enable(activity_name)
        elif current_status == STATUS.DISABLED:
            link_disable(activity_name)
        elif current_status == STATUS.READY:
            link_ready(activity_name)

        last_states[activity_name] = current_status

    # --------------------------------------------
    # - EXECUTE EXTENSIONS                       -
    # --------------------------------------------

    extension_guardian()
    for extension in os.listdir(path_scripts_extensions):
        code = os.system(f"{path_scripts_extensions}/{extension} > /dev/null 2>&1")
        code = int(int(code) / 256)

        if verbose:
            print(f"[EXTENSION] {extension} returned {code}")

    # --------------------------------------------
    # - PREPARE FOR NEXT TICK                    -
    # --------------------------------------------

    last_tick_at = time.time()
    next_tick = 60

    if verbose:
        print(f"Scheduling next tick in {next_tick} seconds")

    timer.enter(next_tick, 1, tick)


def module_auto_trigger(activity_data, current_status, decisions):
    activity = activity_data["activity"]
    previous_time = activity_data["previous_time"]
    current_time = activity_data["current_time"]
    auto_start = None

    if activity.__contains__("AutoStart"):
        auto_start = activity["AutoStart"]

    auto_stop = None
    if activity.__contains__("AutoStop"):
        auto_stop = activity["AutoStop"]

    if auto_start is not None:
        if process_auto_trigger(previous_time, current_time, auto_start):
            current_status = STATUS.ENABLED
            decisions.append("ENABLE (AutoStart)")

    if auto_stop is not None:
        if process_auto_trigger(previous_time, current_time, auto_stop):
            current_status = STATUS.DISABLED
            decisions.append("DISABLE (AutoStop)")

    return current_status, decisions


def process_auto_trigger(previous_time, current_time, trigger_at):
    trigger_timestamp = dt.datetime.combine(dt.date.today(), dt.time.fromisoformat(trigger_at)).timestamp()

    if previous_time < trigger_timestamp <= current_time:
        return True
    return False


def module_manager(activity_data_pack, current_status, decisions):
    activity_name = activity_data_pack["activity"]["name"]

    if not os.path.isfile(f"{path_scripts_managers}/{activity_name}"):
        return current_status, decisions

    manager_return_code = run_script(f"{path_scripts_managers}/{activity_name}")

    if manager_return_code is not None:
        if manager_return_code == 0:
            current_status = STATUS.ENABLED
            decisions.append("ENABLE (Manager script)")
        elif manager_return_code == 1:
            current_status = STATUS.READY
            decisions.append("READY (Manager script)")

    return current_status, decisions


def module_limit(activity_data_pack, current_status, decisions):
    activity = activity_data_pack["activity"]

    if not activity.__contains__("Limit"):
        return current_status, decisions

    activity_name = activity["name"]
    time_delta = activity_data_pack["delta_time"]

    activity_time = read_activity_time(activity_name)
    limit = activity["Limit"]

    activity_time, activity_still_available = process_limit(time_delta, activity_time, limit, current_status)

    if not activity_still_available:
        current_status = STATUS.DISABLED
        decisions.append("DISABLE (Limit)")

    if activity_data_pack.__contains__("previous_status") and activity_data_pack["previous_status"] == STATUS.ENABLED:
        activity_time += time_delta

    if activity_time > limit:
        activity_time = limit

    write_activity_time(activity_name, activity_time)
    write_reverse_time(activity_name, limit - activity_time)

    return current_status, decisions


def process_limit(time_delta, activity_time, limit, current_status):
    if current_status == STATUS.ENABLED:
        activity_time += time_delta

    if activity_time >= limit:
        activity_time = limit
        return activity_time, False

    return activity_time, True


def module_interrupts(activity_data_pack, current_status, decisions):
    activity = activity_data_pack["activity"]

    if not activity.__contains__("InterruptAfter"):
        return current_status, decisions

    activity_name = activity["name"]
    time_delta = activity_data_pack["delta_time"]
    previous_status = activity_data_pack["previous_state"]

    continuous_time = read_activity_continuous_time(activity_name)
    interrupted_for = read_interrupted_time(activity_name)
    interrupt_after = activity["InterruptAfter"]
    interrupt_for = activity["InterruptFor"]

    if current_status == STATUS.ENABLED:
        interrupt_action, interrupted_for, continuous_time = process_interrupt(current_status, interrupt_after, interrupt_for, continuous_time,
                                             interrupted_for, time_delta)

        write_continuous_time(activity_name, continuous_time)

        if interrupt_action == ACTION.INTERRUPT:
            decisions.append("[INTERRUPT] Interrupt time reached! Interrupting activity")
            current_status = STATUS.INTERRUPTED
            write_interrupted_time(activity_name, interrupted_for)

    elif current_status == STATUS.INTERRUPTED:
        interrupt_action, interrupted_for = process_interrupt(current_status, interrupt_after, interrupt_for, continuous_time,
                                             interrupted_for, time_delta)

        if interrupt_action == ACTION.IDLE and previous_status == STATUS.INTERRUPTED:
            decisions.append("[INTERRUPT] Interrupt finished! You are now free to use the activity")
            write_interrupted_time(activity_name, 0)

    else:
        write_continuous_time(activity_name, 0)
        write_interrupted_time(activity_name, 0)

    return current_status, decisions


def process_interrupt(current_status, interrupt_after, interrupt_for, continuous_time, interrupted_for, time_delta):
    if current_status == STATUS.ENABLED and continuous_time >= interrupt_after:
        return ACTION.INTERRUPT, interrupt_for, 0

    if current_status == STATUS.ENABLED and continuous_time < interrupt_after:
        return ACTION.IDLE, interrupted_for, continuous_time + time_delta

    if interrupted_for != 0:
        interrupted_for -= time_delta

        if interrupted_for < 0:
            return ACTION.IDLE, 0

        return ACTION.INTERRUPT, interrupted_for, continuous_time

    return ACTION.IDLE, 0, continuous_time


def module_recharge(activity_data_pack, current_status, decisions):
    activity = activity_data_pack["activity"]

    if not activity.__contains__("Limit") or not activity.__contains__("Recharge"):
        return current_status, decisions

    if current_status == STATUS.ENABLED:
        return current_status, decisions

    time_delta = activity_data_pack["delta_time"]
    recharge_time = activity["Recharge"]
    limit = activity["Limit"]
    activity_time = read_activity_time(activity["name"])

    recharge = process_recharge(time_delta, current_status, recharge_time, limit)
    activity_time -= recharge

    if activity_time <= 0:
        activity_time = 0

    write_activity_time(activity_time, activity["name"])
    return current_status, decisions


def process_recharge(time_delta, current_status, recharge_time, limit):
    if current_status == STATUS.ENABLED:
        return 0

    recharge = limit / recharge_time  # Get how many seconds should recharge in one second
    recharge *= time_delta  # Multiply by num of seconds

    return recharge


def module_reset(activity_data, current_status, decisions):
    activity = activity_data["activity"]
    act_name = activity["name"]
    previous_time = activity_data["previous_time"]
    current_time = activity_data["current_time"]
    reset = activity["ResetOn"]

    if process_reset(previous_time, current_time, reset):

        global allow_reset
        allow_reset.append(act_name)

        write_activity_time(act_name, 0)
        current_status = STATUS.DISABLED

        if activity["Limit"]:
            write_reverse_time(act_name, activity["Limit"])

    return current_status, decisions


def process_reset(previous_time, current_time, reset):
    trigger_timestamp = dt.datetime.combine(dt.date.today(), dt.time.fromisoformat(reset)).timestamp()

    if previous_time < trigger_timestamp <= current_time:
        return True
    return False


def process_decision(current_status, previous_status, first_run):
    if current_status == STATUS.INTERRUPTED and previous_status != STATUS.INTERRUPTED:
        return ACTION.DISABLE

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


SYSTEMD_UNIT_PATH = "/etc/systemd/system/overseer.service"
RECHARGE_TOLERANCE = 100

activity_defs = None

systemd_unit = None
overseer_code = None

activity_files = {}
activity_trackers = {}
previous_time = None

allow_reset = []


def extension_guardian():

    global overseer_code
    global activity_defs
    global activity_trackers
    global previous_time
    global allow_reset
    global systemd_unit

    # SECURING SOURCE CODE
    path_to_code = os.path.realpath(__file__)
    if overseer_code is None:
        with open(path_to_code, 'r') as f:
            overseer_code = f.read()
    
    # REMOVED because it is just annying to work with and it's not like I can cheat simply by editing the code. I mean I can cheat by editing the code but it's not gonna be simple
    #with open(path_to_code, 'r+') as f:
    #    if overseer_code != f.read():
    #        f.seek(0)
    #        print(f"[GUARDIAN] Detected change in {path_to_code}, rewriting with original content")
    #        f.write(overseer_code)
    #        f.truncate()

    # SECURING SYSTEMD UNIT
    if systemd_unit is None:

        with open(SYSTEMD_UNIT_PATH, 'r') as content_file:
            systemd_unit = content_file.read()

    with open(SYSTEMD_UNIT_PATH, 'r+') as content_file:
        if systemd_unit != content_file.read():
            content_file.seek(0)
            print(f"[GUARDIAN] Detected change in {SYSTEMD_UNIT_PATH}, overwriting with original content...")
            content_file.write(systemd_unit)
            content_file.truncate()

    # SECURING ACTIVITY DEFINITIONS
    if activity_defs is None:
        activity_defs = parse_activities()

    for activity in activity_defs.values():

        if not activity_files.__contains__(activity["name"]):
            with open(Path(f"{path_activities}/{activity['name']}.json"), 'r') as content_file:
                activity_files[activity["name"]] = content_file.read()

        with open(Path(f"{path_activities}/{activity['name']}.json"), 'r+') as content_file:
            if activity_files[activity["name"]] != content_file.read():
                content_file.seek(0)
                print(f"[GUARDIAN] Detected change in {activity['name']}.json, overwriting with original content...")
                content_file.write(activity_files[activity["name"]])
                content_file.truncate()

    # SECURING ACTIVITY TRACKERS
    current_time = int(time.time())
    if previous_time is None:
        previous_time = current_time

    for activity in os.listdir(path_activities):
        name = Path(f"{path_activities}/{activity}").stem

        if not activity_trackers.__contains__(name):
            activity_trackers[name] = read_activity_time(name)

        current_time = read_activity_time(name)
        prev_time = activity_trackers[name]
        activity_trackers[name] = current_time

        if current_time < prev_time:  # GREAT SUSPICION OF CHEATING
            if process_auto_trigger(previous_time, current_time, activity_defs[name]["ResetOn"]):
                continue
            if activity_defs[name].__contains__("Recharge") and prev_time - current_time < RECHARGE_TOLERANCE:
                continue
            if allow_reset.__contains__(name):
                continue

            # If there is no reason why activity should decrease in tracker time, reset the tracker to previous value
            print(f"[GUARDIAN] Detected change in {name}'s tracker, overwriting with previous time ({prev_time})...")
            write_activity_time(name, prev_time)

    allow_reset = []
    previous_time = current_time


def parse_activities():
    names = os.listdir(path_activities)
    activities = {}

    for name in names:
        with open(f"{path_activities}/{name}", 'r') as f:
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

        if not activity.__contains__("ResetOn"):
            activity["ResetOn"] = "04:00"

        if activity.__contains__("InterruptAfter") or activity.__contains__("InterruptFor"):
            if not activity.__contains__("InterruptAfter"):
                activity["InterruptAfter"] = "01:00"
            if not activity.__contains__("InterruptFor"):
                activity["InterruptFor"] = "01:00"
            activity["InterruptAfter"] = parse_time(activity["InterruptAfter"], activity["name"])
            activity["InterruptFor"] = parse_time(activity["InterruptFor"], activity["name"])

    return activities


def parse_time(time_raw, act_name):
    time_parsed = 0
    unit = ''
    time = 0

    try:
        time = float(time_raw[:-1])
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


if __name__ == "__main__":

    last_states = {}

    last_tick_at = int(time.time())
    timer = sched.scheduler(time.time, time.sleep)

    parser = argparse.ArgumentParser(description="Controls the environment overseer")
    parser.add_argument('-e', '--enable', nargs='+', help='Enables an activity')
    parser.add_argument('-d', '--disable', nargs='+', help='Disables an activity')
    parser.add_argument('-l', '--list', action='store_true', help='List usage activities')
    parser.add_argument('-r', '--reset', action='store_true', help='Reset all timers and disables everything')
    parser.add_argument('-p', '--prepare', action='store_true', help='Prepares the file structure')
    parser.add_argument('-t', '--tick', action='store_true', help='Forces a daemon to process a tick')
    parser.add_argument('-v', '--verbose', action='store_true', help='Makes daemon be extra verbose')
    parser.epilog = "Exit Codes: " + " ".join([f"{exit_codes[pair][0]}:{exit_codes[pair][1]}" for pair in exit_codes])
    args = parser.parse_args()

    start_daemon = not args.enable and \
                   not args.disable and \
                   not args.reset and \
                   not args.list and \
                   not args.prepare and \
                   not args.tick

    verbose = args.verbose

    if args.list:
        activities = parse_activities()
        enabled = os.listdir(path_enabled)
        ready = os.listdir(path_ready)

        if activities.__len__() == 0:
            print("No currently configured activities! See README.md for guide")

        if not is_daemon_running():
            print("Daemon is not running")

        for ls_activity in activities.values():
            print(ls_activity["name"], end='\t')
            if enabled.__contains__(ls_activity["name"]):
                print("Enabled!", end='\t')
            elif read_interrupted_time(ls_activity["name"]) != 0:
                print("Interrupted!", end='\t')
            elif ready.__contains__(ls_activity["name"]):
                print("Standby!", end='\t')
            else:
                print("Disabled", end='\t')

            if os.path.isfile(f"{path_scripts_managers}/{ls_activity['name']}"):
                print("Managed", end='\t')
            else:
                print("Unmanaged", end='\t')

            print(dt.timedelta(seconds=int(read_activity_time(ls_activity["name"]))), end='\t')
            print("out of", end='\t')
            print(dt.timedelta(seconds=int(ls_activity["Limit"])), end='\t')

            if ls_activity.__contains__("Recharge"):
                print("Rechargable", end='\t')

            print()
        exit(0)

    if args.prepare:
        print(f"Creating folder structure in {path_home}")
        create_folders_if_non_existent()
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
        activities = match_activities(args.enable, get_all_activities())
        for a in activities:
            print(a)
            if activity_exists(a):
                link_enable(a)

                if os.path.isfile(f"{path_scripts_managers}/{a}"):
                    print(f"Activity {a} is managed by {path_scripts_managers}/{a}, "
                          "your decision to enable it will be overridden in around a minute.")

            else:
                print(f"Did not find '{a}' activity")
        remote_tick()

    if args.disable:
        print("Disabling activities...")
        os.chdir(path_home)
        activities = match_activities(args.disable, get_all_activities())
        for a in activities:
            print(a)
            if activity_exists(a):
                link_disable(a)

                if os.path.isfile(f"{path_scripts_managers}/{a}"):
                    print(f"Activity {a} is managed by {path_scripts_managers}/{a}, "
                          "your decision to disable it will be overridden in around a minute.")

            else:
                print(f"Did not find '{a}' activity")
        remote_tick()

    if start_daemon:
        print("Starting as daemon...")
        create_folders_if_non_existent()
        os.chdir(path_home)
        create_all_records()

        signal.signal(signal.SIGUSR1, sigusr)
        signal.signal(signal.SIGUSR2, sigusr2)
        signal.signal(signal.SIGTERM, sigterm)
        tick()
        with open(path_pid, "w") as pidf:
            pidf.write(str(os.getpid()))
            pidf.close()
        timer.run()
