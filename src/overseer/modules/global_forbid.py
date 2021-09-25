from src.overseer.config import *
from src.overseer.utils import *
from .supermodule import *


class GlobalForbid(Supermodule):

    def applicable(self, activity):
        return "GlobalForbid" in activity

    def run(self, activity, time, time_prev, delta, status, decisions, misc):
        if "GlobalForbid" in activity:
            status, decisions = decide(STATUS.DISABLED, "Globally Forbidden", decisions)

        return status, decisions
