
from overseer.filesystem import *
from overseer.config import *
from overseer.utils import *
from .supermodule import *


path_scripts_block=f"{path_home}/scripts/block"


class ForcedActivity(Supermodule):

    def prepare(self):
        create_folders_if_non_existent([path_scripts_block])

    def applicable(self, activity):
        return "ForcedAt" in activity and "Goal" in activity

    def run(self, activity, time, time_prev, delta, status, decisions, misc):
        if is_after(activity["ForcedAt"], time) and read_path(path_trackers, activity["name"]) < activity["Goal"]:
            status, decisions = decide(STATUS.FORCED, "ForcedAt", decisions)
            run("BLOCK", path_scripts_block, activity["name"], misc["verbose"])

        return status, decisions
