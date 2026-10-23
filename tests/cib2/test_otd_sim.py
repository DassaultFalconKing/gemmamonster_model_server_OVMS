# Copyright (C) 2018-2026 Intel Corporation
# SPDX-License-Identifier: Apache-2.0
"""CIB2-03 tests for the strict offline OTD trace replay.

The tests assert concrete expected slot/hit/eviction sequences and concrete rejection
behavior; they do not merely mirror the implementation.
"""

from __future__ import annotations

import io
import json
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "cib2" / "otd_sim"))

import otd_sim  # noqa: E402
from otd_sim import TraceFormatError, parse_trace_text, replay, verify_lru  # noqa: E402

HEADER = "# moe_otd_trace v1"
LAYER = "L,0,layer-a,model-a,3,8,2"


def _event_line(call, t_ns, expert, slot, hit, evicted=-1, nbytes=100):
    if hit:
        return f"E,{call},{t_ns},0,{expert},{slot},1,-1,0,0,0,0,0"
    return f"E,{call},{t_ns},0,{expert},{slot},0,{evicted},{nbytes},1,10,1,1"


VALID_TRACE = "\n".join([
    HEADER,
    LAYER,
    "C,0,100,0,S,2,ok,0 1",
    _event_line(0, 101, 0, 0, False),
    _event_line(0, 102, 1, 1, False),
    "C,1,200,0,S,2,ok,0 1",
    _event_line(1, 201, 0, 0, True),
    _event_line(1, 202, 1, 1, True),
    "C,2,300,0,S,2,ok,2 0",
    _event_line(2, 301, 2, 2, False),
    _event_line(2, 302, 0, 0, True),
    "C,3,400,0,S,1,ok,3",
    _event_line(3, 401, 3, 1, False, evicted=1),
]) + "\n"

EXPECTED_VALID_DECISIONS = [
    {"call": 0, "expert": 0, "hit": False, "slot": 0, "evicted": None},
    {"call": 0, "expert": 1, "hit": False, "slot": 1, "evicted": None},
    {"call": 1, "expert": 0, "hit": True, "slot": 0, "evicted": None},
    {"call": 1, "expert": 1, "hit": True, "slot": 1, "evicted": None},
    {"call": 2, "expert": 2, "hit": False, "slot": 2, "evicted": None},
    {"call": 2, "expert": 0, "hit": True, "slot": 0, "evicted": None},
    {"call": 3, "expert": 3, "hit": False, "slot": 1, "evicted": 1},
]


def _synthetic_trace(capacity, plan):
    """Render a synthetic offline trace. plan: [(routed, status, unique, events)]."""
    lines = [HEADER, f"L,0,layer-a,model-a,{capacity},16,2"]
    for call, (routed, status, unique, events) in enumerate(plan):
        start = 100 * call
        lines.append(f"C,{call},{start},0,S,{routed},{status},{' '.join(map(str, unique))}")
        for i, (expert, slot, hit, evicted) in enumerate(events):
            lines.append(_event_line(call, start + i + 1, expert, slot, hit, evicted))
    return "\n".join(lines) + "\n"


def _decisions(plan):
    out = []
    for call, (_routed, _status, _unique, events) in enumerate(plan):
        for expert, slot, hit, evicted in events:
            out.append({
                "call": call,
                "expert": expert,
                "hit": hit,
                "slot": slot,
                "evicted": None if evicted < 0 else evicted,
            })
    return out


