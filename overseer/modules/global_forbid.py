from overseer.filesystem import *
from overseer.config import *
from overseer.utils import *
from .supermodule import *


class ForbidActivity(Supermodule):

    def applicable(self, activity):
        return "ForceForbid" in activity

    def run(self, activity, time, time_prev, delta, status, decisions, misc):

        if "ForceForbid" in activity:
            status, decisions = decide(STATUS.DISABLED, "Globally Forbidden", decisions)

        return status, decisions
