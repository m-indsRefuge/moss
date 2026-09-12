from datetime import datetime, timezone

from moss.clock import RealClock, SimClock


def test_real_clock_returns_aware_utc_between_samples():
    before = datetime.now(timezone.utc)
    now = RealClock().now()
    after = datetime.now(timezone.utc)
    assert before <= now <= after
    assert now.tzinfo is not None


def test_sim_clock_holds_still_until_advanced():
    c = SimClock()
    first = c.now()
    assert c.now() == first


def test_sim_clock_advance_mirrors_timedelta():
    c = SimClock(start=datetime(2025, 1, 1, 9, 0, tzinfo=timezone.utc))
    c.advance(hours=240, minutes=30)
    assert c.now() == datetime(2025, 1, 11, 9, 30, tzinfo=timezone.utc)


def test_sim_clock_accepts_explicit_start():
    start = datetime(2020, 6, 15, 12, 0, tzinfo=timezone.utc)
    assert SimClock(start).now() == start