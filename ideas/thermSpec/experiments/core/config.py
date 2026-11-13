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
    if project.get("config_version") != 1:
        raise ValueError("Unsupported project config version")
    return project, hashlib.sha256(raw).hexdigest()


def load_calibration_prompts(project):
    """Verify the frozen dataset and select the same prompts on every machine."""
    spec = project["dataset"]
    location = os.environ.get(spec["path_env"])
    if not location:
        raise RuntimeError(f"Set {spec['path_env']} to the frozen dataset file")
    raw = Path(location).read_bytes()
    actual = hashlib.sha256(raw).hexdigest()
    if actual.lower() != spec["sha256"].lower():
        raise ValueError(f"Dataset SHA-256 mismatch: {actual}")
    rows = [json.loads(line) for line in raw.decode("utf-8").splitlines() if line]
    selection = spec["calibration_selection"]
    chosen = []
    for family in selection["families"]:
        matches = sorted((row for row in rows if row["split"] == selection["split"] and
                          row["task_family"] == family), key=lambda row: row[selection["order_by"]])
        if len(matches) < selection["per_family"]:
            raise ValueError(f"Too few calibration prompts for {family}")
        chosen.extend(matches[:selection["per_family"]])
    return chosen
