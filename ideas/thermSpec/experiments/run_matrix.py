"""Persisted sequential matrix with a cool-start gate and resumable runs."""
import argparse
import importlib
import itertools
import json
from datetime import datetime, timezone
from pathlib import Path

from .core.state_gate import wait_for_cool
from .core.storage import append_jsonl, write_json
from .run_once import run


def expand(config):
    for repeat, profile in itertools.product(range(config["repeats"]), config["frequency_profiles"]):
        run_id = f"{config['study_id']}-{profile['name']}-r{repeat + 1:02d}"
        resolved = {key: value for key, value in config.items()
                    if key not in ("frequency_profiles", "repeats", "cool_gate")}
        resolved["frequency_caps_khz"] = profile["caps_khz"]
        resolved["profile_name"] = profile["name"]
        yield run_id, resolved


def execute(config):
    if config["repeats"] < 1 or not config["frequency_profiles"]:
        raise ValueError("Matrix requires positive repeats and at least one frequency profile")
    output_root = Path(config["output_root"])
    output_root.mkdir(parents=True, exist_ok=True)
    jobs = list(expand(config))
    write_json(output_root / "matrix.json", {"jobs": [job_id for job_id, _ in jobs], "config": config})
    results = {}
    for run_id, resolved in jobs:
        status_path = output_root / run_id / "status.json"
        if status_path.exists() and json.loads(status_path.read_text(encoding="utf-8")).get("state") == "PLOTTED":
            results[run_id] = "SKIPPED_COMPLETE"
            continue
        if (output_root / run_id).exists():
            results[run_id] = "SKIPPED_INCOMPLETE_INSPECT_MANUALLY"
            continue
        try:
            wait_for_cool(config["adb_path"], config["cool_gate"],
                          on_sample=lambda reading: append_jsonl(output_root / "cooldown.jsonl",
                              {"run_id": run_id, "utc": datetime.now(timezone.utc).isoformat(), **reading}))
            run(resolved, run_id)
            results[run_id] = "PLOTTED"
        except Exception as exc:
            results[run_id] = f"FAILED: {exc}"
        write_json(output_root / "matrix_status.json", results)
    if config.get("postprocess") and all(value in ("PLOTTED", "SKIPPED_COMPLETE") for value in results.values()):
        module_name, function_name = config["postprocess"].split(":", 1)
        function = getattr(importlib.import_module(module_name), function_name)
        function(output_root)
    return results


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True, type=Path)
    args = parser.parse_args()
    config = json.loads(args.config.read_text(encoding="utf-8"))
    print(json.dumps(execute(config), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
