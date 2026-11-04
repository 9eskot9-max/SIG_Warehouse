from datetime import date


def overlaps(start_a, end_a, start_b, end_b):
    """Return whether two inclusive assignment periods intersect."""
    start_a = _as_date(start_a)
    start_b = _as_date(start_b)
    end_a = _as_date(end_a) or date.max
    end_b = _as_date(end_b) or date.max
    return start_a <= end_b and start_b <= end_a


def _as_date(value):
    if not value:
        return None
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value)[:10])
