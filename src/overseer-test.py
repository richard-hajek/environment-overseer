import unittest
from overseer import *  # For some reason PyCharm detects Unresolved reference, but file execution works fine


class OverseerTest(unittest.TestCase):

    def test_auto_triggers(self):
        self.small_trigger_test("10:00", "10:02", "10:01", True)
        self.small_trigger_test("0:00", "23:00", "10:01", True)
        self.small_trigger_test("10:00", "10:02", "10:10", False)

    def small_trigger_test(self, time_a, time_b, trigger, should_trigger):
        time_a = datetime.datetime.strptime(time_a, "%H:%M").time()
        time_b = datetime.datetime.strptime(time_b, "%H:%M").time()
        assert should_trigger == process_auto_trigger(time_a, time_b, trigger)

    def test_recharge(self):
        assert 0 == process_recharge(60, STATUS.ENABLED, 3600, 3600)
        assert 60 == process_recharge(60, STATUS.DISABLED, 3600, 3600)
        assert 30 == process_recharge(60, STATUS.DISABLED, 7200, 3600)
        assert 120 == process_recharge(60, STATUS.DISABLED, 3600, 7200)
        assert 120 == process_recharge(60, STATUS.READY, 3600, 7200)

    def test_decisions(self):
        assert ACTION.ENABLE == process_decision(STATUS.ENABLED, STATUS.DISABLED, False)
        assert ACTION.IDLE == process_decision(STATUS.DISABLED, STATUS.DISABLED, False)
        assert ACTION.ENABLE == process_decision(STATUS.READY, STATUS.DISABLED, False)
        assert ACTION.IDLE == process_decision(STATUS.ENABLED, STATUS.ENABLED, False)
        assert ACTION.DISABLE == process_decision(STATUS.DISABLED, STATUS.ENABLED, False)
        assert ACTION.IDLE == process_decision(STATUS.READY, STATUS.ENABLED, False)
        assert ACTION.IDLE == process_decision(STATUS.ENABLED, STATUS.READY, False)
        assert ACTION.DISABLE == process_decision(STATUS.DISABLED, STATUS.READY, False)
        assert ACTION.IDLE == process_decision(STATUS.READY, STATUS.READY, False)

    def test_limit(self):
        assert (3600, False) == process_limit(0, 3600, 3600, STATUS.DISABLED)
        assert (3600, False) == process_limit(0, 3600, 3600, STATUS.ENABLED)
        assert (3600, False) == process_limit(0, 3600, 3600, STATUS.READY)

        assert (3600, True) == process_limit(0, 3600, 3601, STATUS.DISABLED)
        assert (3600, True) == process_limit(0, 3600, 3601, STATUS.ENABLED)
        assert (3600, True) == process_limit(0, 3600, 3601, STATUS.READY)

        assert (3660, False) == process_limit(60, 3600, 3660, STATUS.ENABLED)
        assert (3660, True) == process_limit(60, 3600, 3670, STATUS.ENABLED)
        assert (3601, False) == process_limit(60, 3600, 3601, STATUS.ENABLED)

    def test_process_activity(self):
        decision, current_state, decisions, new_activity_time = process_activity(0, 60, STATUS.DISABLED, 0, 120, None, True, [])
        assert current_state == STATUS.ENABLED

        decision, current_state, decisions, new_activity_time = process_activity(0, 60, STATUS.ENABLED, 120, 120, None, True, [])
        assert current_state == STATUS.DISABLED


if __name__ == '__main__':
    unittest.main()
