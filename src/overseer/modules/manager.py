from overseer.config import *
from overseer.filesystem import *
from overseer.utils import *
from .supermodule import Supermodule


class Manager(Supermodule):

    def applicable(self, activity):
        return os.path.isfile(f"{path_scripts_managers}/{activity['name']}")

    def run(self, activity: {}, time: float, time_prev: float, delta: float, status: str, decisions: [], misc: {}):
        manager_return_code = run_script(f"{path_scripts_managers}/{activity['name']}", misc.get("Verbose"))

        if manager_return_code == 0:
            status, decisions = decide(STATUS.ENABLED, "Manager", decisions)
        elif manager_return_code == 1:
            status, decisions = decide(STATUS.DISABLED, "Manager", decisions)
        else:
            status, decisions = decide(status, "ERR Manager", decisions)

        return status, decisions
