from overseer.config import *
from overseer.filesystem import *
from overseer.modules.supermodule import Supermodule
from overseer.modules.limit import write


class Recharge(Supermodule):

    def applicable(self, activity):
        return "Limit" in activity and "Recharge" in activity

    def run(self, activity: {}, time: float, time_prev: float, delta: float, status: str, decisions: [], misc: {}):
        if status != STATUS.ENABLED:
            recharge_time = activity["Recharge"]
            limit = activity["Limit"]
            activity_time = read_path(path_trackers, activity["name"])

            activity_time -= (limit / recharge_time) * delta
            activity_time = max(0, activity_time)

            write(activity["name"], limit, activity_time)

        return status, decisions
