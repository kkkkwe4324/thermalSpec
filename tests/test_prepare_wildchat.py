import unittest

from ideas.thermSpec.experiments.prepare_wildchat import count_prompt_tokens, extract_prompt, locate_row


class PrepareWildchatTests(unittest.TestCase):
    def test_first_user_turn_only(self):
        row = {"toxic": False, "redacted": False, "conversation": [
            {"role": "user", "content": "Please explain why my phone gets hot."},
            {"role": "assistant", "content": "Because..."},
            {"role": "user", "content": "Tell me more"},
        ]}
        self.assertEqual(extract_prompt(row), "Please explain why my phone gets hot.")

    def test_excludes_redacted_and_nontext(self):
        row = {"toxic": False, "redacted": True, "conversation": [
            {"role": "user", "content": "Please explain why my phone gets hot."}]}
        self.assertIsNone(extract_prompt(row))
        row["redacted"] = False
        row["conversation"][0]["content"] = "x\ufffdx"
        self.assertIsNone(extract_prompt(row))

    def test_counts_token_ids_in_chat_template(self):
        class Tokenizer:
            def apply_chat_template(self, *args, **kwargs):
                return {"input_ids": [1, 2, 3], "attention_mask": [1, 1, 1]}

        self.assertEqual(count_prompt_tokens(Tokenizer(), "hello"), 3)

    def test_locates_row_in_pinned_parquet_shard_and_group(self):
        self.assertEqual(locate_row(1002, [0, 1000, 2000],
                                    [[0, 500, 1000], [0, 700, 1000]]), (1, 0, 2))


if __name__ == "__main__":
    unittest.main()
