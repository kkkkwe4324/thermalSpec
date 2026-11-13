"""Regenerate a simple per-run comparison figure from summary.csv."""
import csv
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


def plot_comparison(summary_csv):
    summary_csv = Path(summary_csv)
    with summary_csv.open(encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    fig, ax = plt.subplots(figsize=(max(7, len(rows) * 1.2), 4), constrained_layout=True)
    ax.scatter(range(len(rows)), [float(r["amortized_ms_per_token"]) for r in rows])
    ax.set_xticks(range(len(rows)), [r["run_id"] for r in rows], rotation=35, ha="right")
    ax.set_ylabel("Request ms/token")
    ax.set_title("Phone draft integration runs (no Orin verification)")
    output = summary_csv.parent / f"{summary_csv.stem}-comparison.png"
    fig.savefig(output, dpi=160)
    plt.close(fig)
    return output


def postprocess(root, study_id):
    from .summarize import summarize
    return plot_comparison(summarize(root, study_id))
