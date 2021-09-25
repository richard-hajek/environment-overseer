from src.overseer.config import *
from src.overseer.utils import *
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
