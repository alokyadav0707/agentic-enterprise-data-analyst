import argparse, json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.evaluation.runner import run_benchmark
if __name__ == "__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--mode",choices=["mock","groq"],default="mock")
    p.add_argument("--no-correction",action="store_true")
    p.add_argument("--output-dir",default="reports")
    args=p.parse_args()
    summary,_=run_benchmark(args.mode,not args.no_correction,output_dir=args.output_dir)
    print(json.dumps(summary,indent=2))
