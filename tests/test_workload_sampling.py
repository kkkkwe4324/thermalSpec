"""Frozen real-prompt selection and exact speculative sampling checks."""
import hashlib
import json
import math
import random
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from framework.core.config import load_calibration_prompts, load_project
from framework.core.sampling import (accept_probability,
    normalize_top_p, residual_distribution, verify_round)


class WorkloadSamplingTests(unittest.TestCase):
    def test_selects_frozen_wildchat_calibration_without_task_categories(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "prompts.jsonl"
            rows = [
                {"prompt_id": "c2", "split": "calibration", "selection_rank": 2, "prompt": "second"},
                {"prompt_id": "t1", "split": "test", "selection_rank": 1, "prompt": "test"},
                {"prompt_id": "c1", "split": "calibration", "selection_rank": 1, "prompt": "first"},
            ]
            raw = ("\n".join(json.dumps(row) for row in rows) + "\n").encode()
            path.write_bytes(raw)
            project, _ = load_project()
            project["dataset"]["sha256"] = hashlib.sha256(raw).hexdigest()
            project["dataset"]["split_counts"] = {"calibration": 2, "test": 1}
            with patch.dict("os.environ", {project["dataset"]["path_env"]: str(path)}):
                self.assertEqual([row["prompt_id"] for row in load_calibration_prompts(project)], ["c1", "c2"])
                project["dataset"]["sha256"] = "0" * 64
                with self.assertRaisesRegex(ValueError, "SHA-256 mismatch"):
                    load_calibration_prompts(project)

    def test_exact_residual_preserves_target_distribution(self):
        target = [0.6, 0.3, 0.1]
        draft = [0.2, 0.5, 0.3]
        residual = residual_distribution(target, draft)
        self.assertEqual(residual, [1.0, 0.0, 0.0])
        accepted = [min(p, q) for p, q in zip(target, draft)]
        rejected_mass = 1 - sum(accepted)
        reconstructed = [a + rejected_mass * r for a, r in zip(accepted, residual)]
        for observed, expected in zip(reconstructed, target):
            self.assertAlmostEqual(observed, expected)
        self.assertAlmostEqual(accept_probability(0.3, 0.5), 0.6)

    def test_draft_distribution_can_have_smaller_padded_vocabulary(self):
        self.assertEqual(residual_distribution([0.2, 0.3, 0.5], [0.5, 0.5]),
                         [0.0, 0.0, 1.0])

    def test_sampling_transform_masks_padded_logits_and_normalizes_top_p(self):
        logits = [math.log(x) for x in (0.6, 0.3, 0.1)] + [100.0]
        result = normalize_top_p(logits, vocab_tokens=3, temperature=1.0, top_p=0.8)
        self.assertEqual(len(result), 3)
        self.assertAlmostEqual(result[0], 2 / 3)
        self.assertAlmostEqual(result[1], 1 / 3)
        self.assertEqual(result[2], 0.0)

    def test_invalid_sampling_distributions_fail(self):
        with self.assertRaises(ValueError):
            residual_distribution([0.5, 0.5], [0.4, 0.4])
        with self.assertRaises(ValueError):
            accept_probability(0.1, 0)

    def test_verification_corrects_first_rejected_token(self):
        class FixedRandom:
            def __init__(self, values):
                self.values = iter(values)

            def random(self):
                return next(self.values)

        # First proposal is accepted. Second has p/q=0.2 and is rejected.
        result = verify_round([0, 0], [[0.5, 0.5], [0.5, 0.5]],
                              [[0.5, 0.5], [0.1, 0.9], [0.7, 0.3]],
                              FixedRandom([0.4, 0.9, 0.1]))
        self.assertEqual(result, {"tokens": [0, 1], "accepted_draft_tokens": 1,
                                  "rejected_at": 1})

    def test_verification_adds_target_bonus_when_all_accepted(self):
        class FixedRandom:
            def random(self):
                return 0.7

        result = verify_round([0], [[0.5, 0.5]], [[0.5, 0.5], [0.2, 0.8]], FixedRandom())
        self.assertEqual(result["tokens"], [0, 1])
        self.assertEqual(result["accepted_draft_tokens"], 1)

    def test_sampled_output_matches_target_frequency(self):
        rng = random.Random(20261113)
        target = [0.7, 0.3]
        draft = [0.2, 0.8]
        first_token_zero = 0
        trials = 20000
        for _ in range(trials):
            proposal = 0 if rng.random() < draft[0] else 1
            result = verify_round([proposal], [draft], [target, target], rng)
            first_token_zero += result["tokens"][0] == 0
        self.assertLess(abs(first_token_zero / trials - target[0]), 0.015)

    def test_rounding_gap_never_draws_zero_probability_bonus(self):
        class FixedRandom:
            def __init__(self):
                self.values = iter([0.5, 0.9999997])

            def random(self):
                return next(self.values)

        result = verify_round([0], [[1.0, 0.0]],
                              [[1.0, 0.0], [0.9999995, 0.0]], FixedRandom())
        self.assertEqual(result["tokens"], [0, 0])


if __name__ == "__main__":
    unittest.main()
