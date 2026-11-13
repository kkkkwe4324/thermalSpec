"""Persisted sequential matrix with a cool-start gate and resumable runs."""
import argparse
import importlib
import itertools
import json
from datetime import datetime, timezone
from pathlib import Path

from .core.config import load_project
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
    _, project_hash = load_project(config.get("project_config"))
    jobs = list(expand(config))
    manifest = output_root / f"{config['study_id']}-matrix.json"
    if manifest.exists():
        previous = json.loads(manifest.read_text(encoding="utf-8"))
        if previous.get("project_sha256") is None and previous["config"] == config:
            hashes = set()
            for old_run_id in previous["jobs"]:
                old_config_path = output_root / old_run_id / "config.resolved.json"
                if old_config_path.exists():
                    hashes.add(json.loads(old_config_path.read_text(encoding="utf-8")).get("project_sha256"))
            if hashes == {project_hash}:
                previous["project_sha256"] = project_hash
                write_json(manifest, previous)
        if previous["config"] != config or previous.get("project_sha256") != project_hash:
            raise ValueError("Matrix or project config changed for this study_id; use a new study_id")
    else:
        write_json(manifest, {"jobs": [job_id for job_id, _ in jobs], "config": config,
                              "project_sha256": project_hash})
    results = {}
    for run_id, resolved in jobs:
        status_path = output_root / run_id / "status.json"
        if status_path.exists():
            old_state = json.loads(status_path.read_text(encoding="utf-8")).get("state")
            if old_state in ("PLOTTED", "SAVED", "STOPPED"):
                results[run_id] = "SKIPPED_COMPLETE" if old_state != "STOPPED" else "SKIPPED_STOPPED"
                continue
        if (output_root / run_id).exists():
            results[run_id] = "SKIPPED_INCOMPLETE_INSPECT_MANUALLY"
            continue
        try:
            wait_for_cool(config["adb_path"], config["cool_gate"], serial=config.get("adb_serial"),
                          on_sample=lambda reading: append_jsonl(output_root / f"{config['study_id']}-cooldown.jsonl",
                              {"run_id": run_id, "utc": datetime.now(timezone.utc).isoformat(), **reading}))
            run(resolved, run_id)
            results[run_id] = json.loads(status_path.read_text(encoding="utf-8"))["state"]
        except Exception as exc:
            results[run_id] = f"FAILED: {exc}"
        write_json(output_root / f"{config['study_id']}-matrix_status.json", results)
    if config.get("postprocess") and all(value in ("PLOTTED", "SAVED", "STOPPED", "SKIPPED_COMPLETE", "SKIPPED_STOPPED") for value in results.values()):
        module_name, function_name = config["postprocess"].split(":", 1)
        function = getattr(importlib.import_module(module_name), function_name)
        function(output_root, study_id=config["study_id"])
    return results


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True, type=Path)
    args = parser.parse_args()
    config = json.loads(args.config.read_text(encoding="utf-8"))
    print(json.dumps(execute(config), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
