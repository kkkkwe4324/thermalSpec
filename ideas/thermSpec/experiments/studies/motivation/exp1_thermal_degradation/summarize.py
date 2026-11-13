"""Rebuild a per-run table from preserved summaries."""
import csv
import json
from pathlib import Path


def summarize(root):
    root = Path(root)
    rows = []
    for summary_path in sorted(root.glob("*/summary.json")):
        run_dir = summary_path.parent
        config = json.loads((run_dir / "config.resolved.json").read_text(encoding="utf-8"))
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        rows.append({"run_id": run_dir.name, "profile": config.get("profile_name", "manual"),
                     "mode": summary["mode"], "requests": summary["requests"],
                     "valid_tokens": summary["valid_tokens"],
                     "amortized_ms_per_token": summary["amortized_ms_per_token"],
                     "max_cpu_temp_c": summary["max_cpu_temp_c"],
                     "stop_reason": summary["stop_reason"]})
    if not rows:
        raise ValueError(f"No completed runs in {root}")
    output = root / "summary.csv"
    with output.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
    return output