class ExactLruReplayTest(unittest.TestCase):
    def test_valid_trace_has_exact_slot_hit_eviction_sequence(self):
        trace = parse_trace_text(VALID_TRACE)
        result = verify_lru(trace, include_decisions=True)
        self.assertEqual(result["mismatches"], 0, result["first_mismatches"])
        self.assertEqual(result["checked_events"], 7)
        self.assertEqual(result["decisions"], EXPECTED_VALID_DECISIONS)

    def test_replay_at_recorded_capacity_matches_expected_counts(self):
        trace = parse_trace_text(VALID_TRACE)
        result = replay(trace, "lru")
        total = result["total"]
        self.assertEqual(total["accesses"], 7)
        self.assertEqual(total["hits"], 3)
        self.assertEqual(total["misses"], 4)
        self.assertEqual(total["evictions"], 1)
        self.assertEqual(total["overflow_calls"], 0)
        self.assertEqual(total["overflow_partial_loads"], 0)
        self.assertTrue(result["offline_only"])
        self.assertEqual(result["runtime_acceptance"], "NO")

    def test_tampered_decision_is_detected(self):
        text = VALID_TRACE.replace(
            _event_line(3, 401, 3, 1, False, evicted=1),
            _event_line(3, 401, 3, 1, False, evicted=0),
        )
        result = verify_lru(parse_trace_text(text))
        self.assertGreater(result["mismatches"], 0)
        self.assertEqual(result["first_mismatches"][0]["call"], 3)


class StrictParsingTest(unittest.TestCase):
    def assert_rejected(self, text, fragment):
        with self.assertRaises(TraceFormatError) as ctx:
            parse_trace_text(text)
        self.assertIn(fragment, str(ctx.exception))

    def test_missing_header(self):
        self.assert_rejected(LAYER + "\n", "missing")
        self.assert_rejected("\n" + HEADER + "\n" + LAYER + "\n", "expected first record")

    def test_unknown_and_malformed_records(self):
        self.assert_rejected(HEADER + "\n" + LAYER + "\nX,1,2\n", "unknown record")
        self.assert_rejected(HEADER + "\nL,0,layer-a,model-a,3,8\n", "needs 7 fields")
        self.assert_rejected(HEADER + "\nL,x,layer-a,model-a,3,8,2\n", "base-10 integer")
        self.assert_rejected(
            HEADER + "\n" + LAYER + "\nC,0,100,0,S,1,ok,0\nE,0,101,0,0,0\n",
            "needs 13 fields",
        )

    def test_duplicate_layer_and_call_ids(self):
        self.assert_rejected(HEADER + "\n" + LAYER + "\n" + LAYER + "\n", "duplicate layer id")
        self.assert_rejected(HEADER + "\n" + LAYER + "\n" + HEADER + "\n", "duplicate trace header")
        duplicate_call = "\n".join([
            HEADER, LAYER,
            "C,0,100,0,S,1,ok,0",
            _event_line(0, 101, 0, 0, False),
            "C,0,200,0,S,1,ok,1",
            _event_line(0, 201, 1, 1, False),
        ]) + "\n"
        self.assert_rejected(duplicate_call, "duplicate call id")

    def test_out_of_range_ids_and_bounds(self):
        self.assert_rejected(
            HEADER + "\n" + LAYER + "\nC,0,100,1,S,1,ok,0\n",
            "unregistered layer",
        )
        self.assert_rejected(
            HEADER + "\n" + LAYER + "\nC,0,100,0,S,1,ok,99\n",
            "outside 0..7",
        )
        self.assert_rejected(
            HEADER + "\n" + LAYER + "\nC,0,100,0,S,1,ok,0\n" + _event_line(0, 101, 0, 5, False) + "\n",
            "outside 0..2",
        )
        self.assert_rejected(
            HEADER + "\n" + LAYER + "\nC,0,100,0,S,2,ok,0 0\n",
            "repeats an expert",
        )
        self.assert_rejected(
            HEADER + "\n" + LAYER + "\nC,0,100,0,O,2,ok,0 1\n",
            "one expert",
        )

    def test_overflow_accounting_is_strict(self):
        # An overflowing lease must exceed capacity, must not touch the cache, and its
        # fallback is separate.
        overflow_layer = "L,0,layer-a,model-a,2,8,2"
        self.assert_rejected(
            HEADER + "\n" + overflow_layer + "\nC,0,100,0,S,3,ok,0 1 2\n",
            "marked ok",
        )
        self.assert_rejected(
            HEADER + "\n" + overflow_layer + "\nC,0,100,0,S,2,overflow,0 1\n",
            "marked overflow",
        )
        self.assert_rejected(
            HEADER + "\n" + overflow_layer + "\nC,0,100,0,S,3,overflow,0 1 2\n"
            + _event_line(0, 101, 0, 0, False) + "\n",
            "after it was closed",
        )
        self.assert_rejected(
            HEADER + "\n" + LAYER + "\nC,0,100,0,S,1,ok,0\n"
            + _event_line(0, 101, 0, 0, True).replace(",1,-1,0,0,0,0,0", ",1,-1,100,1,10,1,1") + "\n",
            "cache hit must have zero",
        )

    def test_incomplete_and_truncated_calls_are_rejected(self):
        truncated_at_eof = "\n".join([
            HEADER, LAYER,
            "C,0,100,0,S,2,ok,0 1",
            _event_line(0, 101, 0, 0, False),
        ]) + "\n"
        self.assert_rejected(truncated_at_eof, "incomplete")
        truncated_before_next = truncated_at_eof + "C,1,200,0,S,1,ok,2\n"
        self.assert_rejected(truncated_before_next, "incomplete")
        self.assert_rejected(
            HEADER + "\n" + LAYER + "\nC,0,100,0,S,1,ok,0\nE,0,101,0,0\n",
            "needs 13 fields",
        )
        # A file cut in the middle of the expert list is malformed, not silently accepted.
        self.assert_rejected(
            HEADER + "\n" + LAYER + "\nC,0,100,0,S,1,ok,",
            "no experts",
        )


