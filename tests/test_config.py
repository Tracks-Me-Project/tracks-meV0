from pathlib import Path

import pytest
from pydantic import ValidationError

from tracks.config import load_rules


def test_rules_loaded_from_toml():
    rules = load_rules()
    assert rules.auction.durations_minutes == [30, 60, 180, 360, 720]
    assert rules.bet.podium_split_percent == [50, 30, 20]
    assert rules.recycling.daily_cap == 50


def test_split_must_total_100(tmp_path: Path):
    bad = Path("config/rules.toml").read_text().replace("[50, 30, 20]", "[50, 30, 30]")
    p = tmp_path / "rules.toml"
    p.write_text(bad)
    with pytest.raises(ValidationError):
        load_rules(p)


def test_unknown_key_rejected(tmp_path: Path):
    p = tmp_path / "rules.toml"
    p.write_text(Path("config/rules.toml").read_text() + "\n[bet2]\nx = 1\n")
    with pytest.raises(ValidationError):
        load_rules(p)
