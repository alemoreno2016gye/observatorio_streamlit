# Observatorio de Comercio Ecuador–China

Arquitectura de datos y aplicación analítica para monitorear comercio bilateral Ecuador–China con pipeline ETL (bronze/silver/gold) y frontend Streamlit.

## Estructura del repositorio

```text
.
├── app/
│   ├── Home.py
│   ├── data_access.py
│   └── pages/
│       ├── 1_Structure.py
│       ├── 2_Seasonality.py
│       └── 3_Opportunities_Risks.py
├── config/
│   └── settings.py
├── etl/
│   ├── extract.py
│   ├── transform.py
│   ├── load.py
│   ├── pipeline.py
│   └── utils.py
├── data/
│   ├── raw/
│   ├── silver/
│   └── gold/
└── requirements.txt
```

## Arquitectura

- **Bronze**: lectura de Excel/CSV de BCE y TradeMap, conversión a Parquet.
- **Silver**: normalización de periodos, estandarización HS, generación de `fact_trade_ecuador`, `fact_china_imports`, y `dim_sector`.
- **Gold**: tablas KPI preagregadas para visualizaciones y drill-down.

## Reglas clave implementadas

1. Parseo de periodo BCE `YYYY / MM - Mes` a `year`, `month`, `period_date`.
2. Derivación jerárquica HS desde hs10: `hs6`, `hs4`, `hs2`.
3. Mapeo dinámico de sector por rangos:
   - Expansión de `Capítulos` (e.g., `01 – 05` → 01..05).
   - Generación de dimensión `dim_sector(section_id, hs2, sector_name)`.
4. Carga de KPIs a Parquet en `data/gold`.

## Esquemas principales

### `fact_trade_ecuador` (silver)
- year, month, period_date, flow
- hs10, hs6, hs4, hs2
- sector, country_iso3, country_name
- weight_tm, value_fob, value_cif

### `fact_china_imports` (silver)
- year, hs2, country, value

### KPI tables (gold)
- `kpi_historical_series`
- `kpi_bilateral_balance`
- `kpi_country_ranking`
- `kpi_structure`
- `kpi_seasonality`
- `kpi_emerging_products`
- `kpi_china_dependency`
- `kpi_ecuador_in_china`

## Preparación de datos raw

Ubicar archivos en:
- `data/raw/exports/*.xlsx`
- `data/raw/imports/*.xlsx`
- Panel China imports en `data/raw/` (CSV o Excel). Nombres soportados incluyen `china_imports.*`, `china imports.*`, `china_import_panel.*`, `importaciones_china.*` y **`panel_trademap.*`**.
- Diccionario de productos en `data/raw/` (CSV o Excel). Nombres soportados incluyen `product_dictionary.*`, `product_dictionary_ec.*`, `diccionario_productos.*`, `diccionario_subpartidas.*` y **`diccionario_ecuador.*`**.
- Tabla de sectores en `data/raw/` (CSV o Excel). Nombres soportados incluyen `sector_table.*`, `sector_mapping.*`, `tabla_sectores.*`, `sectores.*` y **`SECTORES.*`**.

> Recomendación: aunque el pipeline detecta alias automáticamente, usa nombres estables para producción y evita caracteres especiales en nombres de archivo.

## Ejecución

Instalar dependencias:

```bash
pip install -r requirements.txt
```

Ejecutar pipeline ETL:

```bash
python -m etl.pipeline
```

Levantar aplicación:

```bash
streamlit run app/Home.py
```

## Escalabilidad y performance

- Persistencia 100% Parquet para evitar I/O costoso.
- Preagregaciones de alto costo en capa gold usando DuckDB SQL.
- `@st.cache_data` en acceso a tablas gold.
- Separación modular extract/transform/load para facilitar orquestación externa (Airflow, Prefect, Dagster).
