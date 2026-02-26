from __future__ import annotations

from pathlib import Path
from pydantic import BaseModel, Field


class PathsConfig(BaseModel):
    root: Path = Field(default_factory=lambda: Path(__file__).resolve().parents[1])
    raw: Path | None = None
    silver: Path | None = None
    gold: Path | None = None

    def model_post_init(self, __context: object) -> None:
        self.raw = self.root / "data" / "raw"
        self.silver = self.root / "data" / "silver"
        self.gold = self.root / "data" / "gold"


class ETLConfig(BaseModel):
    paths: PathsConfig = Field(default_factory=PathsConfig)
    start_year: int = 1998
    end_year: int = 2025


def get_etl_config() -> ETLConfig:
    return ETLConfig()
