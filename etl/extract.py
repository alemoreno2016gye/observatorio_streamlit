from __future__ import annotations

import re
from pathlib import Path

import pandas as pd

from etl.utils import ensure_dir


class RawExtractor:
    """Extract raw files and persist parquet bronze tables."""

    def __init__(self, raw_dir: Path, bronze_dir: Path) -> None:
        self.raw_dir = raw_dir
        self.bronze_dir = bronze_dir
        ensure_dir(self.bronze_dir)

    @staticmethod
    def _normalize_name(name: str) -> str:
        return re.sub(r"[^a-z0-9]", "", name.lower())

    def _read_tabular(self, file_path: Path) -> pd.DataFrame:
        suffix = file_path.suffix.lower()
        if suffix in {".xlsx", ".xls"}:
            return pd.read_excel(file_path)
        if suffix == ".csv":
            return pd.read_csv(file_path)
        raise ValueError(f"Unsupported file format: {file_path}")

    def _find_first_file(self, candidates: list[str], glob_patterns: list[str] | None = None) -> Path:
        # 1) Exact candidate filenames
        for name in candidates:
            path = self.raw_dir / name
            if path.exists():
                return path

        # 2) Pattern search
        if glob_patterns:
            for pattern in glob_patterns:
                matches = sorted(self.raw_dir.glob(pattern))
                if matches:
                    return matches[0]

        raise FileNotFoundError(
            f"No source file found. Tried names={candidates} patterns={glob_patterns or []}"
        )

    def _find_by_alias(
        self,
        aliases: list[str],
        allowed_exts: set[str] | None = None,
    ) -> Path:
        allowed_exts = allowed_exts or {".xlsx", ".xls", ".csv"}
        normalized_aliases = [self._normalize_name(alias) for alias in aliases]

        files = sorted([p for p in self.raw_dir.iterdir() if p.is_file()])
        for file in files:
            if file.suffix.lower() not in allowed_exts:
                continue
            normalized_stem = self._normalize_name(file.stem)
            if any(alias in normalized_stem for alias in normalized_aliases):
                return file

        raise FileNotFoundError(
            f"No alias match found for {aliases} in {self.raw_dir}"
        )

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
        try:
            source = self._find_first_file(
                candidates=[
                    "china_imports.csv",
                    "china_imports.xlsx",
                    "china imports.csv",
                    "china imports.xlsx",
                    "china_import_panel.csv",
                    "china_import_panel.xlsx",
                    "importaciones_china.csv",
                    "importaciones_china.xlsx",
                ],
                glob_patterns=[
                    "*china*import*.csv",
                    "*china*import*.xlsx",
                    "*import*china*.csv",
                    "*import*china*.xlsx",
                ],
            )
        except FileNotFoundError:
            source = self._find_by_alias(["panel_trademap", "trademap", "china imports", "importaciones china"])

        df = self._read_tabular(source)
        out = self.bronze_dir / "china_imports_bronze.parquet"
        df.to_parquet(out, index=False)
        return out

    def extract_dimensions(self) -> tuple[Path, Path]:
        try:
            product_path = self._find_first_file(
                candidates=[
                    "product_dictionary.csv",
                    "product_dictionary.xlsx",
                    "product_dictionary_ec.csv",
                    "product_dictionary_ec.xlsx",
                    "diccionario_productos.csv",
                    "diccionario_productos.xlsx",
                    "diccionario_subpartidas.csv",
                    "diccionario_subpartidas.xlsx",
                ],
                glob_patterns=[
                    "*product*dict*.csv",
                    "*product*dict*.xlsx",
                    "*diccionario*product*.csv",
                    "*diccionario*product*.xlsx",
                ],
            )
        except FileNotFoundError:
            product_path = self._find_by_alias(["diccionario_ecuador", "diccionario", "product dictionary"])

        try:
            sector_path = self._find_first_file(
                candidates=[
                    "sector_table.csv",
                    "sector_table.xlsx",
                    "sector_mapping.csv",
                    "sector_mapping.xlsx",
                    "tabla_sectores.csv",
                    "tabla_sectores.xlsx",
                    "sectores.csv",
                    "sectores.xlsx",
                    "SECTORES.xlsx",
                ],
                glob_patterns=[
                    "*sector*table*.csv",
                    "*sector*table*.xlsx",
                    "*sector*map*.csv",
                    "*sector*map*.xlsx",
                    "*tabla*sector*.csv",
                    "*tabla*sector*.xlsx",
                    "*SECTOR*.xlsx",
                ],
            )
        except FileNotFoundError:
            sector_path = self._find_by_alias(["sectores", "tabla sectores", "sector table", "sector mapping"])

        product = self._read_tabular(product_path)
        sector = self._read_tabular(sector_path)
        product_out = self.bronze_dir / "product_dictionary_bronze.parquet"
        sector_out = self.bronze_dir / "sector_table_bronze.parquet"
        product.to_parquet(product_out, index=False)
        sector.to_parquet(sector_out, index=False)
        return product_out, sector_out
