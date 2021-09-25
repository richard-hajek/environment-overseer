import os.path
import overseer.config as cfg


class Resetter:

    def __init__(self):
        self.scanned = {}

    def scan(self):

        for act_name in os.listdir(cfg.path_activities):
            with open(os.path.join(cfg.path_activities, act_name)) as f:
                self.scanned[f"activities/{act_name}"] = f.readlines()

        for act_name in os.listdir(cfg.path_scripts_dual):
            with open(os.path.join(cfg.path_scripts_dual, act_name)) as f:
                self.scanned[f"dual/{act_name}"] = f.readlines()

    def write(self):
        for k, v in self.scanned.items():
            with open(os.path.join(cfg.path_home, k), "w") as f:
                f.writelines(v)