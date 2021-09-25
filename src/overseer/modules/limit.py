from src.overseer.config import *
from src.overseer.filesystem import *
from src.overseer.modules.supermodule import Supermodule
from src.overseer.utils import *


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

        if activity_time >= limit and not Limit.ignore(activity, time):
            status, decisions = decide(STATUS.DISABLED, "Limit", decisions)

        activity_time = min(activity_time, limit)
        write(activity["name"], limit, activity_time)

        if "ResetOn" in activity and just_happened(time_prev, time, activity["ResetOn"]):
            write(activity["name"], limit, 0)

        return status, decisions

    @staticmethod
    def ignore(activity: {}, time: float):

        if "IgnoreAfter" in activity and is_after(time, activity["IgnoreAfter"]):
            return True

        if "IgnoreBefore" in activity and is_before(time, activity["IgnoreBefore"]):
            return True

        return False

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
