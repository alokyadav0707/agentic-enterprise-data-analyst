from src.evaluation.metrics import summarize
def test_summary_rates():
    s=summarize([{"success":True,"correct":True,"attempts":0,"latency_seconds":0.2},
                 {"success":False,"correct":False,"attempts":2,"latency_seconds":0.4}])
    assert s["execution_success_rate"] == 0.5
    assert s["result_correctness_rate"] == 0.5