class OversizedLeaseTest(unittest.TestCase):
    # Capacity 2. The overflowing call 1 must be rejected without mutating slots 0/1;
    # calls 2 and 3 must still hit those exact slots.
    TRACE = "\n".join([
        HEADER,
        "L,0,layer-a,model-a,2,8,2",
        "C,0,100,0,S,2,ok,0 1",
        _event_line(0, 101, 0, 0, False),
        _event_line(0, 102, 1, 1, False),
        "C,1,200,0,S,3,overflow,2 3 4",
        "C,2,300,0,S,1,ok,0",
        _event_line(2, 301, 0, 0, True),
        "C,3,400,0,S,1,ok,1",
        _event_line(3, 401, 1, 1, True),
    ]) + "\n"

    def test_refusal_does_not_mutate_lru_state(self):
        trace = parse_trace_text(self.TRACE)
        verified = verify_lru(trace, include_decisions=True)
        self.assertEqual(verified["mismatches"], 0, verified["first_mismatches"])
        self.assertEqual(verified["decisions"], [
            {"call": 0, "expert": 0, "hit": False, "slot": 0, "evicted": None},
            {"call": 0, "expert": 1, "hit": False, "slot": 1, "evicted": None},
            {"call": 2, "expert": 0, "hit": True, "slot": 0, "evicted": None},
            {"call": 3, "expert": 1, "hit": True, "slot": 1, "evicted": None},
        ])
        total = replay(trace, "lru")["total"]
        self.assertEqual(total["hits"], 2)
        self.assertEqual(total["misses"], 2)
        self.assertEqual(total["evictions"], 0)
        self.assertEqual(total["overflow_calls"], 1)
        self.assertEqual(total["overflow_partial_loads"], 0)


