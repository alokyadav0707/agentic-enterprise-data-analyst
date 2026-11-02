"""Load and validate the OKF-inspired metric catalog."""
from pathlib import Path
import yaml

REQUIRED = {"name", "description", "expression", "grain", "tables", "business_rules"}

def load_catalog(path: str | Path) -> dict:
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict) or "metrics" not in data:
        raise ValueError("Catalog must contain a metrics list")
    names = set()
    for metric in data["metrics"]:
        missing = REQUIRED - set(metric)
        if missing:
            raise ValueError(f"Metric missing fields {sorted(missing)}")
        if metric["name"] in names:
            raise ValueError(f"Duplicate metric: {metric['name']}")
        names.add(metric["name"])
    return data

def retrieve_relevant(question: str, catalog: dict, limit: int = 8) -> list[dict]:
    """Simple transparent keyword retrieval; no external embedding service required."""
    words = set(question.lower().replace("-", " ").split())
    scored = []
    for metric in catalog["metrics"]:
        text = " ".join([metric["name"], metric["description"], " ".join(metric.get("synonyms", []))]).lower()
        score = sum(1 for word in words if len(word) > 2 and word in text)
        if score:
            scored.append((score, metric))
    scored.sort(key=lambda x: (-x[0], x[1]["name"]))
    return [m for _, m in scored[:limit]]
