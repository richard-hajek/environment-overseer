from overseer.config import *
from overseer.utils import *

from .supermodule import *


class AutoTrigger(Supermodule):

    def applicable(self, activity):
        return "AutoStart" in activity and "AutoStop" in activity

    def run(self, activity: {}, time: float, time_prev: float, delta: float, status: str, decisions: [], misc: {}):
        if "AutoStart" in activity and just_happened(time_prev, time, activity["AutoStart"]):
            status, decisions = decide(STATUS.ENABLED, "AutoStart", decisions)

        if "AutoStop" in activity and just_happened(time_prev, time, activity["AutoStop"]):
            status, decisions = decide(STATUS.DISABLED, "AutoStart", decisions)

        return status, decisions

    @staticmethod
    def self_test(add_activity, set_time, set_activity, run_command, activity_assert):

        routines = []

        routines.append(
            [
                add_activity({"Limit": "1H", "AutoStart": "01:00", "AutoStop": "01:30"}),
                set_time("00:55"),
                activity_assert("disabled"),
                set_time("01:10"),
                activity_assert("enabled"),
                set_time("01:40"),
                activity_assert("disabled")
            ]
        )

        return routines
