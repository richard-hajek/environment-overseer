from src.overseer.config import *
from src.overseer.utils import *
from .supermodule import *


class ForbidActivity(Supermodule):

    def applicable(self, activity):
        return "ForbidBefore" in activity and "ForbidAfter" in activity

    def run(self, activity, time, time_prev, delta, status, decisions, misc):
        if ("ForbidAfter" in activity and is_after(time, activity["ForbidAfter"])) or \
                ("ForbidBefore" in activity and is_before(time, activity["ForbidBefore"])):
            status, decisions = decide(STATUS.DISABLED, "Forbidden", decisions)

        return status, decisions
