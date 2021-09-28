from overseer.config import *
from overseer.filesystem import *
from overseer.modules.limit import Limit
from overseer.modules.supermodule import Supermodule
from overseer.utils import *

CHECK_TAG = "interrupt"


class Interrupt(Supermodule):

    def applicable(self, activity):
        return "InterruptAfter" in activity

    def run(self, activity, time, time_prev, delta, status, decisions, misc):

        continuous_time = read_path(path_continuous, activity["name"])
        interrupted_for = read_path(path_interrupts, activity["name"])

        definition_interrupt_after = activity["InterruptAfter"]
        definition_interrupt_for = activity["InterruptFor"]

        # Guardian
        if not check_check(CHECK_TAG, activity["name"], interrupted_for):
            decisions.append("[INTERRUPT] Detecting a bad check, forcing a full interrupt")
            interrupted_for = definition_interrupt_for

        # Base math
        interrupted_for -= delta * (STATUS.base[status] == STATUS.DISABLED)
        continuous_time += delta * (STATUS.base[status] == STATUS.ENABLED)
        continuous_time -= delta * (STATUS.base[status] == STATUS.DISABLED)
        interrupted_for = max(0, interrupted_for)
        continuous_time = min(definition_interrupt_after, continuous_time)
        continuous_time = max(0, continuous_time)

        # If just going into interrupted
        if continuous_time >= definition_interrupt_after and not Limit.ignore(activity, time):
            continuous_time = 0
            interrupted_for = definition_interrupt_for
            status, decisions = decide(STATUS.INTERRUPTED, "InterruptBegin", decisions)

        # If currently interrupted
        if interrupted_for > 0 and not Limit.ignore(activity, time):
            continuous_time = 0
            status, decisions = decide(STATUS.INTERRUPTED, "InterruptedContinues", decisions)

        # If just leaving interrupted
        if status == STATUS.INTERRUPTED and interrupted_for == 0:
            status, decisions = decide(STATUS.DISABLED, "InterruptEnd", decisions)

        # Reset
        if "ResetOn" in activity and just_happened(time_prev, time, activity["ResetOn"]):
            continuous_time = 0
            interrupted_for = 0

        write_path(path_continuous, activity["name"], continuous_time)
        write_path(path_interrupts, activity["name"], interrupted_for)
        write_check(CHECK_TAG, activity["name"], interrupted_for)

        return status, decisions

    def reset(self, activities: []):
        for activity in activities.values():

            if not self.applicable(activity):
                continue

            write_path(path_continuous, activity["name"], 0)
            write_path(path_interrupts, activity["name"], 0)
            write_check(CHECK_TAG, activity["name"], 0)
