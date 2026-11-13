"""Run a phone-draft/Orin-target correctness smoke test in the Jetson CUDA container.

Requires the D-PROMISE `src/dpromise` package and frozen Spec-Bench data alongside
this file in an isolated `repro` copy. See SETUP.md.
"""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import torch
from transformers import AutoTokenizer

from dpromise.coordinator import run_comparison
from dpromise.target import load_cuda_model


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", required=True)
    parser.add_argument("--draft-url", default="http://127.0.0.1:18082")
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--k", type=int, default=2)
    parser.add_argument("--max-new-tokens", type=int, default=8)
    args = parser.parse_args()
    if args.k < 1 or args.max_new_tokens < 1:
        parser.error("k and max-new-tokens must be positive")

    rows = [json.loads(line) for line in (ROOT / "data/specbench_4task_prompts.jsonl").read_text(encoding="utf-8").splitlines()]
    selected = {}
    for row in rows:
        if row["split"] == "calibration":
            selected.setdefault(row["task_family"], row)

    tokenizer = AutoTokenizer.from_pretrained(args.model, local_files_only=True)
    model = load_cuda_model(args.model)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as output:
        for row in selected.values():
            result = run_comparison(
                model, tokenizer, row["prompt_id"], row["task_family"], row["prompt"],
                "llama", args.draft_url, args.k, args.max_new_tokens,
            )
            output.write(json.dumps(result, ensure_ascii=False) + "\n")
            output.flush()
            print(json.dumps({
                "prompt_id": row["prompt_id"],
                "exact_match": result["speculative"]["exact_match"],
                "target_ms": round(result["target_only"]["total_ms"], 1),
                "spec_ms": round(result["speculative"]["total_ms"], 1),
                "target_gpu": torch.cuda.get_device_name(0),
            }), flush=True)


if __name__ == "__main__":
    main()
