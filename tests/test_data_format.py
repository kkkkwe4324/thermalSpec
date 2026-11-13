"""Checks for the reusable raw-data contract."""
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from ideas.thermSpec.experiments.core.config import load_calibration_prompts, load_project
from ideas.thermSpec.experiments.core.storage import EventWriter
from ideas.thermSpec.experiments.studies.motivation.exp1_thermal_degradation.summarize import summarize


class DataFormatTests(unittest.TestCase):
    def test_events_are_visible_before_writer_closes(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "events.jsonl"
            writer = EventWriter(path, "run-a", 100)
            try:
                writer.emit("phone_telemetry", "phone", {"cpu_temp_c": 35}, sample_ns=200)
                first = json.loads(path.read_text(encoding="utf-8").splitlines()[0])
                self.assertEqual((first["schema_version"], first["run_id"], first["elapsed_ns"]),
                                 (1, "run-a", 100))
                writer.emit("draft_request", "phone", {"generated_tokens": 4}, sample_ns=300)
            finally:
                writer.close()
            events = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
            self.assertEqual([event["index"] for event in events], [0, 1])

    def test_calibration_selection_verifies_hash_and_order(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "prompts.jsonl"
            rows = [{"split": "calibration", "selection_rank": rank,
                     "prompt_id": f"wildchat-{rank}", "prompt": f"Real request {rank}"}
                    for rank in (3, 1, 2)]
            raw = ("\n".join(json.dumps(row) for row in rows) + "\n").encode("utf-8")
            path.write_bytes(raw)
            project, _ = load_project()
            project["dataset"]["sha256"] = hashlib.sha256(raw).hexdigest()
            project["dataset"]["split_counts"] = {"calibration": 3, "test": 0}
            with patch.dict("os.environ", {project["dataset"]["path_env"]: str(path)}):
                chosen = load_calibration_prompts(project)
                self.assertEqual(len(chosen), 3)
                self.assertEqual([row["selection_rank"] for row in chosen], [1, 2, 3])
                project["dataset"]["sha256"] = "0" * 64
                with self.assertRaises(ValueError):
                    load_calibration_prompts(project)

    def test_summary_rebuilds_from_events_instead_of_cached_number(self):
        with tempfile.TemporaryDirectory() as folder:
            run_dir = Path(folder) / "study-a-r01"
            run_dir.mkdir()
            (run_dir / "config.resolved.json").write_text(json.dumps({"mode": "phone_draft"}), encoding="utf-8")
            (run_dir / "summary.json").write_text(json.dumps({"amortized_ms_per_token": 999}), encoding="utf-8")
            events = [
                {"kind": "draft_request", "data": {"request_wall_ms": 100, "generated_tokens": 4}},
                {"kind": "phone_telemetry", "data": {"cpu_temp_c": 35}},
                {"kind": "run_end", "data": {"reason": "request_limit"}},
            ]
            (run_dir / "events.jsonl").write_text("\n".join(json.dumps(row) for row in events) + "\n", encoding="utf-8")
            result = summarize(folder, "study")
            self.assertIn("25.0", result.read_text(encoding="utf-8"))
            self.assertNotIn("999", result.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
