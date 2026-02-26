from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st


GOLD_DIR = Path(__file__).resolve().parents[1] / "data" / "gold"


@st.cache_data(show_spinner=False)
def load_gold(table: str) -> pd.DataFrame:
    path = GOLD_DIR / f"{table}.parquet"
    if not path.exists():
        return pd.DataFrame()
    return pd.read_parquet(path)
