# Evaluation methodology

The benchmark includes 50 questions spanning simple, intermediate, and complex query patterns. Each case has reference SQL executed against the generated database. Results are compared after conversion to string values; this is intentionally transparent but may be strict for floating-point formatting and row ordering.

Metrics:
- **Execution success rate:** successful executions / all benchmark cases.
- **Result correctness rate:** exact result matches / all cases.
- **Correction success:** successful queries that required at least one correction.
- **Mean attempts:** average correction attempts.
- **Mean latency:** wall-clock time per question.

Run `python scripts/run_evaluation.py --mode mock` and compare with `python scripts/run_evaluation.py --mode mock --no-correction`. Each run overwrites output files in the chosen report directory. Run Groq mode separately after configuring credentials. Do not compare runs unless database seed, benchmark, model, settings, and environment are recorded. No performance claims are pre-filled.
