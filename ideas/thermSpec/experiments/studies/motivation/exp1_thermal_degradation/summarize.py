"""Rebuild a per-run table from preserved summaries."""
import csv
import json
from pathlib import Path


def summarize(root, study_id):
    root = Path(root)
    rows = []
    for run_dir in sorted(root.glob(f"{study_id}-*/")):
        summary_path = run_dir / "summary.json"
        if not summary_path.exists():
            continue
        config = json.loads((run_dir / "config.resolved.json").read_text(encoding="utf-8"))
        event_path = run_dir / "events.jsonl"
        if event_path.exists():
            events = [json.loads(line) for line in event_path.read_text(encoding="utf-8").splitlines()]
            requests = [event["data"] for event in events if event["kind"] == "draft_request"]
            telemetry = [event["data"] for event in events if event["kind"] == "phone_telemetry"]
            endings = [event["data"] for event in events if event["kind"] == "run_end"]
            total_ms = sum(row["request_wall_ms"] for row in requests)
            token_count = sum(row["generated_tokens"] for row in requests)
            summary = {"mode": config["mode"], "requests": len(requests), "valid_tokens": token_count,
                       "amortized_ms_per_token": total_ms / token_count if token_count else None,
                       "max_cpu_temp_c": max(row["cpu_temp_c"] for row in telemetry),
                       "stop_reason": endings[-1].get("reason") if endings else "unknown"}
        else:
            summary = json.loads(summary_path.read_text(encoding="utf-8"))
        rows.append({"run_id": run_dir.name, "profile": config.get("profile_name", "manual"),
                     "mode": summary["mode"], "requests": summary["requests"],
                     "valid_tokens": summary["valid_tokens"],
                     "amortized_ms_per_token": summary["amortized_ms_per_token"],
                     "max_cpu_temp_c": summary["max_cpu_temp_c"],
                     "stop_reason": summary["stop_reason"]})
    if not rows:
        raise ValueError(f"No completed runs in {root}")
    output = root / f"{study_id}-summary.csv"
    with output.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
    return output
