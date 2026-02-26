from __future__ import annotations

from config.settings import get_etl_config
from etl.extract import RawExtractor
from etl.transform import Transformer
from etl.load import GoldBuilder
from etl.utils import ensure_dir


def run_pipeline() -> None:
    cfg = get_etl_config()
    bronze_dir = cfg.paths.silver / "bronze"
    ensure_dir(bronze_dir)
    ensure_dir(cfg.paths.silver)
    ensure_dir(cfg.paths.gold)

    extractor = RawExtractor(cfg.paths.raw, bronze_dir)
    extractor.extract_bce_exports()
    extractor.extract_bce_imports()
    extractor.extract_china_imports()
    extractor.extract_dimensions()

    transformer = Transformer(bronze_dir=bronze_dir, silver_dir=cfg.paths.silver)
    transformer.run()

    gold = GoldBuilder(silver_dir=cfg.paths.silver, gold_dir=cfg.paths.gold)
    gold.run()


if __name__ == "__main__":
    run_pipeline()
