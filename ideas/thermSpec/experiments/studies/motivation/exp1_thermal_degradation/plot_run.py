"""Regenerate the three-panel integration plot from saved raw data."""
import csv
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


def plot_run(directory):
    directory = Path(directory)
    if (directory / "events.jsonl").exists():
        events = [json.loads(line) for line in (directory / "events.jsonl").read_text(encoding="utf-8").splitlines()]
        telemetry = [{"elapsed_s": event["elapsed_ns"] / 1e9, **event["data"]}
                     for event in events if event["kind"] == "phone_telemetry"]
        rounds = [{"elapsed_s": event["elapsed_ns"] / 1e9,
                   "elapsed_ms": event["data"]["request_wall_ms"],
                   "valid_tokens": event["data"]["generated_tokens"]}
                  for event in events if event["kind"] == "draft_request"]
    else:
        with (directory / "phone_telemetry.csv").open(encoding="utf-8") as stream:
            telemetry = list(csv.DictReader(stream))
        rounds = [json.loads(line) for line in (directory / "rounds.jsonl").read_text(encoding="utf-8").splitlines()]
    t = [float(r["elapsed_s"]) for r in telemetry]
    fig, axes = plt.subplots(3, 1, figsize=(9, 8), sharex=True, constrained_layout=True)
    axes[0].plot(t, [float(r["cpu_temp_c"]) for r in telemetry], label="CPU")
    axes[0].plot(t, [float(r["battery_temp_c"]) for r in telemetry], label="Battery")
    axes[0].set_ylabel("Temperature (C)")
    axes[0].legend()
    for name, label in [("freq_little_khz", "little"), ("freq_mid_khz", "mid"), ("freq_big_khz", "big")]:
        axes[1].plot(t, [int(r[name]) / 1000 for r in telemetry], label=label)
    axes[1].set_ylabel("Frequency (MHz)")
    axes[1].legend()
    axes[2].scatter([r["elapsed_s"] for r in rounds],
                    [r["elapsed_ms"] / r["valid_tokens"] if r["valid_tokens"] else float("nan") for r in rounds], s=14)
    axes[2].set_ylabel("Request ms/token")
    axes[2].set_xlabel("Elapsed time (s)")
    fig.suptitle("Phone draft integration run (no Orin verification)")
    output = directory / "plots" / "exp1_run.png"
    output.parent.mkdir(exist_ok=True)
    fig.savefig(output, dpi=160)
    plt.close(fig)
    return output
