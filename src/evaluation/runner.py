"""Run the benchmark and export actual observed results."""
import json, time
from pathlib import Path
import pandas as pd
from src.agent.workflow import AnalystAgent
from src.database.executor import execute_sql
from src.config import DATABASE_PATH

def run_benchmark(mode="mock", correction=True, benchmark_path=None, output_dir="reports"):
    root = Path(__file__).resolve().parents[2]
    benchmark_path = Path(benchmark_path or root/"benchmarks"/"questions.json")
    cases = json.loads(benchmark_path.read_text(encoding="utf-8"))
    agent = AnalystAgent(mode=mode, correction_enabled=correction)
    rows = []
    for case in cases:
        start = time.perf_counter()
        result = agent.ask(case["question"])
        correct = False
        expected = case.get("expected_sql")
        if result["success"] and expected:
            try:
                actual_df = execute_sql(result["sql"], DATABASE_PATH)
                expected_df = execute_sql(expected, DATABASE_PATH)
                # Stable comparison: sort by columns/values after rounding numeric values.
                actual = actual_df.fillna("").astype(str).values.tolist()
                target = expected_df.fillna("").astype(str).values.tolist()
                correct = actual == target
            except Exception:
                correct = False
        rows.append({"id":case["id"],"difficulty":case["difficulty"],"question":case["question"],
                     "success":result["success"],"correct":correct,"correction_success":bool(result["success"] and result["attempts"]>0),
                     "attempts":result["attempts"],"latency_seconds":round(time.perf_counter()-start,4),
                     "sql":result["sql"],"error":result["error"]})
    out = Path(output_dir); out.mkdir(parents=True, exist_ok=True)
    df = pd.DataFrame(rows)
    df.to_csv(out/"evaluation_results.csv", index=False)
    from src.evaluation.metrics import summarize
    summary = summarize(rows)
    summary["mode"] = mode
    summary["correction_enabled"] = correction
    (out/"evaluation_summary.json").write_text(json.dumps(summary,indent=2),encoding="utf-8")
    return summary, rows
