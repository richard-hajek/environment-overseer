import json
import os.path
import shutil
import subprocess
import time
import datetime as dt

import overseer.modules.auto_trigger
import overseer.modules.forbid
import overseer.config
import overseer.filesystem
import overseer.main
import overseer.modules.limit

modules_to_test = [
    overseer.modules.auto_trigger.AutoTrigger,
    overseer.modules.forbid.ForbidActivity
]


class ROUTINE_TYPES:
    ADD_ACTIVITY = 0
    SET_TIME = 1
    RUN_CMD = 2
    ACTIVITY_ASSERT = 3
    SET_ACTIVITY = 4

    @staticmethod
    def get_str(routine_type):
        return ["ADD_ACT", "SET_TIME", "RUN_CMD", "ACT_ASSERT", "SET_ACTIVITY"][routine_type]


def debug_print():

    def debug_folder(folder):

        print(f"[DEBUG]", end=' ')

        if not os.path.isdir(folder):
            print(f"{folder} doesn't even exist")
            return

        if len(os.listdir(folder)) == 0:
            print(f"No files in {folder}")

        for act in os.listdir(folder):
            print(os.path.join(folder, act), end="\t")

            print("'", end='')
            with open(os.path.join(folder, act)) as f:
                print(("".join(f.readlines())).replace("\n", "\\n"), end='')
            print("'")

    debug_folder("/etc/overseer/activities")
    debug_folder("/etc/overseer/status")
    debug_folder("/etc/overseer/checks/tracker")

    print("/time file")

    if os.path.isfile("/time"):
        with open("/time") as f:
            print(f.readlines())
    else:
        print("Doesnt exist")


def execute_instruction(routine_type, data):

    print("\n\n\n\n")
    print(f"Executing {ROUTINE_TYPES.get_str(routine_type)} ({routine_type}) with {data}")
    print("=====> DEBUG BEFORE")
    debug_print()

    overseer.main.wait_for_until_not_busy()

    if routine_type == ROUTINE_TYPES.ADD_ACTIVITY:

        with open(os.path.join(overseer.config.path_activities, "activity.json"), "w") as f:
            json.dump(data, f)

        activity_data = overseer.main.parse_activities()["activity"]
        overseer.modules.limit.write("activity", activity_data["Limit"], 0)

    elif routine_type == ROUTINE_TYPES.SET_TIME:
        t = dt.datetime.combine(dt.date.today(), dt.time.fromisoformat(data))
        os.system(f"echo '{t.strftime('%Y-%m-%d %T')}' > /time")

    elif routine_type == ROUTINE_TYPES.RUN_CMD:

        os.system(data)

    elif routine_type == ROUTINE_TYPES.ACTIVITY_ASSERT:

        if not os.path.exists(os.path.join(overseer.config.path_activity_status, "activity")):
            status = "disabled"
        else:
            with open(os.path.join(overseer.config.path_activity_status, "activity")) as f:
                status = f.readline().strip()

        assert (status == data)

    elif routine_type == ROUTINE_TYPES.SET_ACTIVITY:

        with open(os.path.join(overseer.config.path_activity_status, "activity"), "w") as f:
            f.write(data)

    overseer.main.remote_tick()
    overseer.main.wait_for_until_not_busy()

    print("=====> DEBUG AFTER")
    debug_print()


def execute_routine(routine):

    print("==ROUTINE BEGIN==")

    if os.path.exists(overseer.config.path_home):
        shutil.rmtree(overseer.config.path_home)

    p = subprocess.Popen("overseer --verbose", shell=True, env=os.environ.copy())

    while not overseer.filesystem.is_daemon_running():
        print("Waiting for daemon to start")
        time.sleep(0.2)

    print("Daemon started")
    for routine_type, data in routine:
        execute_instruction(routine_type, data)

    p.kill()

    os.remove(overseer.filesystem.path_busy)
    os.remove(overseer.filesystem.path_pid)

    print("==ROUTINE END==\n\n")


def main():

    def add_activity(data):
        return ROUTINE_TYPES.ADD_ACTIVITY, data

    def set_time(time_to):
        return ROUTINE_TYPES.SET_TIME, time_to

    def set_activity(status):
        return ROUTINE_TYPES.SET_ACTIVITY, status

    def run_command(cmd):
        return ROUTINE_TYPES.RUN_CMD, cmd

    def activity_assert(status):
        return ROUTINE_TYPES.ACTIVITY_ASSERT, status

    for m in modules_to_test:

        routines = m.self_test(add_activity, set_time, set_activity, run_command, activity_assert)

        for routine in routines:
            execute_routine(routine)

    print("Tests OK")


    pass


if __name__ == "__main__":
    main()