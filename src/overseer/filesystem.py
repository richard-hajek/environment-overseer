import json
import os

import psutil

from src.overseer.config import STATUS
from src.overseer.config import path_activities
from src.overseer.config import path_checks
from src.overseer.config import path_trackers

path_pid = f"/run/overseer.pid"
path_busy = f"/run/overseer.busy"


def create_folders_if_non_existent(directories):
    for path in directories:
        os.path.isdir(path) or os.makedirs(path)


def create_all_records(directory=path_trackers):
    for activity in os.listdir(path_activities):
        zero_if_non_existent(directory, activity.split('.')[0])


def run(flag, directory, activity_name, verbose, args=""):
    code = os.system(f"{directory}/{activity_name} {args} {'> /dev/null 2>&1' if not verbose else ''}")
    code = int(int(code) / 256)

    if verbose:
        print(f"[{flag}] {activity_name}, returned {code}")


def run_script(script_path, verbose):
    code = os.system(f"{script_path} > /dev/null 2>&1")
    code = int(int(code) / 256)

    if verbose:
        print(f"[SCRIPT] {script_path}, returned {code}")

    return code


def activity_exists(activities_directory, activity_name):
    return os.path.isfile(f"{activities_directory}/{activity_name}.json")


def zero_if_non_existent(directory, activity_name):
    path = f"{directory}/{activity_name}"

    if os.path.isfile(path):
        return

    with open(path, 'w') as content_file:
        content_file.write('0')


def read_path(directory, activity_name):
    path = f"{directory}/{activity_name}"

    if not os.path.isfile(path):
        return 0.

    with open(path, 'r') as content_file:
        time_spent = content_file.read()

    try:
        time_spent = float(time_spent) / 1000.
    except():
        time_spent = 0.

    return time_spent


def write_path(directory, activity_name, seconds):
    with open(f"{directory}/{activity_name}", 'w') as file:
        file.write(str(int(seconds * 1000)))


def read_activity_status(activity_status_folder, activity_name, default=STATUS.DISABLED):
    path = f"{activity_status_folder}/{activity_name}"

    if not os.path.isfile(path):
        set_activity_status(activity_status_folder, activity_name, default)

    with open(path, 'r') as content_file:
        return content_file.read()


def set_activity_status(activity_status_folder, activity_name, status):
    path = f"{activity_status_folder}/{activity_name}"

    with open(path, 'w') as content_file:
        content_file.write(status)


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


def get_all_activities(path_activities):
    return [".".join(x.split(".")[:-1]) for x in os.listdir(path_activities)]


def create_hash(activity_name, data):
    if type(data) == int: data = float(data)

    content = str(data) + activity_name
    # content = content.encode()
    # hsh = md5(content).hexdigest()
    # return str(hsh)
    return content


def write_check(tag, activity_name, data):
    if not os.path.isdir(f"{path_checks}/{tag}"):
        os.makedirs(f"{path_checks}/{tag}")

    with open(f"{path_checks}/{tag}/{activity_name}", 'w') as file:
        file.write(str(create_hash(activity_name, data)))


def check_check(tag, activity_name, data):
    if not os.path.isdir(f"{path_checks}/{tag}"):
        os.makedirs(f"{path_checks}/{tag}")
        print(f"Failed check due to nonexistent TAG folder {path_checks}/{tag}")
        return False

    if not os.path.isfile(f"{path_checks}/{tag}/{activity_name}"):
        print(f"Failed check due to missing {path_checks}/{tag}/{activity_name}")
        return False

    with open(f"{path_checks}/{tag}/{activity_name}", 'r') as file:
        check = file.read()

    if check != create_hash(activity_name, data):
        print(f"Failed check due to bad hashsum: {check} != {create_hash(activity_name, data)}")

    return check == create_hash(activity_name, data)


def parse_activities():
    names = os.listdir(path_activities)
    activities = {}

    for name in names:
        with open(f"{path_activities}/{name}", 'r') as f:
            activity = json.load(f)

        activity["name"] = name.split(".")[0]
        activities[activity['name']] = activity

    for activity in activities.values():

        if "Limit" in activity:
            activity["Limit"] = parse_time(activity["Limit"], activity["name"])

        if "Recharge" in activity:
            activity["Recharge"] = parse_time(activity["Recharge"], activity["name"])

        if "ResetOn" not in activity:
            activity["ResetOn"] = "04:00"

        if "Goal" in activity:
            activity["Goal"] = float(activity["Goal"])

        if "InterruptAfter" in activity or "InterruptFor" in activity:
            activity["InterruptAfter"] = parse_time(activity.get("InterruptAfter") or "1H", activity["name"])
            activity["InterruptFor"] = parse_time(activity.get("InterruptFor") or "1H", activity["name"])

    return activities


def parse_time(time_raw, activity_name):
    try:
        raw_time = float(time_raw[:-1])
        unit = time_raw[-1:].lower()
    except ValueError:
        print(f'Could not parse time "{time_raw}" of activity {activity_name}')
        return -1

    if unit == 'h':
        time_parsed = raw_time * 3600
    elif unit == 'm':
        time_parsed = raw_time * 60
    elif unit == 's':
        time_parsed = raw_time
    else:
        print(f"Unknown time unit '{unit}' in activity {activity_name}")
        return -1

    return time_parsed
