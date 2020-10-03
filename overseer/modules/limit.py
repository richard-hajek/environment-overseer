from overseer.config import *
from overseer.filesystem import *
from overseer.modules.supermodule import Supermodule
from overseer.utils import *


class Limit(Supermodule):

    def applicable(self, activity):
        return "Limit" in activity or "Goal" in activity

    def run(self, activity: {}, time: float, time_prev: float, delta: float, status: str, decisions: [], misc: {}):
        limit = activity.get("Limit") or activity.get("Goal")

        activity_time = float(read_path(path_trackers, activity["name"]))

        if not check_check(CHECK_TAG, activity["name"], activity_time):
            decisions.append("[LIMIT] Detecting a bad check, forcing a full limit or empty goal")
            activity_time = limit * ("Limit" in activity)

        activity_time += delta * (STATUS.base[status] == STATUS.ENABLED)
        activity_time = min(activity_time, limit)

        if activity_time >= limit:
            status, decisions = decide(STATUS.DISABLED, "Limit", decisions)

        activity_time = min(activity_time, limit)
        write(activity["name"], limit, activity_time)

        if "ResetOn" in activity and just_happened(time_prev, time, activity["ResetOn"]):
            write(activity["name"], limit, 0)

        return status, decisions

    def reset(self, activities):
        print("Manual reset...")
        for a in activities.values():
            limit_like = a.get("Limit") or a.get("Goal")
            write(a["name"], limit_like, 0)


CHECK_TAG = "tracker"


def write(activity_name, limit, activity_time):
    activity_time = float(activity_time)
    write_path(path_trackers, activity_name, activity_time)
    write_check(CHECK_TAG, activity_name, activity_time)
    write_path(path_reverse_trackers, activity_name, limit - activity_time)
