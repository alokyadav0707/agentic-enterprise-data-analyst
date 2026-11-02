from pathlib import Path
from src.semantic_layer.catalog import load_catalog, retrieve_relevant
ROOT=Path(__file__).resolve().parents[1]
def test_catalog_has_at_least_15_metrics():
    catalog=load_catalog(ROOT/"semantic_layer"/"metrics.yaml")
    assert len(catalog["metrics"]) >= 15
def test_retrieval_finds_net_sales():
    catalog=load_catalog(ROOT/"semantic_layer"/"metrics.yaml")
    assert "net_sales" in [m["name"] for m in retrieve_relevant("net sales by month",catalog)]
