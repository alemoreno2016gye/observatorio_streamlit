from __future__ import annotations

from pathlib import Path

import pandas as pd

from etl.utils import ensure_dir


class RawExtractor:
    """Extract raw files and persist parquet bronze tables."""

    def __init__(self, raw_dir: Path, bronze_dir: Path) -> None:
        self.raw_dir = raw_dir
        self.bronze_dir = bronze_dir
        ensure_dir(self.bronze_dir)

    def _excel_to_parquet(self, pattern: str, output_name: str) -> Path:
        files = sorted(self.raw_dir.glob(pattern))
        if not files:
            raise FileNotFoundError(f"No files found for pattern: {pattern}")
        frames = [pd.read_excel(file) for file in files]
        data = pd.concat(frames, ignore_index=True)
        output_path = self.bronze_dir / output_name
        data.to_parquet(output_path, index=False)
        return output_path

    def extract_bce_exports(self) -> Path:
        return self._excel_to_parquet("exports/*.xlsx", "bce_exports_bronze.parquet")

    def extract_bce_imports(self) -> Path:
        return self._excel_to_parquet("imports/*.xlsx", "bce_imports_bronze.parquet")

    def extract_china_imports(self) -> Path:
        csv_path = self.raw_dir / "china_imports.csv"
        if not csv_path.exists():
            raise FileNotFoundError(f"Missing {csv_path}")
        df = pd.read_csv(csv_path)
        out = self.bronze_dir / "china_imports_bronze.parquet"
        df.to_parquet(out, index=False)
        return out

    def extract_dimensions(self) -> tuple[Path, Path]:
        product_path = self.raw_dir / "product_dictionary.csv"
        sector_path = self.raw_dir / "sector_table.csv"
        if not product_path.exists() or not sector_path.exists():
            raise FileNotFoundError("Missing product_dictionary.csv or sector_table.csv")
        product = pd.read_csv(product_path)
        sector = pd.read_csv(sector_path)
        product_out = self.bronze_dir / "product_dictionary_bronze.parquet"
        sector_out = self.bronze_dir / "sector_table_bronze.parquet"
        product.to_parquet(product_out, index=False)
        sector.to_parquet(sector_out, index=False)
        return product_out, sector_out
