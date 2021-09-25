class Supermodule:

    def prepare(self):
        pass

    def applicable(self, activity):
        return True

    def run(self, activity: {}, time: float, time_prev: float, delta: float, status: str, decisions: [], misc: {}):
        return status, decisions

    def reset(self, activities: []):
        pass
