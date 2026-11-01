"""Run `python -m unittest -v test_wttp_token_fixture.py` (stdlib only)."""
from __future__ import annotations

import copy
import json
from pathlib import Path
import tempfile
import unittest

from wttp_token_fixture import TokenizerInventory, WeightedTokenProbe, generate, replay, python_call_shape


def miniature_tokenizer(dst: Path):
    # Fake tokenizer used exclusively to test the harness, NOT claimed to be LiquidAI tokenizer.
    vocab = {chr(i): i + 100 for i in range(32, 127)}
    vocab["[UNK]"] = 0
    added = [
        {"id": 301, "content": "<|tool_call_start|>", "special": True},
        {"id": 302, "content": "<|tool_call_end|>", "special": True},
        {"id": 303, "content": "<tool_call>", "special": False},
        {"id": 304, "content": "</tool_call>", "special": False},
    ]
    dst.write_text(json.dumps({"version": "1.0", "added_tokens": added,
        "normalizer": None, "pre_tokenizer": None, "post_processor": None,
        "decoder": {"type": "Fuse"},
        "model": {"type": "WordLevel", "vocab": vocab, "unk_token": "[UNK]"}}, indent=2), encoding="utf-8")


class SyntheticHarnessTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.path = Path(cls.tmp.name) / "tokenizer.json"
        miniature_tokenizer(cls.path)
        cls.tok = TokenizerInventory(cls.path)
        cls.fixtures = generate(cls.tok, "lfm25", "get_weather", 'city="Paris"')

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_generated_scenarios_from_real_file_ids_not_guessed(self):
        self.assertEqual(len(self.fixtures["scenarios"]), 12)
        self.assertTrue(self.fixtures["synthetic"])
        self.assertFalse(self.fixtures["model_output"])
        self.assertEqual(self.fixtures["profiles"]["lfm2"]["start_ids"], [301])
        self.assertEqual(self.fixtures["profiles"]["lfm3"]["start_ids"], [303])
        self.assertGreater(len(self.fixtures["profiles"]["lfm2"]["composite_start"]), 1)
        self.assertTrue(all(self.tok.decode(x["token_ids"]) for x in self.fixtures["scenarios"]))

    def test_replay_all_variants_and_mixed(self):
        result = replay(self.fixtures, allow_composite=False)
        self.assertEqual(len(result["runs"]), 12)
        for run in result["runs"]:
            calls = [ev for ev in run["events"] if ev["event"] == "TOOL_CANDIDATE"]
            self.assertEqual(len(calls), 1, run["scenario"])
            self.assertEqual(calls[0]["tools"], ["get_weather"])
            self.assertTrue(calls[0]["syntax_valid"])
            expected_allowed = run["scenario"].endswith("dedicated_dedicated")
            self.assertEqual(calls[0]["publication_eligible"], expected_allowed)
            self.assertTrue(calls[0]["retainer_required"])

    def test_composite_eligibility_is_opt_in_without_execution(self):
        result = replay(self.fixtures, allow_composite=True)
        self.assertTrue(all(next(e for e in x["events"] if e["event"] == "TOOL_CANDIDATE")
                            ["publication_eligible"] for x in result["runs"]))
        self.assertTrue(result["synthetic"])

    def test_family_hint_does_not_exclude_other_protocol(self):
        fixtures = copy.deepcopy(self.fixtures)
        for c in fixtures["scenarios"]:
            c["family_hint"] = "lfm2"
        out = replay(fixtures, allow_composite=True)
        lfm3 = [x for x in out["runs"] if x["scenario"].startswith("lfm3_")]
        self.assertEqual(len(lfm3), 4)
        self.assertTrue(all(any(e["event"] == "TOOL_CANDIDATE" and e["protocol"] == "lfm3"
                                for e in x["events"]) for x in lfm3))

    def feed_text(self, start_ids, text, end_ids, allow=False):
        # All body characters are tokens from the *test tokenizer's* base vocab.
        sequence = list(start_ids) + [self.tok.data["model"]["vocab"][ch] for ch in text] + list(end_ids)
        p = WeightedTokenProbe(self.fixtures["profiles"], "lfm25", {"get_weather"}, allow_composite=allow)
        ids = []
        for tid in sequence:
            before = self.tok.decode(ids) if ids else ""
            ids.append(tid)
            after = self.tok.decode(ids)
            self.assertTrue(after.startswith(before))
            p.feed(tid, after[len(before):])
        return p.finish()

    def test_incomplete_call_is_not_tool(self):
        events = self.feed_text([301], '[get_weather(city="Paris")', [])
        self.assertTrue(any(e["event"] == "INCOMPLETE" for e in events))
        self.assertFalse(any(e["event"] == "TOOL_CANDIDATE" for e in events))

    def test_closing_marker_inside_python_string(self):
        events = self.feed_text([301], '[get_weather(city="<|tool_call_end|>")]', [302])
        calls = [e for e in events if e["event"] == "TOOL_CANDIDATE"]
        self.assertEqual(len(calls), 1)
        self.assertIn('city="<|tool_call_end|>"', calls[0]["raw_body"])
        self.assertTrue(calls[0]["syntax_valid"])

    def test_malformed_does_not_become_published_call(self):
        events = self.feed_text([301], '[get_weather(city=)]', [302])
        call = next(e for e in events if e["event"] == "TOOL_CANDIDATE")
        self.assertFalse(call["syntax_valid"])
        self.assertFalse(call["publication_eligible"])

    def test_injection_expressions_rejected(self):
        for body in ['[get_weather(city=__import__("os").system("echo hi"))]',
                     '[get_weather(city="Paris", **{"hack":True})]',
                     '[get_weather(city="Paris", city="Berlin")]',
                     '[get_weather(city="Paris")]; print(5)']:
            with self.subTest(body=body):
                self.assertIsNone(python_call_shape(body, {"get_weather"}))

    def test_literal_python_alias_accepted_without_execution(self):
        body = '[get_weather(city="Paris", use_cache=True, limit=10000000000000001)]'
        self.assertEqual(python_call_shape(body, {"get_weather"}), ["get_weather"])

    def test_tokenizer_sha_change_prevents_replay(self):
        fixture = copy.deepcopy(self.fixtures)
        fixture["tokenizer_sha256"] = "0000"
        with self.assertRaises(ValueError):
            replay(fixture, allow_composite=False)

    def test_empty_registry_disallows_tool(self):
        events = self.feed_text([301], '[delete_file(path="notes.md")]', [302])
        call = next(e for e in events if e["event"] == "TOOL_CANDIDATE")
        self.assertEqual(call["tools"], [])
        self.assertFalse(call["publication_eligible"])

    def test_composite_quoted_example_is_shadow_by_default(self):
        # Quoted example can look exactly like a call; no intention inference from bytes.
        start = self.fixtures["profiles"]["lfm2"]["composite_start"]
        end = self.fixtures["profiles"]["lfm2"]["composite_end"]
        events = self.feed_text(start, '[get_weather(city="Paris")]', end)
        call = next(e for e in events if e["event"] == "TOOL_CANDIDATE")
        self.assertEqual(call["start_recognition"], "COMPOSITE_TEXT")
        self.assertFalse(call["publication_eligible"])


if __name__ == "__main__":
    unittest.main()
