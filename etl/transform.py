from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from etl.utils import normalize_hs, parse_period, safe_numeric


@dataclass
class Transformer:
    bronze_dir: Path
    silver_dir: Path

    def _expand_sector_ranges(self, sector_table: pd.DataFrame) -> pd.DataFrame:
        records: list[dict[str, str]] = []
        for _, row in sector_table.iterrows():
            section_id = str(row["Sección"]).strip()
            sector_name = str(row["Sector/Industria"]).strip()
            raw_chapters = str(row["Capítulos"]).replace("–", "-").replace("—", "-").strip()
            if "-" in raw_chapters:
                start, end = [part.strip() for part in raw_chapters.split("-")]
                for chapter in range(int(start), int(end) + 1):
                    records.append(
                        {"section_id": section_id, "hs2": str(chapter).zfill(2), "sector_name": sector_name}
                    )
            else:
                records.append(
                    {
                        "section_id": section_id,
                        "hs2": str(int(raw_chapters)).zfill(2),
                        "sector_name": sector_name,
                    }
                )
        return pd.DataFrame(records).drop_duplicates(["hs2"])

    def _normalize_trade(
        self,
        source: pd.DataFrame,
        flow: str,
        country_code_col: str,
        country_name_col: str,
        value_col: str,
        fob_col: str | None = "FOB",
    ) -> pd.DataFrame:
        year_month = source["Período"].map(parse_period)
        normalized = pd.DataFrame(
            {
                "year": year_month.map(lambda x: x[0]),
                "month": year_month.map(lambda x: x[1]),
                "period_date": year_month.map(lambda x: x[2]),
                "flow": flow,
                "hs10": source["Código Subpartida"].map(lambda x: normalize_hs(x, 10)),
                "country_iso3": source[country_code_col].astype(str).str.upper(),
                "country_name": source[country_name_col].astype(str),
                "weight_tm": safe_numeric(source["TM (Peso Neto)"]),
                "value_fob": safe_numeric(source[fob_col]) if fob_col else 0.0,
                "value_cif": safe_numeric(source[value_col]) if value_col == "CIF" else 0.0,
            }
        )
        normalized["hs6"] = normalized["hs10"].str[:6]
        normalized["hs4"] = normalized["hs10"].str[:4]
        normalized["hs2"] = normalized["hs10"].str[:2]
        return normalized

    def run(self) -> None:
        exports = pd.read_parquet(self.bronze_dir / "bce_exports_bronze.parquet")
        imports = pd.read_parquet(self.bronze_dir / "bce_imports_bronze.parquet")
        sector = pd.read_parquet(self.bronze_dir / "sector_table_bronze.parquet")

        exports_norm = self._normalize_trade(
            exports,
            flow="export",
            country_code_col="Código País Destino",
            country_name_col="País Destino",
            value_col="FOB",
        )
        imports_norm = self._normalize_trade(
            imports,
            flow="import",
            country_code_col="Código País Origen",
            country_name_col="País Origen",
            value_col="CIF",
            fob_col="FOB",
        )

        dim_sector = self._expand_sector_ranges(sector)
        trade = pd.concat([exports_norm, imports_norm], ignore_index=True)
        trade = trade.merge(dim_sector, on="hs2", how="left")
        trade["sector"] = trade["sector_name"].fillna("No clasificado")

        self.silver_dir.mkdir(parents=True, exist_ok=True)
        trade.to_parquet(self.silver_dir / "fact_trade_ecuador_silver.parquet", index=False)
        dim_sector.to_parquet(self.silver_dir / "dim_sector.parquet", index=False)

        china = pd.read_parquet(self.bronze_dir / "china_imports_bronze.parquet")
        china["hs2"] = china["product"].astype(str).str.extract(r"^(\d{2})", expand=False)
        china["value"] = safe_numeric(china["value"])
        china = china.rename(columns={"pais": "country"})[["year", "hs2", "country", "value"]]
        china.to_parquet(self.silver_dir / "fact_china_imports.parquet", index=False)