class ByteAccountingTest(unittest.TestCase):
    def test_logical_and_physical_bytes_are_separate(self):
        trace = parse_trace_text(VALID_TRACE)
        verified = verify_lru(trace)
        self.assertEqual(verified["logical_bytes"]["requested"], 400)
        self.assertEqual(verified["logical_bytes"]["read_from_storage"], 400)
        self.assertEqual(verified["logical_bytes"]["copied_to_slots"], 400)
        self.assertEqual(verified["physical_bytes"]["nvme_read"], "NOT_EXPOSED")
        self.assertEqual(verified["physical_bytes"]["nvme_write"], "NOT_EXPOSED")
        self.assertIn("device counters", verified["physical_bytes"]["reason"])

        simulated = replay(trace, "lru")
        self.assertEqual(simulated["logical_bytes"]["requested"], 400)
        self.assertEqual(simulated["logical_bytes"]["read_from_storage"], 400)
        self.assertEqual(simulated["physical_bytes"]["nvme_read"], "NOT_EXPOSED")
        self.assertTrue(simulated["offline_only"])

    def test_cli_per_token_bytes_never_fabricate_physical_traffic(self):
        fd, path = tempfile.mkstemp(suffix=".trace")
        os.close(fd)
        try:
            with open(path, "w", encoding="utf-8", newline="\n") as fh:
                fh.write(VALID_TRACE)
            out = io.StringIO()
            with redirect_stdout(out):
                rc = otd_sim.main([
                    "simulate", path, "--policy", "lru", "--committed-tokens", "4",
                ])
        finally:
            os.remove(path)
        self.assertEqual(rc, 0)
        payload = json.loads(out.getvalue())[0]
        self.assertEqual(payload["total"]["logical_bytes_per_committed_token"], 100)
        self.assertEqual(payload["total"]["physical_nvme_bytes_per_committed_token"], "NOT_EXPOSED")
        self.assertEqual(payload["physical_bytes"]["nvme_read"], "NOT_EXPOSED")

    def test_cli_rejects_missing_header_with_exit_2(self):
        fd, path = tempfile.mkstemp(suffix=".trace")
        os.close(fd)
        try:
            with open(path, "w", encoding="utf-8", newline="\n") as fh:
                fh.write(LAYER + "\n")
            err = io.StringIO()
            with redirect_stderr(err):
                rc = otd_sim.main(["verify", path])
        finally:
            os.remove(path)
        self.assertEqual(rc, 2)
        self.assertIn("trace_format_error", err.getvalue())


class SyntheticConcurrencyTest(unittest.TestCase):
    """C1/C2/C4 traces are offline inputs only; never live-workload evidence."""

    C1 = ([
        (2, "ok", [0, 1], [(0, 0, False, -1), (1, 1, False, -1)]),
        (2, "ok", [1, 2], [(1, 1, True, -1), (2, 2, False, -1)]),
        (2, "ok", [0, 3], [(0, 0, True, -1), (3, 3, False, -1)]),
    ], 4, (6, 2, 4, 0))

    C2 = ([
        (4, "ok", [0, 1, 2, 3],
         [(0, 0, False, -1), (1, 1, False, -1), (2, 2, False, -1), (3, 3, False, -1)]),
        (2, "ok", [0, 1], [(0, 0, True, -1), (1, 1, True, -1)]),
        (2, "ok", [4, 5], [(4, 2, False, 2), (5, 3, False, 3)]),
        (2, "ok", [0, 1], [(0, 0, True, -1), (1, 1, True, -1)]),
    ], 4, (10, 4, 6, 2))

    C4 = ([
        (4, "ok", [0, 1, 2, 3],
         [(0, 0, False, -1), (1, 1, False, -1), (2, 2, False, -1), (3, 3, False, -1)]),
        (4, "ok", [4, 5, 6, 7],
         [(4, 0, False, 0), (5, 1, False, 1), (6, 2, False, 2), (7, 3, False, 3)]),
        (2, "ok", [4, 5], [(4, 0, True, -1), (5, 1, True, -1)]),
    ], 4, (10, 2, 8, 4))

    def test_c1_c2_c4_replay_offline_only(self):
        for name, (plan, capacity, expected) in (
            ("C1", self.C1),
            ("C2", self.C2),
            ("C4", self.C4),
        ):
            with self.subTest(concurrency=name):
                text = _synthetic_trace(capacity, plan)
                trace = parse_trace_text(text)
                verified = verify_lru(trace, include_decisions=True)
                self.assertEqual(verified["mismatches"], 0, (name, verified["first_mismatches"]))
                self.assertEqual(verified["decisions"], _decisions(plan), name)
                total = replay(trace, "lru")["total"]
                accesses, hits, misses, evictions = expected
                self.assertEqual(
                    (total["accesses"], total["hits"], total["misses"], total["evictions"]),
                    (accesses, hits, misses, evictions),
                    name,
                )
                self.assertTrue(verified["offline_only"], name)
                self.assertEqual(verified["runtime_acceptance"], "NO", name)
                self.assertEqual(verified["physical_bytes"]["nvme_read"], "NOT_EXPOSED", name)


if __name__ == "__main__":
    unittest.main()
