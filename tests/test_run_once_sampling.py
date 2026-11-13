import unittest

from ideas.thermSpec.experiments.run_once import draft_request_payload


class RunOnceSamplingTests(unittest.TestCase):
    def test_demo_sends_frozen_sampling_parameters(self):
        payload = draft_request_payload({"prompt": "hello", "tokens_per_request": 8},
                                        {"generation": {"temperature": 1.0, "top_p": 0.9,
                                                        "top_k": 0, "min_p": 0.0,
                                                        "repeat_penalty": 1.0}})
        self.assertEqual(payload["temperature"], 1.0)
        self.assertEqual(payload["top_p"], 0.9)
        self.assertEqual(payload["top_k"], 0)
        self.assertEqual(payload["min_p"], 0.0)
        self.assertEqual(payload["repeat_penalty"], 1.0)
        self.assertEqual(payload["n_predict"], 8)


if __name__ == "__main__":
    unittest.main()
