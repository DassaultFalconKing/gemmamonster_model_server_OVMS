# Copyright (C) 2018-2026 Intel Corporation
# SPDX-License-Identifier: Apache-2.0
#
# Adapted for CIB2-03 (offline replay) from the OpenVINO Intel GPU tool
# src/plugins/intel_gpu/tools/moe_otd_sim/otd_sim.py.
# Donor provenance: original import 86bab01ebf2558e9d796be754c1b179677efc1b3;
# current donor file (HEAD 956d5eca956f45b9b76a29daafc3642eb2d9520f, last changed by
# f054eecc7767c9c45627beb4a7883f1642916125) differs from 86bab01e by the
# --precheck -> --legacy-partial-lease rename. The current donor file was used.
#
# CIB2 changes: strict trace-v1 validation (header, field counts, duplicate IDs,
# bounds, closed-call accounting, overflow/incomplete-call rejection), explicit
# offline-only metadata, and separate logical byte accounting from physical NVMe
# bytes (which are NOT_EXPOSED without external device counters).

"""Deterministic offline replay of MOE_OTD_TRACE expert-routing traces.

This module never starts inference, loads a model, builds native code, or changes
runtime state. It reads a trace file, validates it strictly, and replays the exact
LRU slot/hit/eviction decisions recorded by the runtime or by a synthetic offline
generator.

Physical NVMe bytes are deliberately reported as ``NOT_EXPOSED``: trace-v1 has no
device-level counters, so the simulator must not invent them from logical payload
sizes. Synthetic C1/C2/C4 traces are offline inputs, not live workloads, and no
cache policy is promoted by this tool.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from collections import OrderedDict, defaultdict, deque
from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional, Sequence, Set, Tuple

TRACE_HEADER = "# moe_otd_trace v1"
SCHEMA = "cib2.otd_sim.v1"
PHYSICAL_NOT_EXPOSED = "NOT_EXPOSED"
PHYSICAL_REASON = (
    "trace-v1 records no NVMe/OS device counters; physical reads, writeback, "
    "readahead, retries and amplification require external device counters"
)

L_FIELDS = 7
C_FIELDS = 8
E_FIELDS = 13


@dataclass
class Layer:
    layer: int
    layer_key: str
    model_key: str
    capacity: int
    num_expert: int
    top_k: int
    expert_bytes: int = 0


@dataclass
class Event:
    expert: int
    slot: int
    hit: bool
    evicted: Optional[int]
    bytes: int
    reads: int
    read_ns: int
    transform_ns: int
    copy_ns: int
    t_ns: int = 0


@dataclass
class Call:
    call: int
    t_ns: int
    layer: int
    kind: str  # "S" simultaneous lease, "O" single expert
    routed: int
    overflow: bool
    unique: List[int]
    events: List[Event] = field(default_factory=list)
    # "O" calls emitted by the runtime's per-expert fallback after an overflowing "S".
    fallback_of: Optional[int] = None


@dataclass
class Trace:
    layers: Dict[int, Layer]
    calls: List[Call]


class TraceFormatError(ValueError):
    """A trace is missing, malformed, truncated, or violates trace-v1 invariants."""


def _int(value: str, where: str) -> int:
    try:
        return int(value, 10)
    except (TypeError, ValueError) as exc:
        raise TraceFormatError(f"{where}: expected base-10 integer, got {value!r}") from exc


def _expected_events(kind: str, overflow: bool, unique: List[int]) -> int:
    if kind == "S" and overflow:
        return 0
    if kind == "S":
        return len(unique)
    return 1  # "O"


def parse_trace(lines: Iterable[str]) -> Trace:
    """Parse and strictly validate a trace-v1 stream.

    Rejects: missing/duplicate header, unknown records, wrong field counts,
    malformed integers, duplicate layer/call IDs, out-of-range layer/expert/slot
    IDs, duplicate experts in a lease, unknown status/kind, overflow calls that
    touch the cache, and incomplete/truncated calls. There is no lenient mode.
    """
    layers: Dict[int, Layer] = {}
    calls: List[Call] = []
    by_id: Dict[int, Call] = {}
    saw_header = False
    current: Optional[Call] = None
    last_event_ns = 0

    for lineno, raw in enumerate(lines, 1):
        line = raw.rstrip("\r\n")
        if lineno == 1:
            line = line.lstrip("\ufeff")
            if line != TRACE_HEADER:
                raise TraceFormatError(
                    f"line 1: missing {TRACE_HEADER!r} header "
                    f"(expected first record to be the header, got {line!r})"
                )
            saw_header = True
            continue
        if not line:
            continue
        if line.startswith("#"):
            if line == TRACE_HEADER:
                raise TraceFormatError(f"line {lineno}: duplicate trace header")
            # Other comments are ignored after the header.
            continue
        if not saw_header:
            raise TraceFormatError(f"line {lineno}: missing {TRACE_HEADER!r} header")
        fields = line.split(",")
        tag = fields[0]
        if tag == "L":
            if len(fields) != L_FIELDS:
                raise TraceFormatError(f"line {lineno}: L record needs {L_FIELDS} fields, got {len(fields)}")
            lid = _int(fields[1], f"line {lineno}: layer id")
            layer_key, model_key = fields[2], fields[3]
            capacity = _int(fields[4], f"line {lineno}: capacity")
            num_expert = _int(fields[5], f"line {lineno}: num_expert")
            top_k = _int(fields[6], f"line {lineno}: top_k")
            if lid < 0:
                raise TraceFormatError(f"line {lineno}: negative layer id {lid}")
            if lid in layers:
                raise TraceFormatError(f"line {lineno}: duplicate layer id {lid}")
            if not layer_key or not model_key:
                raise TraceFormatError(f"line {lineno}: empty layer_key or model_key")
            if capacity <= 0:
                raise TraceFormatError(f"line {lineno}: capacity must be positive")
            if num_expert <= 0:
                raise TraceFormatError(f"line {lineno}: num_expert must be positive")
            if top_k <= 0 or top_k > num_expert:
                raise TraceFormatError(f"line {lineno}: top_k {top_k} outside 1..{num_expert}")
            layers[lid] = Layer(lid, layer_key, model_key, capacity, num_expert, top_k)
        elif tag == "C":
            if current is not None:
                raise TraceFormatError(
                    f"line {lineno}: call {current.call} is incomplete "
                    f"({len(current.events)}/{_expected_events(current.kind, current.overflow, current.unique)} events)"
                )
            if len(fields) != C_FIELDS:
                raise TraceFormatError(f"line {lineno}: C record needs {C_FIELDS} fields, got {len(fields)}")
            cid = _int(fields[1], f"line {lineno}: call id")
            t_ns = _int(fields[2], f"line {lineno}: call t_ns")
            lid = _int(fields[3], f"line {lineno}: call layer")
            kind, status = fields[4], fields[6]
            routed = _int(fields[5], f"line {lineno}: routed")
            if cid < 0:
                raise TraceFormatError(f"line {lineno}: negative call id {cid}")
            if cid in by_id:
                raise TraceFormatError(f"line {lineno}: duplicate call id {cid}")
            if lid not in layers:
                raise TraceFormatError(f"line {lineno}: call {cid} references unregistered layer {lid}")
            layer = layers[lid]
            if kind not in ("S", "O"):
                raise TraceFormatError(f"line {lineno}: unknown call kind {kind!r}")
            if status not in ("ok", "overflow"):
                raise TraceFormatError(f"line {lineno}: unknown call status {status!r}")
            if t_ns < 0:
                raise TraceFormatError(f"line {lineno}: negative call timestamp {t_ns}")
            if routed < 0:
                raise TraceFormatError(f"line {lineno}: negative routed count {routed}")
            try:
                unique = [int(x, 10) for x in fields[7].split()] if fields[7].strip() else []
            except ValueError as exc:
                raise TraceFormatError(f"line {lineno}: malformed expert list {fields[7]!r}") from exc
            if not unique:
                raise TraceFormatError(f"line {lineno}: call {cid} has no experts")
            if len(set(unique)) != len(unique):
                raise TraceFormatError(f"line {lineno}: call {cid} repeats an expert")
            for expert in unique:
                if expert < 0 or expert >= layer.num_expert:
                    raise TraceFormatError(
                        f"line {lineno}: expert {expert} outside 0..{layer.num_expert - 1} on layer {lid}"
                    )
            if routed < len(unique):
                raise TraceFormatError(
                    f"line {lineno}: routed {routed} is smaller than unique expert count {len(unique)}"
                )
            overflow = status == "overflow"
            if kind == "S":
                if overflow and len(unique) <= layer.capacity:
                    raise TraceFormatError(
                        f"line {lineno}: call {cid} marked overflow but {len(unique)} experts fit capacity {layer.capacity}"
                    )
                if not overflow and len(unique) > layer.capacity:
                    raise TraceFormatError(
                        f"line {lineno}: call {cid} marked ok but {len(unique)} experts exceed capacity {layer.capacity}"
                    )
            else:
                if overflow:
                    raise TraceFormatError(f"line {lineno}: O call {cid} cannot be an overflowing lease")
                if len(unique) != 1 or routed != 1:
                    raise TraceFormatError(f"line {lineno}: O call {cid} must have routed=1 and one expert")
            call = Call(cid, t_ns, lid, kind, routed, overflow, unique)
            calls.append(call)
            by_id[cid] = call
            current = call if _expected_events(kind, overflow, unique) else None
        elif tag == "E":
            if len(fields) != E_FIELDS:
                raise TraceFormatError(f"line {lineno}: E record needs {E_FIELDS} fields, got {len(fields)}")
            cid = _int(fields[1], f"line {lineno}: event call id")
            if current is None or cid != current.call:
                if cid in by_id:
                    raise TraceFormatError(f"line {lineno}: event for call {cid} after it was closed")
                raise TraceFormatError(f"line {lineno}: event for unknown or non-current call {cid}")
            call = current
            layer = layers[call.layer]
            t_ns = _int(fields[2], f"line {lineno}: event t_ns")
            lid = _int(fields[3], f"line {lineno}: event layer")
            expert = _int(fields[4], f"line {lineno}: expert")
            slot = _int(fields[5], f"line {lineno}: slot")
            hit_s = _int(fields[6], f"line {lineno}: hit")
            evicted_i = _int(fields[7], f"line {lineno}: evicted")
            nbytes = _int(fields[8], f"line {lineno}: bytes")
            reads = _int(fields[9], f"line {lineno}: reads")
            read_ns = _int(fields[10], f"line {lineno}: read_ns")
            transform_ns = _int(fields[11], f"line {lineno}: transform_ns")
            copy_ns = _int(fields[12], f"line {lineno}: copy_ns")
            if lid != call.layer:
                raise TraceFormatError(f"line {lineno}: event layer {lid} differs from call layer {call.layer}")
            if t_ns < call.t_ns or t_ns < last_event_ns:
                raise TraceFormatError(f"line {lineno}: non-monotonic event timestamp {t_ns}")
            if expert < 0 or expert >= layer.num_expert:
                raise TraceFormatError(
                    f"line {lineno}: expert {expert} outside 0..{layer.num_expert - 1}"
                )
            if slot < 0 or slot >= layer.capacity:
                raise TraceFormatError(f"line {lineno}: slot {slot} outside 0..{layer.capacity - 1}")
            if hit_s not in (0, 1):
                raise TraceFormatError(f"line {lineno}: hit must be 0 or 1")
            hit = hit_s == 1
            if evicted_i == -1:
                evicted = None
            elif evicted_i < 0 or evicted_i >= layer.num_expert:
                raise TraceFormatError(
                    f"line {lineno}: evicted {evicted_i} outside -1 or 0..{layer.num_expert - 1}"
                )
            else:
                evicted = evicted_i
            if any(v < 0 for v in (nbytes, reads, read_ns, transform_ns, copy_ns)):
                raise TraceFormatError(f"line {lineno}: negative byte or timing counter")
            if hit:
                if evicted is not None:
                    raise TraceFormatError(f"line {lineno}: a cache hit cannot evict expert {evicted}")
                if nbytes or reads or read_ns or transform_ns or copy_ns:
                    raise TraceFormatError(f"line {lineno}: a cache hit must have zero bytes/reads/timings")
            elif evicted == expert:
                raise TraceFormatError(f"line {lineno}: expert {expert} cannot evict itself")
            expected_expert = call.unique[len(call.events)]
            if expert != expected_expert:
                raise TraceFormatError(
                    f"line {lineno}: event expert {expert} differs from lease order (expected {expected_expert})"
                )
            call.events.append(Event(expert, slot, hit, evicted, nbytes, reads, read_ns,
                                     transform_ns, copy_ns, t_ns))
            last_event_ns = t_ns
            if len(call.events) == _expected_events(call.kind, call.overflow, call.unique):
                current = None
        else:
            raise TraceFormatError(f"line {lineno}: unknown record type {tag!r}")

    if not saw_header:
        raise TraceFormatError(f"missing {TRACE_HEADER!r} header")
    if current is not None:
        raise TraceFormatError(
            f"call {current.call} is incomplete: "
            f"{len(current.events)}/{_expected_events(current.kind, current.overflow, current.unique)} events"
        )
    for call in calls:
        layer = layers[call.layer]
        for ev in call.events:
            if not ev.hit and ev.bytes > 0:
                layer.expert_bytes = max(layer.expert_bytes, ev.bytes)
    _link_fallbacks(calls)
    return Trace(layers, calls)


def parse_trace_text(text: str) -> Trace:
    """Parse a trace from a string (test/CLI convenience)."""
    return parse_trace(text.splitlines())


def _link_fallbacks(calls: List[Call]) -> None:
    """Mark per-expert "O" calls that service an overflowing "S" call on the same layer."""
    pending: Dict[int, Tuple[Call, Set[int]]] = {}
    for call in calls:
        if call.kind == "S":
            pending.pop(call.layer, None)
            if call.overflow:
                pending[call.layer] = (call, set(call.unique))
            continue
        entry = pending.get(call.layer)
        if entry is None:
            continue
        owner, remaining = entry
        if len(call.unique) == 1 and call.unique[0] in remaining:
            call.fallback_of = owner.call
            remaining.discard(call.unique[0])
            if not remaining:
                del pending[call.layer]
        else:
            del pending[call.layer]


# --------------------------------------------------------------------------------------------
# Policies. access() must never evict an expert in `pinned` (already leased by the current call).
# --------------------------------------------------------------------------------------------


class Policy:
    name = "base"

    def __init__(self, capacity: int):
        if capacity <= 0:
            raise ValueError("capacity must be positive")
        self.capacity = capacity

    def access(self, expert: int, pinned: Set[int]) -> Tuple[bool, int, Optional[int]]:
        raise NotImplementedError

    def resident(self) -> Set[int]:
        raise NotImplementedError


class ExactLRU(Policy):
    """Bit-exact model of ov::intel_gpu::ocl::moe::LRUCache including slot numbering."""

    name = "lru"

    def __init__(self, capacity: int):
        super().__init__(capacity)
        self._order: "OrderedDict[int, int]" = OrderedDict()  # expert -> slot, oldest first

    def access(self, expert, pinned):
        slot = self._order.get(expert)
        if slot is not None:
            self._order.move_to_end(expert)
            return True, slot, None
        evicted = None
        if len(self._order) >= self.capacity:
            evicted, slot = self._order.popitem(last=False)
        else:
            slot = len(self._order)
        self._order[expert] = slot
        return False, slot, evicted

    def resident(self):
        return set(self._order)


class _SlotPool:
    def __init__(self, capacity: int):
        self._free = list(range(capacity - 1, -1, -1))
        self.slot_of: Dict[int, int] = {}

    def take(self, expert: int, from_expert: Optional[int] = None) -> int:
        slot = self.slot_of.pop(from_expert) if from_expert is not None else self._free.pop()
        self.slot_of[expert] = slot
        return slot


class Clock(Policy):
    name = "clock"

    def __init__(self, capacity: int):
        super().__init__(capacity)
        self._ring: List[int] = []
        self._ref: Dict[int, bool] = {}
        self._hand = 0
        self._slots = _SlotPool(capacity)

    def access(self, expert, pinned):
        if expert in self._ref:
            self._ref[expert] = True
            return True, self._slots.slot_of[expert], None
        if len(self._ring) < self.capacity:
            self._ring.append(expert)
            self._ref[expert] = False
            return False, self._slots.take(expert), None
        for _ in range(2 * len(self._ring) + 1):
            victim = self._ring[self._hand]
            if victim in pinned:
                self._hand = (self._hand + 1) % len(self._ring)
                continue
            if self._ref[victim]:
                self._ref[victim] = False
                self._hand = (self._hand + 1) % len(self._ring)
                continue
            del self._ref[victim]
            self._ring[self._hand] = expert
            self._ref[expert] = False
            self._hand = (self._hand + 1) % len(self._ring)
            return False, self._slots.take(expert, victim), victim
        raise RuntimeError("clock: every resident expert is pinned")

    def resident(self):
        return set(self._ref)


class TwoQ(Policy):
    """Simplified 2Q: probationary FIFO (A1in), protected LRU (Am) and a ghost list (A1out)."""

    name = "2q"

    def __init__(self, capacity: int, in_fraction: float = 0.25, ghost_fraction: float = 0.5):
        super().__init__(capacity)
        self._kin = max(1, int(capacity * in_fraction))
        self._kout = max(1, int(capacity * ghost_fraction))
        self._a1in: "OrderedDict[int, None]" = OrderedDict()
        self._am: "OrderedDict[int, None]" = OrderedDict()
        self._a1out: "OrderedDict[int, None]" = OrderedDict()
        self._slots = _SlotPool(capacity)

    def _victim(self, pinned):
        prefer_in = len(self._a1in) > self._kin or not self._am
        queues = (self._a1in, self._am) if prefer_in else (self._am, self._a1in)
        for queue in queues:
            for expert in queue:
                if expert not in pinned:
                    return queue, expert
        raise RuntimeError("2q: every resident expert is pinned")

    def access(self, expert, pinned):
        if expert in self._am:
            self._am.move_to_end(expert)
            return True, self._slots.slot_of[expert], None
        if expert in self._a1in:
            return True, self._slots.slot_of[expert], None
        evicted = None
        if len(self._a1in) + len(self._am) >= self.capacity:
            queue, evicted = self._victim(pinned)
            del queue[evicted]
            if queue is self._a1in:
                self._a1out[evicted] = None
                while len(self._a1out) > self._kout:
                    self._a1out.popitem(last=False)
            slot = self._slots.take(expert, evicted)
        else:
            slot = self._slots.take(expert)
        if expert in self._a1out:
            del self._a1out[expert]
            self._am[expert] = None
        else:
            self._a1in[expert] = None
        return False, slot, evicted

    def resident(self):
        return set(self._a1in) | set(self._am)


class Belady(Policy):
    """Offline optimum (evict the resident expert reused furthest in the future). Upper bound only."""

    name = "opt"

    def __init__(self, capacity: int, future: Sequence[int]):
        super().__init__(capacity)
        self._future = future
        self._pos = 0
        self._next_use: Dict[int, deque] = defaultdict(deque)
        for i, expert in enumerate(future):
            self._next_use[expert].append(i)
        self._resident: Set[int] = set()
        self._slots = _SlotPool(capacity)

    def access(self, expert, pinned):
        if self._pos >= len(self._future) or self._future[self._pos] != expert:
            raise RuntimeError("opt: access sequence diverged from the precomputed future")
        uses = self._next_use[expert]
        uses.popleft()
        self._pos += 1
        if expert in self._resident:
            return True, self._slots.slot_of[expert], None
        evicted = None
        if len(self._resident) >= self.capacity:
            candidates = [e for e in self._resident if e not in pinned]
            if not candidates:
                raise RuntimeError("opt: every resident expert is pinned")
            evicted = max(candidates, key=lambda e: self._next_use[e][0] if self._next_use[e] else math.inf)
            self._resident.discard(evicted)
            slot = self._slots.take(expert, evicted)
        else:
            slot = self._slots.take(expert)
        self._resident.add(expert)
        return False, slot, evicted

    def resident(self):
        return set(self._resident)


POLICIES = ("lru", "clock", "2q", "opt")


# --------------------------------------------------------------------------------------------
# Replay
# --------------------------------------------------------------------------------------------


def phase_of(call: Call, layer: Layer) -> str:
    if call.kind == "O":
        return "fallback" if call.fallback_of is not None else "per_expert"
    tokens = call.routed / layer.top_k if layer.top_k else call.routed
    if tokens <= 1:
        return "decode_1tok"
    if tokens <= 8:
        return "multi_2to8tok"
    return "prefill_gt8tok"


@dataclass
class Counters:
    accesses: int = 0
    hits: int = 0
    misses: int = 0
    evictions: int = 0
    lease_calls: int = 0
    overflow_calls: int = 0
    overflow_partial_loads: int = 0
    logical_requested_bytes: int = 0
    logical_read_bytes: int = 0
    logical_copied_bytes: int = 0
    bytes_unknown_misses: int = 0

    def add_access(self, hit: bool, evicted: Optional[int], expert_bytes: int) -> None:
        self.accesses += 1
        if hit:
            self.hits += 1
        else:
            self.misses += 1
            if expert_bytes > 0:
                self.logical_requested_bytes += expert_bytes
                self.logical_read_bytes += expert_bytes
                self.logical_copied_bytes += expert_bytes
            else:
                self.bytes_unknown_misses += 1
        if evicted is not None:
            self.evictions += 1

    def as_dict(self) -> dict:
        d = dict(self.__dict__)
        d["hit_rate"] = self.hits / self.accesses if self.accesses else None
        return d


def _logical_bytes(counters: Counters, source: str) -> dict:
    if counters.bytes_unknown_misses:
        requested = read = copied = PHYSICAL_NOT_EXPOSED
    else:
        requested = counters.logical_requested_bytes
        read = counters.logical_read_bytes
        copied = counters.logical_copied_bytes
    return {
        "requested": requested,
        "read_from_storage": read,
        "copied_to_slots": copied,
        "unknown_misses": counters.bytes_unknown_misses,
        "source": source,
        "note": "logical expert payload accounting only; not a physical device measurement",
    }


def _physical_bytes() -> dict:
    return {
        "nvme_read": PHYSICAL_NOT_EXPOSED,
        "nvme_write": PHYSICAL_NOT_EXPOSED,
        "reason": PHYSICAL_REASON,
    }


def _logical_steps(trace: Trace, capacities: Dict[int, int], legacy_partial_lease: bool):
    """Yield (call, experts_to_access, overflowed) in replay order for the given capacities.

    An overflowing simultaneous lease is rejected before the cache is touched. Recorded
    fallback calls are skipped when the simulated lease succeeds; when a simulated lease
    overflows without a recorded fallback, per-expert fallback calls are synthesized in
    sorted expert order.

    ``legacy_partial_lease`` models the pre-fix runtime and is an offline what-if only; it is
    never a recommendation and never changes a real cache.
    """
    fallbacks: Dict[int, List[Call]] = defaultdict(list)
    for call in trace.calls:
        if call.fallback_of is not None:
            fallbacks[call.fallback_of].append(call)
    for call in trace.calls:
        if call.fallback_of is not None:
            continue
        cap = capacities[call.layer]
        if call.kind == "O":
            yield call, call.unique, False
            continue
        overflow = len(call.unique) > cap
        if not overflow:
            yield call, call.unique, False
            continue
        yield call, (call.unique[:cap] if legacy_partial_lease else []), True
        recorded = fallbacks.get(call.call)
        if recorded:
            for fb in recorded:
                yield fb, fb.unique, False
        elif not call.overflow:
            # The trace recorded a lease that fit at recording time; a smaller simulated
            # capacity would make the runtime fall back per expert. Do not invent a
            # fallback for a lease that the trace already records as rejected.
            for expert in sorted(call.unique):
                synthetic = Call(-1, call.t_ns, call.layer, "O", 1, False, [expert], fallback_of=call.call)
                yield synthetic, [expert], False


def _capacities(trace: Trace, capacity: Optional[int], capacity_fraction: Optional[float]) -> Dict[int, int]:
    result: Dict[int, int] = {}
    if capacity is not None and capacity <= 0:
        raise ValueError("capacity must be positive")
    if capacity_fraction is not None:
        if not (0.0 < capacity_fraction <= 1.0):
            raise ValueError("capacity_fraction must be in (0, 1]")
    for lid, layer in trace.layers.items():
        if capacity is not None:
            result[lid] = capacity
        elif capacity_fraction is not None:
            result[lid] = max(1, int(round(layer.num_expert * capacity_fraction)))
        else:
            result[lid] = layer.capacity
    return result


def _offline_envelope(trace: Trace) -> dict:
    return {
        "offline_only": True,
        "runtime_acceptance": "NO",
        "workload_provenance": "offline trace input; synthetic traces are not live workloads",
        "trace": {
            "layers": len(trace.layers),
            "calls": len(trace.calls),
            "overflow_calls": sum(1 for c in trace.calls if c.kind == "S" and c.overflow),
            "fallback_calls": sum(1 for c in trace.calls if c.fallback_of is not None),
        },
    }


def replay(trace: Trace,
           policy: str,
           capacity: Optional[int] = None,
           capacity_fraction: Optional[float] = None,
           legacy_partial_lease: bool = False) -> dict:
    if policy not in POLICIES:
        raise ValueError(f"unknown policy {policy!r}")
    capacities = _capacities(trace, capacity, capacity_fraction)
    steps = list(_logical_steps(trace, capacities, legacy_partial_lease))
    caches: Dict[int, Policy] = {}
    for lid in trace.layers:
        if policy == "opt":
            future = [e for call, experts, _ in steps if call.layer == lid for e in experts]
            caches[lid] = Belady(capacities[lid], future)
        elif policy == "lru":
            caches[lid] = ExactLRU(capacities[lid])
        elif policy == "clock":
            caches[lid] = Clock(capacities[lid])
        else:
            caches[lid] = TwoQ(capacities[lid])

    total = Counters()
    by_phase: Dict[str, Counters] = defaultdict(Counters)
    by_model: Dict[str, Counters] = defaultdict(Counters)
    for call, experts, overflowed in steps:
        layer = trace.layers[call.layer]
        cache = caches[call.layer]
        phase = phase_of(call, layer)
        pinned: Set[int] = set()
        loads = 0
        for expert in experts:
            hit, _slot, evicted = cache.access(expert, pinned)
            pinned.add(expert)
            loads += 0 if hit else 1
            for c in (total, by_phase[phase], by_model[layer.model_key]):
                c.add_access(hit, evicted, layer.expert_bytes)
        if call.kind == "S":
            for c in (total, by_phase[phase], by_model[layer.model_key]):
                c.lease_calls += 1
                if overflowed:
                    c.overflow_calls += 1
                    c.overflow_partial_loads += loads

    result = {
        "schema": SCHEMA,
        "policy": policy,
        "legacy_partial_lease": legacy_partial_lease,
        "capacity": capacity,
        "capacity_fraction": capacity_fraction,
        "total": total.as_dict(),
        "by_phase": {k: v.as_dict() for k, v in sorted(by_phase.items())},
        "by_model": {k: v.as_dict() for k, v in sorted(by_model.items())},
        "bytes_known": all(l.expert_bytes > 0 for l in trace.layers.values()),
        "logical_bytes": _logical_bytes(total, "replay expert_bytes per simulated miss"),
        "physical_bytes": _physical_bytes(),
    }
    result.update(_offline_envelope(trace))
    return result


def verify_lru(trace: Trace, include_decisions: bool = False) -> dict:
    """Replay recorded capacities with exact LRU and compare every recorded decision."""
    caches = {lid: ExactLRU(layer.capacity) for lid, layer in trace.layers.items()}
    checked = 0
    hits = misses = 0
    requested = read = copied = 0
    unknown_misses = 0
    mismatches: List[dict] = []
    decisions: List[dict] = []
    for call in trace.calls:
        cache = caches[call.layer]
        layer = trace.layers[call.layer]
        pinned: Set[int] = set()
        # The runtime rejects an overflowing lease before touching the cache.
        expected = [] if call.kind == "S" and call.overflow else call.unique
        if call.kind == "S" and call.overflow != (len(call.unique) > layer.capacity):
            mismatches.append({"call": call.call, "reason": "overflow status does not match capacity"})
        if [ev.expert for ev in call.events] != list(expected):
            mismatches.append({"call": call.call, "reason": "recorded experts differ from lease order",
                               "recorded": [ev.expert for ev in call.events], "expected": list(expected)})
            continue
        for ev in call.events:
            hit, slot, evicted = cache.access(ev.expert, pinned)
            pinned.add(ev.expert)
            checked += 1
            if hit:
                hits += 1
            else:
                misses += 1
                if ev.bytes > 0:
                    requested += ev.bytes
                    read += ev.bytes
                    copied += ev.bytes
                else:
                    unknown_misses += 1
            if (hit, slot, evicted) != (ev.hit, ev.slot, ev.evicted):
                mismatches.append({"call": call.call, "expert": ev.expert,
                                   "recorded": [ev.hit, ev.slot, ev.evicted], "replayed": [hit, slot, evicted]})
            if include_decisions:
                decisions.append({
                    "call": call.call,
                    "expert": ev.expert,
                    "hit": hit,
                    "slot": slot,
                    "evicted": evicted,
                })
    logical = {
        "requested": requested if not unknown_misses else PHYSICAL_NOT_EXPOSED,
        "read_from_storage": read if not unknown_misses else PHYSICAL_NOT_EXPOSED,
        "copied_to_slots": copied if not unknown_misses else PHYSICAL_NOT_EXPOSED,
        "unknown_misses": unknown_misses,
        "source": "recorded E bytes and per-layer expert_bytes",
        "note": "logical expert payload accounting only; not a physical device measurement",
    }
    out = {
        "schema": SCHEMA,
        "checked_events": checked,
        "hits": hits,
        "misses": misses,
        "mismatches": len(mismatches),
        "first_mismatches": mismatches[:10],
        "logical_bytes": logical,
        "physical_bytes": _physical_bytes(),
        "bytes_known": all(l.expert_bytes > 0 for l in trace.layers.values()),
    }
    if include_decisions:
        out["decisions"] = decisions
    out.update(_offline_envelope(trace))
    return out


def _quantile(sorted_values: List[int], q: float) -> Optional[int]:
    if not sorted_values:
        return None
    idx = min(len(sorted_values) - 1, max(0, int(math.ceil(q * len(sorted_values))) - 1))
    return sorted_values[idx]


def measured_summary(trace: Trace) -> dict:
    """Aggregate the timings and logical bytes the runtime actually recorded."""
    loads = [ev for call in trace.calls for ev in call.events if not ev.hit]
    hits = sum(1 for call in trace.calls for ev in call.events if ev.hit)
    per_load_ns = sorted(ev.read_ns + ev.transform_ns + ev.copy_ns for ev in loads)
    read_ns = sum(ev.read_ns for ev in loads)
    transform_ns = sum(ev.transform_ns for ev in loads)
    copy_ns = sum(ev.copy_ns for ev in loads)
    busy = read_ns + transform_ns + copy_ns
    span_ns = (trace.calls[-1].t_ns - trace.calls[0].t_ns) if len(trace.calls) > 1 else 0
    unknown = sum(1 for ev in loads if ev.bytes <= 0)
    logical_read = sum(ev.bytes for ev in loads)
    out = {
        "schema": SCHEMA,
        "layers": len(trace.layers),
        "models": len({l.model_key for l in trace.layers.values()}),
        "calls": len(trace.calls),
        "overflow_calls": sum(1 for c in trace.calls if c.kind == "S" and c.overflow),
        "fallback_calls": sum(1 for c in trace.calls if c.fallback_of is not None),
        "hits": hits,
        "loads": len(loads),
        "reads": sum(ev.reads for ev in loads),
        "read_ms": read_ns / 1e6,
        "transform_ms": transform_ns / 1e6,
        "copy_ms": copy_ns / 1e6,
        "share_read": read_ns / busy if busy else None,
        "share_transform": transform_ns / busy if busy else None,
        "share_copy": copy_ns / busy if busy else None,
        "load_us_p50": _quantile(per_load_ns, 0.50) / 1e3 if per_load_ns else None,
        "load_us_p95": _quantile(per_load_ns, 0.95) / 1e3 if per_load_ns else None,
        "load_us_p99": _quantile(per_load_ns, 0.99) / 1e3 if per_load_ns else None,
        "trace_span_ms": span_ns / 1e6,
        "logical_bytes": {
            "requested": logical_read if not unknown else PHYSICAL_NOT_EXPOSED,
            "read_from_storage": logical_read if not unknown else PHYSICAL_NOT_EXPOSED,
            "copied_to_slots": logical_read if not unknown else PHYSICAL_NOT_EXPOSED,
            "unknown_misses": unknown,
            "source": "recorded E bytes",
            "note": "logical expert payload accounting only; not a physical device measurement",
        },
        "physical_bytes": _physical_bytes(),
        "bytes_known": all(l.expert_bytes > 0 for l in trace.layers.values()),
    }
    out.update(_offline_envelope(trace))
    return out


def _per_token(result: dict, committed_tokens: Optional[int]) -> None:
    if not committed_tokens:
        return
    if committed_tokens < 0:
        raise ValueError("committed_tokens must be non-negative")
    total = result["total"]
    total["misses_per_committed_token"] = total["misses"] / committed_tokens
    logical = result["logical_bytes"]
    if logical["read_from_storage"] == PHYSICAL_NOT_EXPOSED:
        total["logical_bytes_per_committed_token"] = PHYSICAL_NOT_EXPOSED
    else:
        total["logical_bytes_per_committed_token"] = logical["read_from_storage"] / committed_tokens
    total["physical_nvme_bytes_per_committed_token"] = PHYSICAL_NOT_EXPOSED


def _load(args) -> Trace:
    with open(args.trace, "r", encoding="utf-8", newline="") as fh:
        return parse_trace(fh)


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_sum = sub.add_parser("summary", help="aggregate recorded load timings and logical bytes")
    p_sum.add_argument("trace")

    p_ver = sub.add_parser("verify", help="check exact LRU replay against every recorded decision")
    p_ver.add_argument("trace")
    p_ver.add_argument("--decisions", action="store_true", help="include the full replayed slot sequence")

    p_sim = sub.add_parser("simulate", help="offline replay with alternative policies/capacities")
    p_sim.add_argument("trace")
    p_sim.add_argument("--policy", action="append", choices=POLICIES, help="repeatable; default: all")
    group = p_sim.add_mutually_exclusive_group()
    group.add_argument("--capacity", type=int, action="append", help="slots per layer; repeatable")
    group.add_argument("--capacity-fraction", type=float, action="append", help="fraction of num_expert; repeatable")
    p_sim.add_argument(
        "--legacy-partial-lease",
        action="store_true",
        help="offline what-if for the pre-fix runtime; never a policy promotion",
    )
    p_sim.add_argument("--committed-tokens", type=int, help="accepted output tokens from the serving benchmark")

    args = parser.parse_args(argv)
    try:
        trace = _load(args)
    except (OSError, TraceFormatError) as exc:
        json.dump({"schema": SCHEMA, "error": str(exc), "kind": "trace_format_error",
                   "offline_only": True, "runtime_acceptance": "NO"}, sys.stderr, indent=2)
        sys.stderr.write("\n")
        return 2

    if args.command == "summary":
        out = measured_summary(trace)
    elif args.command == "verify":
        out = verify_lru(trace, include_decisions=args.decisions)
    else:
        policies = args.policy or list(POLICIES)
        sizes: List[Tuple[Optional[int], Optional[float]]]
        if args.capacity:
            sizes = [(c, None) for c in args.capacity]
        elif args.capacity_fraction:
            sizes = [(None, f) for f in args.capacity_fraction]
        else:
            sizes = [(None, None)]
        out = []
        try:
            for cap, frac in sizes:
                for policy in policies:
                    result = replay(trace, policy, cap, frac, args.legacy_partial_lease)
                    _per_token(result, args.committed_tokens)
                    out.append(result)
        except ValueError as exc:
            json.dump({"schema": SCHEMA, "error": str(exc), "kind": "invalid_argument",
                       "offline_only": True, "runtime_acceptance": "NO"}, sys.stderr, indent=2)
            sys.stderr.write("\n")
            return 2

    json.dump(out, sys.stdout, indent=2)
    sys.stdout.write("\n")
    if args.command == "verify" and out["mismatches"]:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
