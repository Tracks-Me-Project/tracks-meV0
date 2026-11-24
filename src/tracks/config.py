"""Configuration centralisée : règles du jeu (config/rules.toml) et réglages d'environnement."""

import tomllib
from functools import lru_cache
from pathlib import Path

from pydantic import BaseModel, ConfigDict, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

RULES_PATH = Path(__file__).resolve().parents[2] / "config" / "rules.toml"


class _Frozen(BaseModel):
    # extra="forbid" : une faute de frappe dans le TOML fait échouer le démarrage
    model_config = ConfigDict(frozen=True, extra="forbid")


class AccountRules(_Frozen):
    starting_coins: int


class AuctionRules(_Frozen):
    durations_minutes: list[int]
    min_raise_percent: int
    max_open_per_account: int
    cancel_window_percent: int


class BetRules(_Frozen):
    stake_percent_of_start_price: int
    max_open_per_account: int
    close_at_percent_of_duration: int
    podium_share_percent: int
    podium_split_percent: list[int]
    two_bettors_split_percent: list[int]
    payout_cap_multiple: int

    @model_validator(mode="after")
    def _splits_sum_to_100(self) -> "BetRules":
        for split in (self.podium_split_percent, self.two_bettors_split_percent):
            if sum(split) != 100:
                raise ValueError(f"une répartition doit totaliser 100 : {split}")
        return self


class BoosterRules(_Frozen):
    tracks_per_booster: int
    minutes_per_booster: int
    max_stock: int


class RecyclingRules(_Frozen):
    coins_per_track: int
    daily_cap: int


class GameRules(_Frozen):
    account: AccountRules
    auction: AuctionRules
    bet: BetRules
    booster: BoosterRules
    recycling: RecyclingRules


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="TRACKS_", env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://tracks:tracks@localhost:5442/tracks"


def load_rules(path: Path = RULES_PATH) -> GameRules:
    with path.open("rb") as f:
        return GameRules.model_validate(tomllib.load(f))


@lru_cache
def get_rules() -> GameRules:
    return load_rules()


@lru_cache
def get_settings() -> Settings:
    return Settings()
