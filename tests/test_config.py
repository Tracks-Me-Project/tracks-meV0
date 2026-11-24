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


def test_split_must_have_right_size(tmp_path: Path):
    bad = Path("config/rules.toml").read_text().replace("[70, 30]", "[50, 30, 20]")
    p = tmp_path / "rules.toml"
    p.write_text(bad)
    with pytest.raises(ValidationError):
        load_rules(p)


def test_essai_rules_valid_and_shorter():
    essai = load_rules(Path("config/rules.essai.toml"))
    assert essai.auction.durations_minutes == [1, 2, 5, 10, 30]
    assert essai.booster.minutes_per_booster == 1
    normal = load_rules()  # le reste des règles doit rester identique
    assert essai.bet == normal.bet and essai.recycling == normal.recycling


def test_rules_path_env_var(monkeypatch: pytest.MonkeyPatch):
    from tracks.config import get_rules, get_settings

    monkeypatch.setenv("TRACKS_RULES_PATH", "config/rules.essai.toml")
    get_settings.cache_clear()
    get_rules.cache_clear()
    try:
        assert get_rules().booster.minutes_per_booster == 1
    finally:  # ne pas laisser les règles d'essai en cache pour les autres tests
        monkeypatch.undo()
        get_settings.cache_clear()
        get_rules.cache_clear()
    assert get_rules().booster.minutes_per_booster == 60
