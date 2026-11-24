from datetime import UTC, datetime, timedelta

from tracks.clock import FakeClock, SystemClock


def test_fake_clock_advances():
    start = datetime(2026, 1, 1, tzinfo=UTC)
    clock = FakeClock(start)
    clock.advance(timedelta(minutes=30))
    assert clock.now() == start + timedelta(minutes=30)


def test_system_clock_is_timezone_aware():
    assert SystemClock().now().tzinfo is not None
