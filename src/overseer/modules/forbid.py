from overseer.config import *
from overseer.utils import *
from .supermodule import *


class ForbidActivity(Supermodule):

    def applicable(self, activity):
        return "ForbidBefore" in activity and "ForbidAfter" in activity

    def run(self, activity, time, time_prev, delta, status, decisions, misc):
        if ("ForbidAfter" in activity and is_after(time, activity["ForbidAfter"])) or \
                ("ForbidBefore" in activity and is_before(time, activity["ForbidBefore"])):
            status, decisions = decide(STATUS.DISABLED, "Forbidden", decisions)

        return status, decisions

    @staticmethod
    def self_test(add_activity, set_time, set_activity, run_command, activity_assert):
        routines = [[
            add_activity({"Limit": "10H", "ForbidBefore": "01:00", "ForbidAfter": "10:00"}),
            run_command("cat /etc/overseer/activities/activity.json"),

            # Activity forbidden before 1AM
            set_time("00:55"),
            run_command("cat /etc/overseer/activities/activity.json"),
            set_activity("enabled"),
            run_command("cat /etc/overseer/activities/activity.json"),
            activity_assert("disabled"),
            run_command("cat /etc/overseer/activities/activity.json"),

            # Activity free after 1AM
            set_time("01:10"),
            set_activity("enabled"),
            activity_assert("enabled"),

            # Activity forbidden after 11PM
            set_time("11:00"),
            activity_assert("disabled"),

            # Attempt to enable
            set_activity("enabled"),
            activity_assert("disabled")
        ]]

        return routines
