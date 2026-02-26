from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import duckdb


@dataclass
class GoldBuilder:
    silver_dir: Path
    gold_dir: Path

    def run(self) -> None:
        self.gold_dir.mkdir(parents=True, exist_ok=True)
        con = duckdb.connect()
        con.execute(f"CREATE VIEW trade AS SELECT * FROM read_parquet('{self.silver_dir / 'fact_trade_ecuador_silver.parquet'}')")
        con.execute(f"CREATE VIEW china AS SELECT * FROM read_parquet('{self.silver_dir / 'fact_china_imports.parquet'}')")

        con.execute(
            f"""
            COPY (
                SELECT
                    year,
                    month,
                    period_date,
                    SUM(CASE WHEN flow='export' THEN value_fob ELSE 0 END) AS exports_fob,
                    SUM(CASE WHEN flow='import' THEN value_fob ELSE 0 END) AS imports_fob,
                    SUM(CASE WHEN flow='import' THEN value_cif ELSE 0 END) AS imports_cif,
                    SUM(CASE WHEN flow='import' THEN value_cif - value_fob ELSE 0 END) AS logistic_cost,
                    CASE
                        WHEN SUM(CASE WHEN flow='import' THEN value_fob ELSE 0 END)=0 THEN 0
                        ELSE SUM(CASE WHEN flow='import' THEN value_cif - value_fob ELSE 0 END)
                             / SUM(CASE WHEN flow='import' THEN value_fob ELSE 0 END)
                    END AS logistic_cost_ratio
                FROM trade
                GROUP BY 1,2,3
            ) TO '{self.gold_dir / 'kpi_historical_series.parquet'}' (FORMAT PARQUET)
            """
        )

        con.execute(
            f"""
            COPY (
                SELECT
                    year,
                    SUM(CASE WHEN flow='export' AND country_iso3='CHN' THEN value_fob ELSE 0 END) AS exports_to_china_fob,
                    SUM(CASE WHEN flow='import' AND country_iso3='CHN' THEN value_fob ELSE 0 END) AS imports_from_china_fob,
                    SUM(CASE WHEN flow='export' AND country_iso3='CHN' THEN value_fob ELSE 0 END)
                    - SUM(CASE WHEN flow='import' AND country_iso3='CHN' THEN value_fob ELSE 0 END) AS trade_balance_fob
                FROM trade
                GROUP BY 1
            ) TO '{self.gold_dir / 'kpi_bilateral_balance.parquet'}' (FORMAT PARQUET)
            """
        )

        con.execute(
            f"""
            COPY (
                SELECT
                    year,
                    flow,
                    country_iso3,
                    country_name,
                    SUM(value_fob) AS value_fob,
                    DENSE_RANK() OVER (PARTITION BY year, flow ORDER BY SUM(value_fob) DESC) AS ranking
                FROM trade
                GROUP BY 1,2,3,4
            ) TO '{self.gold_dir / 'kpi_country_ranking.parquet'}' (FORMAT PARQUET)
            """
        )

        con.execute(
            f"""
            COPY (
                SELECT year, sector, hs2, hs6,
                       SUM(value_fob) AS value_fob,
                       SUM(value_cif) AS value_cif,
                       SUM(weight_tm) AS weight_tm
                FROM trade
                GROUP BY 1,2,3,4
            ) TO '{self.gold_dir / 'kpi_structure.parquet'}' (FORMAT PARQUET)
            """
        )

        con.execute(
            f"""
            COPY (
                SELECT year, month, hs2, sector,
                       SUM(value_fob) AS value_fob,
                       SUM(value_cif) AS value_cif,
                       SUM(weight_tm) AS weight_tm
                FROM trade
                GROUP BY 1,2,3,4
            ) TO '{self.gold_dir / 'kpi_seasonality.parquet'}' (FORMAT PARQUET)
            """
        )

        con.execute(
            f"""
            COPY (
                WITH annual AS (
                    SELECT hs10, year, SUM(value_fob) AS annual_fob
                    FROM trade WHERE flow='export'
                    GROUP BY 1,2
                ),
                lagged AS (
                    SELECT hs10, year, annual_fob,
                           LAG(annual_fob,1) OVER(PARTITION BY hs10 ORDER BY year) AS prev_1y,
                           LAG(annual_fob,2) OVER(PARTITION BY hs10 ORDER BY year) AS prev_2y
                    FROM annual
                )
                SELECT hs10, year, annual_fob,
                       CASE WHEN prev_1y IS NULL OR prev_1y=0 THEN NULL ELSE (annual_fob/prev_1y)-1 END AS cagr_12m,
                       CASE WHEN prev_2y IS NULL OR prev_2y=0 THEN NULL ELSE POWER(annual_fob/prev_2y,0.5)-1 END AS cagr_24m,
                       COALESCE((annual_fob-prev_1y) - (prev_1y-prev_2y),0) AS acceleration,
                       0.0 AS volatility_proxy,
                       annual_fob / NULLIF(SUM(annual_fob) OVER (PARTITION BY year),0) AS share,
                       (COALESCE((annual_fob/NULLIF(prev_1y,0))-1,0)*0.35 +
                        COALESCE(POWER(annual_fob/NULLIF(prev_2y,0),0.5)-1,0)*0.25 +
                        COALESCE((annual_fob-prev_1y)-(prev_1y-prev_2y),0)*0.20 +
                        COALESCE(annual_fob / NULLIF(SUM(annual_fob) OVER (PARTITION BY year),0),0)*0.20) AS emerging_score
                FROM lagged
            ) TO '{self.gold_dir / 'kpi_emerging_products.parquet'}' (FORMAT PARQUET)
            """
        )

        con.execute(
            f"""
            COPY (
                WITH by_country AS (
                    SELECT year, hs2,
                           SUM(CASE WHEN flow='export' AND country_iso3='CHN' THEN value_fob ELSE 0 END) AS exp_china,
                           SUM(CASE WHEN flow='export' THEN value_fob ELSE 0 END) AS exp_total
                    FROM trade
                    GROUP BY 1,2
                )
                SELECT year, hs2,
                       exp_china/NULLIF(exp_total,0) AS china_share,
                       CASE WHEN exp_china/NULLIF(exp_total,0) > 0.75 THEN 1 ELSE 0 END AS dep_gt_75,
                       CASE WHEN exp_china/NULLIF(exp_total,0) > 0.50 THEN 1 ELSE 0 END AS dep_gt_50
                FROM by_country
            ) TO '{self.gold_dir / 'kpi_china_dependency.parquet'}' (FORMAT PARQUET)
            """
        )

        con.execute(
            f"""
            COPY (
                WITH ec_share AS (
                    SELECT c.year, c.hs2,
                           SUM(CASE WHEN c.country='Ecuador' THEN c.value ELSE 0 END) / NULLIF(SUM(c.value),0) AS ecuador_share,
                           SUM(c.value) AS china_total_import
                    FROM china c
                    GROUP BY 1,2
                )
                SELECT *,
                       DENSE_RANK() OVER (PARTITION BY year, hs2 ORDER BY ecuador_share DESC) AS ecuador_rank
                FROM ec_share
            ) TO '{self.gold_dir / 'kpi_ecuador_in_china.parquet'}' (FORMAT PARQUET)
            """
        )

        con.close()
