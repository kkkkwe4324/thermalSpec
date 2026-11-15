"""Small durable JSON/JSONL helpers."""
import json
import os
import threading
import time
from datetime import datetime, timezone
from pathlib import Path


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temp, path)


def append_jsonl(path, value):
    with Path(path).open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(value, ensure_ascii=False) + "\n")
        stream.flush()


class EventWriter:
    """One schema for all producers; flush every event while the run is active."""

    def __init__(self, path, run_id, start_ns):
        self.path = Path(path)
        self.run_id = run_id
        self.start_ns = start_ns
        self.lock = threading.Lock()
        self.stream = self.path.open("a", encoding="utf-8", buffering=1)
        self.index = 0

    def emit(self, kind, source, data, sample_ns=None):
        sample_ns = sample_ns or time.monotonic_ns()
        with self.lock:
            row = {"schema_version": 1, "run_id": self.run_id, "index": self.index,
                   "kind": kind, "source": source,
                   "utc": datetime.now(timezone.utc).isoformat(),
                   "host_monotonic_ns": sample_ns,
                   "elapsed_ns": sample_ns - self.start_ns,
                   "data": data}
            self.stream.write(json.dumps(row, ensure_ascii=False) + "\n")
            self.stream.flush()
            os.fsync(self.stream.fileno())
            self.index += 1
        return row

    def close(self):
        with self.lock:
            self.stream.close()
