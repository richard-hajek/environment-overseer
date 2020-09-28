from overseer.config import *
from overseer.utils import *
from overseer.filesystem import *
from .supermodule import *
import os


class PreCheck(Supermodule):

    def applicable(self, activity):
        return os.path.isfile(f"{path_scripts_checks}/{activity['name']}")

    def run(self, activity: {}, time: float, time_prev: float, delta: float, status: str, decisions: [], misc: {}):
        check_return_code = run_script(f"{path_scripts_checks}/{activity['name']}", misc["verbose"])
        if check_return_code == 0:
            status, decisions = decide(STATUS.ENABLED, "PREV SCRIPT", decisions)
        elif check_return_code == 1:
            status, decisions = decide(STATUS.DISABLED, "PREV SCRIPT", decisions)

        return status, decisions
