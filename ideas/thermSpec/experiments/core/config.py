"""Load and freeze the project-wide experimental contract."""
import hashlib
import json
import os
from pathlib import Path


DEFAULT_PROJECT = Path(__file__).resolve().parents[1] / "configs" / "project.json"


def load_project(path=None):
    path = Path(path) if path else DEFAULT_PROJECT
    raw = path.read_bytes()
    project = json.loads(raw)
    if project.get("config_version") != 2:
        raise ValueError("Unsupported project config version")
    return project, hashlib.sha256(raw).hexdigest()


def load_frozen_prompts(project, split):
    """Verify the frozen file and return a stable split in selection order."""
    spec = project["dataset"]
    location = os.environ.get(spec["path_env"])
    if not location:
        raise RuntimeError(f"Set {spec['path_env']} to the frozen dataset file")
    raw = Path(location).read_bytes()
    actual = hashlib.sha256(raw).hexdigest()
    if actual.lower() != spec["sha256"].lower():
        raise ValueError(f"Dataset SHA-256 mismatch: {actual}")
    rows = [json.loads(line) for line in raw.decode("utf-8").splitlines() if line]
    chosen = sorted((row for row in rows if row["split"] == split),
                    key=lambda row: row["selection_rank"])
    if len(chosen) != spec["split_counts"][split]:
        raise ValueError(f"Expected {spec['split_counts'][split]} {split} prompts, found {len(chosen)}")
    if len({row["prompt_id"] for row in chosen}) != len(chosen):
        raise ValueError("Duplicate prompt IDs in frozen split")
    return chosen


def load_calibration_prompts(project):
    return load_frozen_prompts(project, "calibration")
