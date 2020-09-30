from overseer.config import *
from overseer.filesystem import *
from overseer.modules.supermodule import Supermodule
from overseer.utils import *


class Interrupt(Supermodule):

    def applicable(self, activity):
        return "InterruptAfter" in activity

    def run(self, activity, time, time_prev, delta, status, decisions, misc):
        continuous_time = read_path(path_continuous, activity["name"])
        interrupted_for = read_path(path_interrupts, activity["name"])

        definition_interrupt_after = activity["InterruptAfter"]
        definition_interrupt_for = activity["InterruptFor"]

        interrupted_for -= delta * (STATUS.base[status] == STATUS.DISABLED)
        continuous_time += delta * (STATUS.base[status] == STATUS.ENABLED)

        interrupted_for = max(0, interrupted_for)
        continuous_time = min(definition_interrupt_after, continuous_time)

        print(f"[DEBUG][INTERRUPT] def_interrupt_after: {definition_interrupt_after}, def_interrupt_for: {definition_interrupt_for}")
        print(f"[DEBUG][INTERRUPT] interrupted_for: {interrupted_for}, continuous_time: {continuous_time}")

        if interrupted_for > 0:
            continuous_time = 0
            status, decisions = decide(STATUS.INTERRUPTED, "InterruptedContinues", decisions)

        if continuous_time >= definition_interrupt_after:
            continuous_time = 0
            interrupted_for = definition_interrupt_for
            status, decisions = decide(STATUS.INTERRUPTED, "InterruptBegin", decisions)

        if status == STATUS.INTERRUPTED and interrupted_for == 0:
            status, decisions = decide(STATUS.DISABLED, "InterruptEnd", decisions)

        write_path(path_continuous, activity["name"], continuous_time)
        write_path(path_interrupts, activity["name"], interrupted_for)

        return status, decisions
