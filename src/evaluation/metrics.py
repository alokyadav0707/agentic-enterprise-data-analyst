"""Evaluation metric calculations."""
def summarize(rows: list[dict]) -> dict:
    n = len(rows)
    successes = sum(bool(r.get("success")) for r in rows)
    correct = sum(bool(r.get("correct")) for r in rows)
    corrections = sum(bool(r.get("correction_success")) for r in rows)
    return {
        "total_questions": n,
        "execution_successes": successes,
        "execution_success_rate": round(successes/n, 4) if n else 0.0,
        "correct_results": correct,
        "result_correctness_rate": round(correct/n, 4) if n else 0.0,
        "correction_successes": corrections,
        "mean_attempts": round(sum(r.get("attempts",0) for r in rows)/n, 3) if n else 0.0,
        "mean_latency_seconds": round(sum(r.get("latency_seconds",0) for r in rows)/n, 4) if n else 0.0,
    }
