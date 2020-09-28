import datetime as dt


def is_after(time, pivot):
    pivot_timestamp = dt.datetime.combine(dt.date.today(), dt.time.fromisoformat(pivot)).timestamp()
    return pivot_timestamp < time


def just_happened(previous_time, current_time, trigger):
    trigger_timestamp = dt.datetime.combine(dt.date.today(), dt.time.fromisoformat(trigger)).timestamp()
    return previous_time < trigger_timestamp <= current_time


def decide(to, reason, decisions):
    decisions += [f"[{str(to)}] ({reason})"]
    return to, decisions
