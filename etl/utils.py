from __future__ import annotations

import re
from pathlib import Path

import pandas as pd


PERIOD_PATTERN = re.compile(r"(?P<year>\d{4})\s*/\s*(?P<month>\d{2})")


def normalize_hs(code: object, width: int) -> str:
    if pd.isna(code):
        return ""
    digits = re.sub(r"\D", "", str(code))
    return digits[:width].zfill(width) if digits else ""


def parse_period(period_text: str) -> tuple[int, int, pd.Timestamp]:
    match = PERIOD_PATTERN.search(str(period_text))
    if not match:
        raise ValueError(f"Invalid period format: {period_text}")
    year = int(match.group("year"))
    month = int(match.group("month"))
    return year, month, pd.Timestamp(year=year, month=month, day=1)


def safe_numeric(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series.astype(str).str.replace(",", "", regex=False), errors="coerce").fillna(0.0)


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
