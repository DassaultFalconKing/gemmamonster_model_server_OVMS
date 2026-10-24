# Copyright (C) 2018-2026 Intel Corporation
# SPDX-License-Identifier: Apache-2.0
"""Deterministic offline logical-to-physical expert layout optimizer (CIB2 PGP-02).

This tool reads one *derived* pack-layout profile and emits a complete
``placement[logical_expert_id] = physical_position`` permutation for a single
scoped compiled layer.  It never reads a model, Pack V1 file, ``.bin`` weight
file, or runtime trace; it never writes payload bytes, tensors, a pack V2
manifest, or resident-mode state.

The profile contract is ``cib2.pack_layout_profile.v1``.  It is a small,
sanitized, derived offline input; it is **not** an implementation of
``cib2.expert_trace.v2`` and it does not claim that any trace exists.  Profiles
may be synthetic fixtures.  Synthetic/offline output is never runtime, profile,
or pack acceptance.

Fallback policy:

* no supplied profile (with an explicit expert count) -> identity placement;
* valid profile without usable frequency/coaccess evidence -> identity;
* coaccess ordering that does not improve the documented offline objective
  over identity -> identity;
* a supplied malformed, incomplete, duplicate, out-of-range, non-finite,
  unsanitized, or provenance-mismatched profile -> hard failure (exit 2),
  never a silent fallback.

The only handoff is the existing Pack V1 API ``PackLayout::set_placement``.
Physical reordering is not a runtime benefit claim, and native full-payload
parity is NOT_RUN until native Pack V1 P3/P5 acceptance.
"""

from __future__ import annotations

import argparse
import hashlib
import heapq
import json
import math
import os
import re
import sys
import tempfile
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

PROFILE_SCHEMA = "cib2.pack_layout_profile.v1"
PROFILE_KIND = "cib2_pack_layout_profile"
LAYOUT_SCHEMA = "cib2.pack_layout.v1"
LAYOUT_KIND = "cib2_pack_layout"
ERROR_KIND = "cib2_pack_layout_error"

STRATEGIES = ("identity", "frequency", "coaccess")

MAX_EXPERTS = 16384
MAX_COACCESS_PAIRS = 200_000
MAX_PROFILE_BYTES = 32 * 1024 * 1024
MAX_COUNT = (1 << 53) - 1
MAX_READ_COST_US = 1.0e12
MAX_COACCESS_WEIGHT = 1.0e18
MAX_LAYER_ID = 1_000_000
MAX_SEED = (1 << 63) - 1

# Deterministic local refinement is bounded so a large profile cannot turn the
# offline tool into an unbounded search.  Greedy ordering still applies.
MAX_REFINE_EXPERTS = 256
MAX_REFINE_PAIRS = 5_000
MAX_REFINE_PASSES = 4

SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
COMPILED_LAYER_KEY_RE = re.compile(r"^[A-Za-z0-9._:-]{1,256}$")
MODEL_KEY_RE = re.compile(r"^[A-Za-z0-9._-]{1,128}$")
PROFILE_KEY_RE = re.compile(r"^[A-Za-z0-9._-]{1,128}$")

TOP_LEVEL_KEYS = (
    "schema",
    "kind",
    "complete",
    "synthetic",
    "provenance",
    "scope",
    "expert_count",
    "experts",
    "coaccess",
)
PROVENANCE_KEYS = (
    "checkpoint_sha",
    "export_sha",
    "compiled_layer_key",
    "quant_profile_sha",
    "profile_key",
    "source",
    "sanitized",
)
SCOPE_KEYS = ("model_key", "logical_layer_id")
EXPERT_KEYS = ("logical_expert_id", "miss_count", "read_cost_us")
COACCESS_KEYS = ("expert_a", "expert_b", "weight")

PROVENANCE_SOURCES = ("synthetic", "offline_trace_derived")

POLICY_BLOCK = {
    "pack_format": "V1_PLACEMENT_TABLE_ONLY",
    "payload_bytes": "UNCHANGED",
    "tensors": "UNTOUCHED",
    "pack_v2": False,
    "resident_mode": "UNCHANGED",
    "prefetch": "OFF",
    "pinning": "OFF",
    "router_top_k": "UNCHANGED",
}

NON_CLAIMS = [
    "does not parse or implement cib2.expert_trace.v2; the input is a derived offline profile",
    "does not read model weights, BIN files, or Pack V1 files",
    "does not build or write pack files, Pack V2 manifests, payload bytes, or tensors",
    "does not change resident mode, prefetch, pinning, or router top-k",
    "physical record reordering is not a measured runtime or throughput benefit",
    "native Pack V1 full-payload parity is NOT_RUN until P3/P5 acceptance",
]


class ProfileError(ValueError):
    """A supplied layout profile is missing required data or is unsafe to use."""


class LayoutError(ValueError):
    """An emitted layout is not a complete, consistent permutation."""


@dataclass(frozen=True)
class ExpertEvidence:
    logical_expert_id: int
    miss_count: int
    read_cost_us: float
    score: float


@dataclass(frozen=True)
class CoaccessPair:
    expert_a: int
    expert_b: int
    weight: float


@dataclass(frozen=True)
class ValidatedProfile:
    synthetic: bool
    provenance: Mapping[str, Any]
    scope: Mapping[str, Any]
    expert_count: int
    experts: Tuple[ExpertEvidence, ...]
    coaccess: Tuple[CoaccessPair, ...]
    # Set only when validated from exact profile bytes (CLI / load_profile_bytes).
    source_sha256: Optional[str] = None


def _reject_unknown(obj: Mapping[str, Any], allowed: Sequence[str], where: str) -> None:
    unknown = sorted(set(obj) - set(allowed))
    if unknown:
        raise ProfileError(f"{where}: unknown field(s) {unknown}; unsupported or unsafe input")


def _require_present(obj: Mapping[str, Any], required: Sequence[str], where: str) -> None:
    missing = [key for key in required if key not in obj]
    if missing:
        raise ProfileError(f"{where}: missing required field(s) {missing}")


def _require_bool(value: Any, where: str) -> bool:
    if not isinstance(value, bool):
        raise ProfileError(f"{where}: expected a JSON boolean")
    return value


def _require_int(value: Any, where: str, minimum: int, maximum: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ProfileError(f"{where}: expected an integer")
    if value < minimum or value > maximum:
        raise ProfileError(f"{where}: {value} outside {minimum}..{maximum}")
    return value


def _require_number(value: Any, where: str, minimum: float, maximum: float) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ProfileError(f"{where}: expected a finite number")
    # Check integer bounds before converting: an enormous but valid JSON
    # integer could overflow float(), or round into the permitted range.
    if isinstance(value, int) and (value < minimum or value > maximum):
        raise ProfileError(f"{where}: integer outside {minimum}..{maximum}")
    try:
        number = float(value)
    except (OverflowError, ValueError) as exc:
        raise ProfileError(f"{where}: number cannot be represented as a finite float") from exc
    if not math.isfinite(number):
        raise ProfileError(f"{where}: non-finite number is not allowed")
    if number < minimum or number > maximum:
        raise ProfileError(f"{where}: {number} outside {minimum}..{maximum}")
    return number


def _require_sha256(value: Any, where: str) -> str:
    if not isinstance(value, str) or not SHA256_RE.fullmatch(value):
        raise ProfileError(f"{where}: expected 64 lowercase hexadecimal characters")
    return value


def _require_key(value: Any, where: str, pattern: "re.Pattern[str]") -> str:
    if not isinstance(value, str) or not pattern.fullmatch(value):
        raise ProfileError(f"{where}: expected a non-empty sanitized identifier")
    return value


def _unique_object(pairs: Iterable[Tuple[str, Any]]) -> Dict[str, Any]:
    result: Dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ProfileError(f"profile: duplicate JSON key {key!r}")
        result[key] = value
    return result


def _normalized_pairs(profile: Mapping[str, Any], expert_count: int) -> Tuple[CoaccessPair, ...]:
    raw_pairs = profile["coaccess"]
    if not isinstance(raw_pairs, list):
        raise ProfileError("profile.coaccess: expected a JSON array")
    if len(raw_pairs) > MAX_COACCESS_PAIRS:
        raise ProfileError(
            f"profile.coaccess: {len(raw_pairs)} pairs exceeds bound {MAX_COACCESS_PAIRS}"
        )
    seen: set = set()
    normalized: List[CoaccessPair] = []
    for index, raw in enumerate(raw_pairs):
        where = f"profile.coaccess[{index}]"
        if not isinstance(raw, dict):
            raise ProfileError(f"{where}: expected a JSON object")
        _reject_unknown(raw, COACCESS_KEYS, where)
        _require_present(raw, COACCESS_KEYS, where)
        a = _require_int(raw["expert_a"], f"{where}.expert_a", 0, expert_count - 1)
        b = _require_int(raw["expert_b"], f"{where}.expert_b", 0, expert_count - 1)
        if a == b:
            raise ProfileError(f"{where}: coaccess pair repeats expert {a}")
        weight = _require_number(raw["weight"], f"{where}.weight", 0.0, MAX_COACCESS_WEIGHT)
        key = (a, b) if a < b else (b, a)
        if key in seen:
            raise ProfileError(f"{where}: duplicate coaccess pair {key[0]},{key[1]}")
        seen.add(key)
        normalized.append(CoaccessPair(key[0], key[1], weight))
    normalized.sort(key=lambda pair: (pair.expert_a, pair.expert_b, pair.weight))
    return tuple(normalized)


def validate_profile(profile: Any) -> ValidatedProfile:
    """Strictly validate one ``cib2.pack_layout_profile.v1`` object.

    Rejects incomplete/unsanitized profiles, duplicate experts or pairs, range
    errors, non-finite costs/weights, provenance/synthesis mismatches, and
    unsupported fields (including payload/tensor/resident-mode payloads).
    """
    if not isinstance(profile, dict):
        raise ProfileError("profile: expected a JSON object")
    _reject_unknown(profile, TOP_LEVEL_KEYS, "profile")
    _require_present(profile, TOP_LEVEL_KEYS, "profile")

    if profile["schema"] != PROFILE_SCHEMA:
        raise ProfileError(
            f"profile.schema: unsupported {profile['schema']!r}; expected {PROFILE_SCHEMA!r}"
        )
    if profile["kind"] != PROFILE_KIND:
        raise ProfileError(f"profile.kind: expected {PROFILE_KIND!r}")
    if _require_bool(profile["complete"], "profile.complete") is not True:
        raise ProfileError("profile.complete: an incomplete profile cannot drive a layout")
    synthetic = _require_bool(profile["synthetic"], "profile.synthetic")

    provenance = profile["provenance"]
    if not isinstance(provenance, dict):
        raise ProfileError("profile.provenance: expected a JSON object")
    _reject_unknown(provenance, PROVENANCE_KEYS, "profile.provenance")
    _require_present(provenance, PROVENANCE_KEYS, "profile.provenance")
    _require_sha256(provenance["checkpoint_sha"], "profile.provenance.checkpoint_sha")
    _require_sha256(provenance["export_sha"], "profile.provenance.export_sha")
    _require_key(
        provenance["compiled_layer_key"],
        "profile.provenance.compiled_layer_key",
        COMPILED_LAYER_KEY_RE,
    )
    _require_sha256(provenance["quant_profile_sha"], "profile.provenance.quant_profile_sha")
    _require_key(provenance["profile_key"], "profile.provenance.profile_key", PROFILE_KEY_RE)
    source = provenance["source"]
    if source not in PROVENANCE_SOURCES:
        raise ProfileError(
            f"profile.provenance.source: expected one of {PROVENANCE_SOURCES}, got {source!r}"
        )
    if _require_bool(provenance["sanitized"], "profile.provenance.sanitized") is not True:
        raise ProfileError("profile.provenance.sanitized: must be true; private data is not accepted")
    if synthetic != (source == "synthetic"):
        raise ProfileError(
            "profile: provenance mismatch; synthetic must be true exactly when "
            "provenance.source is 'synthetic'"
        )

    scope = profile["scope"]
    if not isinstance(scope, dict):
        raise ProfileError("profile.scope: expected a JSON object")
    _reject_unknown(scope, SCOPE_KEYS, "profile.scope")
    _require_present(scope, SCOPE_KEYS, "profile.scope")
    _require_key(scope["model_key"], "profile.scope.model_key", MODEL_KEY_RE)
    _require_int(scope["logical_layer_id"], "profile.scope.logical_layer_id", 0, MAX_LAYER_ID)

    expert_count = _require_int(
        profile["expert_count"], "profile.expert_count", 1, MAX_EXPERTS
    )
    raw_experts = profile["experts"]
    if not isinstance(raw_experts, list):
        raise ProfileError("profile.experts: expected a JSON array")
    if len(raw_experts) > expert_count:
        raise ProfileError("profile.experts: more entries than expert_count")
    experts: List[ExpertEvidence] = []
    seen_experts: set = set()
    for index, raw in enumerate(raw_experts):
        where = f"profile.experts[{index}]"
        if not isinstance(raw, dict):
            raise ProfileError(f"{where}: expected a JSON object")
        _reject_unknown(raw, EXPERT_KEYS, where)
        _require_present(raw, EXPERT_KEYS, where)
        expert_id = _require_int(
            raw["logical_expert_id"], f"{where}.logical_expert_id", 0, expert_count - 1
        )
        if expert_id in seen_experts:
            raise ProfileError(f"{where}: duplicate logical_expert_id {expert_id}")
        seen_experts.add(expert_id)
        miss_count = _require_int(
            raw["miss_count"], f"{where}.miss_count", 0, MAX_COUNT
        )
        read_cost_us = _require_number(
            raw["read_cost_us"], f"{where}.read_cost_us", 0.0, MAX_READ_COST_US
        )
        score = miss_count * read_cost_us
        if not math.isfinite(score):
            raise ProfileError(f"{where}: miss_count * read_cost_us is not finite")
        experts.append(ExpertEvidence(expert_id, miss_count, read_cost_us, score))
    experts.sort(key=lambda item: item.logical_expert_id)

    coaccess = _normalized_pairs(profile, expert_count)

    return ValidatedProfile(
        synthetic=synthetic,
        provenance=dict(provenance),
        scope=dict(scope),
        expert_count=expert_count,
        experts=tuple(experts),
        coaccess=coaccess,
    )


def load_profile_bytes(data: bytes) -> ValidatedProfile:
    """Parse and validate exact profile bytes (UTF-8 JSON, bounded size)."""
    if not isinstance(data, (bytes, bytearray)):
        raise ProfileError("profile: expected bytes")
    if len(data) > MAX_PROFILE_BYTES:
        raise ProfileError(
            f"profile: {len(data)} bytes exceeds bound {MAX_PROFILE_BYTES}"
        )
    try:
        text = bytes(data).decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ProfileError(f"profile: not valid UTF-8: {exc}") from exc
    try:
        parsed = json.loads(text, object_pairs_hook=_unique_object)
    except ProfileError:
        raise
    except (json.JSONDecodeError, ValueError) as exc:
        raise ProfileError(f"profile: invalid JSON: {exc}") from exc
    validated = validate_profile(parsed)
    return replace(validated, source_sha256=profile_sha256(data))


def profile_sha256(data: bytes) -> str:
    """SHA-256 over the exact supplied profile bytes."""
    return hashlib.sha256(bytes(data)).hexdigest()


def _paths_collide(left: Path, right: Path) -> bool:
    """True when two paths name the same file, including hardlink/junction aliases."""
    try:
        if left.exists() and right.exists():
            return left.resolve().samefile(right.resolve())
    except OSError:
        pass
    return left.resolve() == right.resolve()


def _tie_key(seed: int, expert_id: int) -> bytes:
    return hashlib.sha256(f"{seed}:{expert_id}".encode("ascii")).digest()


def _frequency_result(profile: ValidatedProfile) -> Tuple[List[int], dict]:
    positive = sorted(
        (expert for expert in profile.experts if expert.score > 0.0),
        key=lambda expert: (-expert.score, expert.logical_expert_id),
    )
    evidenced_ids = [expert.logical_expert_id for expert in positive]
    zero_cost_ids = sorted(
        expert.logical_expert_id for expert in profile.experts if expert.score == 0.0
    )
    seen = {expert.logical_expert_id for expert in profile.experts}
    unseen_ids = [expert_id for expert_id in range(profile.expert_count) if expert_id not in seen]
    rest = sorted(set(zero_cost_ids) | set(unseen_ids))
    order = evidenced_ids + rest
    evidence = {
        "score_definition": "miss_count * read_cost_us (observed miss/read-cost evidence only)",
        "evidenced_expert_count": len(evidenced_ids),
        "evidenced_expert_ids": evidenced_ids,
        "zero_cost_expert_count": len(zero_cost_ids),
        "zero_cost_expert_ids": zero_cost_ids,
        "unseen_expert_count": len(unseen_ids),
        "unseen_expert_ids": unseen_ids,
        "score_total": sum(expert.score for expert in positive),
        "tie_break": "descending score, then ascending logical_expert_id",
        "seed_used": False,
    }
    return order, evidence


def _objective(order: Sequence[int], pairs: Sequence[CoaccessPair]) -> float:
    position = [0] * len(order)
    for physical, logical in enumerate(order):
        position[logical] = physical
    total = 0.0
    for pair in pairs:
        if pair.weight > 0.0:
            total += pair.weight * abs(position[pair.expert_a] - position[pair.expert_b])
    return total


def _refine_coaccess(
    order: List[int], pairs: Sequence[CoaccessPair]
) -> Tuple[List[int], str]:
    if len(order) > MAX_REFINE_EXPERTS or len(pairs) > MAX_REFINE_PAIRS:
        return order, "SKIPPED_BOUND"
    best = list(order)
    best_value = _objective(best, pairs)
    for _ in range(MAX_REFINE_PASSES):
        improved = False
        for index in range(len(best) - 1):
            candidate = list(best)
            candidate[index], candidate[index + 1] = candidate[index + 1], candidate[index]
            value = _objective(candidate, pairs)
            if value < best_value - 1e-12:
                best = candidate
                best_value = value
                improved = True
        if not improved:
            break
    return best, "APPLIED"


def _coaccess_result(
    profile: ValidatedProfile, seed: int
) -> Tuple[List[int], float, float, str]:
    count = profile.expert_count
    positive = [pair for pair in profile.coaccess if pair.weight > 0.0]
    identity_order = list(range(count))
    identity_value = _objective(identity_order, positive)
    if not positive:
        return identity_order, identity_value, identity_value, "NOT_APPLICABLE"

    adjacency: List[Dict[int, float]] = [dict() for _ in range(count)]
    incident = [0.0] * count
    for pair in positive:
        adjacency[pair.expert_a][pair.expert_b] = pair.weight
        adjacency[pair.expert_b][pair.expert_a] = pair.weight
        incident[pair.expert_a] += pair.weight
        incident[pair.expert_b] += pair.weight

    tie = [_tie_key(seed, expert_id) for expert_id in range(count)]
    placed = [False] * count
    connection = [0.0] * count
    order: List[int] = []

    anchor_heap: List[Tuple[float, bytes, int]] = [
        (-incident[expert_id], tie[expert_id], expert_id)
        for expert_id in range(count)
        if incident[expert_id] > 0.0
    ]
    heapq.heapify(anchor_heap)
    connection_heap: List[Tuple[float, bytes, int]] = []

    while len(order) < count:
        chosen: Optional[int] = None
        while connection_heap:
            neg_connection, _tie, expert_id = heapq.heappop(connection_heap)
            if placed[expert_id]:
                continue
            value = -neg_connection
            if value <= 0.0 or value != connection[expert_id]:
                continue
            chosen = expert_id
            break
        if chosen is None:
            while anchor_heap:
                neg_incident, _tie, expert_id = heapq.heappop(anchor_heap)
                if placed[expert_id] or incident[expert_id] <= 0.0:
                    continue
                chosen = expert_id
                break
        if chosen is None:
            # No edge-bearing expert remains.  Isolated experts follow in a
            # seeded deterministic order; this is not invented hotness.
            rest = [expert_id for expert_id in range(count) if not placed[expert_id]]
            rest.sort(key=lambda expert_id: (tie[expert_id], expert_id))
            order.extend(rest)
            break
        placed[chosen] = True
        order.append(chosen)
        for neighbour, weight in adjacency[chosen].items():
            if not placed[neighbour]:
                connection[neighbour] += weight
                heapq.heappush(
                    connection_heap,
                    (-connection[neighbour], tie[neighbour], neighbour),
                )

    refined, refinement = _refine_coaccess(order, positive)
    candidate_value = _objective(refined, positive)
    return refined, candidate_value, identity_value, refinement


def _inverse(placement: Sequence[int]) -> List[int]:
    order = [0] * len(placement)
    for logical, physical in enumerate(placement):
        order[physical] = logical
    return order


def _scope_block(profile: ValidatedProfile) -> dict:
    # Keep every identity key in its own field.  No key is concatenated,
    # derived from another, or silently merged.
    return {
        "model_key": profile.scope["model_key"],
        "logical_layer_id": profile.scope["logical_layer_id"],
        "checkpoint_sha": profile.provenance["checkpoint_sha"],
        "export_sha": profile.provenance["export_sha"],
        "compiled_layer_key": profile.provenance["compiled_layer_key"],
        "quant_profile_sha": profile.provenance["quant_profile_sha"],
        "profile_key": profile.provenance["profile_key"],
    }


def validate_layout(layout: Any) -> bool:
    """Re-check an emitted layout; raise ``LayoutError`` on any inconsistency."""
    if not isinstance(layout, dict):
        raise LayoutError("layout: expected a JSON object")
    if layout.get("schema") != LAYOUT_SCHEMA or layout.get("kind") != LAYOUT_KIND:
        raise LayoutError("layout: unexpected schema/kind")
    placement = layout.get("placement")
    order = layout.get("order")
    count = layout.get("expert_count")
    if isinstance(count, bool) or not isinstance(count, int) or not 1 <= count <= MAX_EXPERTS:
        raise LayoutError("layout.expert_count: invalid")
    if not isinstance(placement, list) or len(placement) != count:
        raise LayoutError("layout.placement: must contain exactly expert_count positions")
    if not isinstance(order, list) or len(order) != count:
        raise LayoutError("layout.order: must contain exactly expert_count logical IDs")
    for value in placement:
        if isinstance(value, bool) or not isinstance(value, int):
            raise LayoutError("layout.placement: non-integer physical position")
    for value in order:
        if isinstance(value, bool) or not isinstance(value, int):
            raise LayoutError("layout.order: non-integer logical ID")
    if sorted(placement) != list(range(count)):
        raise LayoutError("layout.placement: not a permutation of 0..expert_count-1")
    if sorted(order) != list(range(count)):
        raise LayoutError("layout.order: not a permutation of 0..expert_count-1")
    if _inverse(placement) != order:
        raise LayoutError("layout.order: not the exact inverse of placement")
    if layout.get("runtime_acceptance") != "NO":
        raise LayoutError("layout.runtime_acceptance: must remain NO")
    if layout.get("offline_only") is not True:
        raise LayoutError("layout.offline_only: must remain true")
    if any(layout.get(key) != "NO" for key in ("pack_acceptance", "profile_acceptance")):
        raise LayoutError("layout acceptance flags must remain NO")
    if layout.get("policy") != POLICY_BLOCK:
        raise LayoutError("layout.policy: offline placement cannot alter runtime policy")
    source = layout.get("source_profile")
    if not isinstance(source, dict) or not isinstance(source.get("supplied"), bool):
        raise LayoutError("layout.source_profile: missing explicit supplied flag")
    scope = layout.get("scope")
    if not source["supplied"]:
        if scope is not None or source.get("sha256") is not None:
            raise LayoutError("unprofiled layout must not claim source identity or scope")
        if placement != list(range(count)):
            raise LayoutError("unprofiled layout must remain identity")
    else:
        try:
            _require_sha256(source.get("sha256"), "layout.source_profile.sha256")
            if source.get("schema") != PROFILE_SCHEMA or source.get("complete") is not True:
                raise ProfileError("layout.source_profile: incomplete or unsupported profile")
            if not isinstance(scope, dict):
                raise ProfileError("layout.scope: required for supplied profile")
            required = ("model_key", "logical_layer_id", "checkpoint_sha", "export_sha",
                        "compiled_layer_key", "quant_profile_sha", "profile_key")
            _require_present(scope, required, "layout.scope")
            _reject_unknown(scope, required, "layout.scope")
            for key in ("checkpoint_sha", "export_sha", "quant_profile_sha"):
                _require_sha256(scope[key], "layout.scope." + key)
            _require_key(scope["model_key"], "layout.scope.model_key", MODEL_KEY_RE)
            _require_key(scope["compiled_layer_key"], "layout.scope.compiled_layer_key", COMPILED_LAYER_KEY_RE)
            _require_key(scope["profile_key"], "layout.scope.profile_key", PROFILE_KEY_RE)
            _require_int(scope["logical_layer_id"], "layout.scope.logical_layer_id", 0, MAX_LAYER_ID)
        except ProfileError as exc:
            raise LayoutError(str(exc)) from exc
    return True


def build_layout(
    profile: Optional[ValidatedProfile],
    strategy: str,
    seed: int = 0,
    *,
    expert_count: Optional[int] = None,
    source_sha256: Optional[str] = None,
) -> dict:
    """Emit a validated deterministic layout for one scoped layer.

    ``profile is None`` requires an explicit ``expert_count`` and produces the
    documented identity fallback.  A supplied profile must already be validated;
    malformed profiles are rejected before this call.
    """
    if strategy not in STRATEGIES:
        raise LayoutError(f"strategy: expected one of {STRATEGIES}, got {strategy!r}")
    seed = _require_int(seed, "seed", 0, MAX_SEED)
    if profile is None:
        if expert_count is None:
            raise LayoutError("no profile supplied and no explicit expert_count; cannot emit identity")
        count = _require_int(expert_count, "expert_count", 1, MAX_EXPERTS)
        if source_sha256 is not None:
            raise LayoutError("source_sha256 is only valid with a supplied profile")
    else:
        if expert_count is not None and expert_count != profile.expert_count:
            raise LayoutError("expert_count conflicts with the supplied profile")
        count = profile.expert_count
        if source_sha256 is None or not SHA256_RE.fullmatch(source_sha256):
            raise LayoutError("a supplied profile requires its exact 64-hex source SHA-256")
        if profile.source_sha256 is not None and profile.source_sha256 != source_sha256:
            raise LayoutError(
                "source_sha256 does not match the exact profile bytes used to validate"
            )

    fallback_used = False
    fallback_reason: Optional[str] = None
    objective: dict
    evidence: Optional[dict] = None

    if profile is None:
        order = list(range(count))
        fallback_used = True
        fallback_reason = "no_profile_supplied"
        objective = {
            "kind": "identity",
            "note": "no profile supplied; identity placement with no invented hotness",
        }
        effective_strategy = "identity"
    elif strategy == "identity":
        order = list(range(count))
        effective_strategy = "identity"
        objective = {
            "kind": "identity",
            "note": "identity requested; profile evidence is not applied",
        }
    elif strategy == "frequency":
        candidate, evidence = _frequency_result(profile)
        effective_strategy = "frequency"
        if not evidence["evidenced_expert_count"]:
            order = list(range(count))
            fallback_used = True
            fallback_reason = "no_observed_frequency_evidence"
            objective = {
                "kind": "frequency_order_not_applied",
                "note": "no positive miss_count*read_cost_us evidence; identity placement",
            }
        else:
            order = candidate
            objective = {"kind": "frequency_order", "evidence": evidence}
    else:
        candidate, candidate_value, identity_value, refinement = _coaccess_result(profile, seed)
        effective_strategy = "coaccess"
        positive_pairs = sum(1 for pair in profile.coaccess if pair.weight > 0.0)
        objective = {
            "kind": "coaccess_weighted_distance",
            "definition": "sum(weight * abs(position_a - position_b)) over supplied positive-weight pairs",
            "supplied_positive_pair_count": positive_pairs,
            "candidate_value": candidate_value,
            "identity_baseline_value": identity_value,
            "refinement": refinement,
            "greedy_tie_break": "sha256(seed:logical_expert_id), then logical_expert_id",
        }
        if positive_pairs == 0:
            order = list(range(count))
            fallback_used = True
            fallback_reason = "no_coaccess_evidence"
            objective["note"] = "no positive-weight coaccess pairs; identity placement"
        elif candidate_value >= identity_value - 1e-12:
            order = list(range(count))
            fallback_used = True
            fallback_reason = "coaccess_no_offline_improvement"
            objective["note"] = (
                "coaccess candidate did not strictly improve the offline objective; "
                "identity retained, no runtime benefit claimed"
            )
        else:
            order = candidate

    if fallback_used:
        # Placement is identity; do not leave the requested strategy name as
        # strategy_effective — consumers must not mis-record which table applied.
        effective_strategy = "identity"

    placement = _inverse(order)
    layout = {
        "schema": LAYOUT_SCHEMA,
        "kind": LAYOUT_KIND,
        "status": "OK",
        "offline_only": True,
        "runtime_acceptance": "NO",
        "profile_acceptance": "NO",
        "pack_acceptance": "NO",
        "strategy_requested": strategy,
        "strategy_effective": effective_strategy,
        "seed": seed,
        "seed_used_for": "coaccess tie-break only",
        "expert_count": count,
        "scope": _scope_block(profile) if profile is not None else None,
        "source_profile": {
            "supplied": profile is not None,
            "schema": PROFILE_SCHEMA if profile is not None else None,
            "sha256": source_sha256 if profile is not None else None,
            "synthetic": profile.synthetic if profile is not None else None,
            "complete": True if profile is not None else None,
            "provenance_source": profile.provenance["source"] if profile is not None else None,
            "expert_evidence_entries": len(profile.experts) if profile is not None else 0,
            "coaccess_pairs": len(profile.coaccess) if profile is not None else 0,
        },
        "fallback": {
            "used": fallback_used,
            "reason": fallback_reason,
            "identity_used": fallback_used or effective_strategy == "identity",
            "note": (
                "explicit identity fallback; no hotness was invented"
                if fallback_used
                else "no fallback"
            ),
        },
        "placement": placement,
        "order": order,
        "placement_contract": (
            "placement[logical_expert_id] = physical_position; "
            "order[physical_position] = logical_expert_id; both are full permutations"
        ),
        "validation": {
            "permutation": True,
            "logical_ids_preserved": True,
            "inverse_consistent": True,
            "physical_positions_complete": True,
        },
        "objective": objective,
        "policy": dict(POLICY_BLOCK),
        "handoff": {
            "api": "PackLayout::set_placement",
            "build_api": "build_pack(..., placement)",
            "pack_format": "native Pack V1; no pack file is read or written by this tool",
            "native_full_payload_parity": "NOT_RUN",
            "native_full_payload_parity_reason": (
                "requires native Pack V1 P3 build/read and P5 independent full-pack verifier"
            ),
        },
        "non_claims": list(NON_CLAIMS),
        "warnings": [],
    }
    if profile is None:
        layout["warnings"].append("no profile supplied; identity fallback only")
    if profile is not None and profile.synthetic:
        layout["warnings"].append(
            "synthetic profile fixture: results are not runtime, profile, or pack acceptance"
        )
    layout["warnings"].append(
        "offline placement table only; physical reordering is not a measured performance gain"
    )
    validate_layout(layout)
    return layout


def write_layout(path: str, layout: dict) -> None:
    """Write a validated layout atomically; do not create a partial JSON file."""
    validate_layout(layout)
    target = Path(path)
    if target.suffix.lower() != ".json":
        raise LayoutError("output must be a .json layout, never a weight or pack file")
    if not target.parent.exists():
        raise LayoutError(f"output directory does not exist: {target.parent}")
    text = json.dumps(layout, indent=2, allow_nan=False) + "\n"
    fd, temporary = tempfile.mkstemp(
        prefix=target.name + ".", suffix=".tmp", dir=str(target.parent)
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, target)
    except BaseException:
        try:
            os.unlink(temporary)
        except OSError:
            pass
        raise


def _error_output(message: str, error_kind: str = "profile_rejected") -> dict:
    return {
        "schema": LAYOUT_SCHEMA,
        "kind": ERROR_KIND,
        "status": "REJECTED",
        "error_kind": error_kind,
        "error": message,
        "offline_only": True,
        "runtime_acceptance": "NO",
        "profile_acceptance": "NO",
        "pack_acceptance": "NO",
    }


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Emit a deterministic offline Pack V1 placement permutation for one "
            "scoped layer. Offline only; never runtime, profile, or pack acceptance."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--profile", metavar="JSON", help="cib2.pack_layout_profile.v1 input")
    parser.add_argument("--output", required=True, metavar="JSON", help="layout JSON output path")
    parser.add_argument("--strategy", required=True, choices=STRATEGIES)
    parser.add_argument("--seed", type=int, default=0, help="coaccess tie-break seed (default 0)")
    parser.add_argument(
        "--expert-count",
        type=int,
        help="required only when --profile is omitted; emits explicit identity fallback",
    )
    args = parser.parse_args(argv)

    try:
        if args.seed < 0 or args.seed > MAX_SEED:
            raise LayoutError(f"seed: {args.seed} outside 0..{MAX_SEED}")
        if args.profile and args.expert_count is not None:
            raise LayoutError("--expert-count is only valid when --profile is omitted")
        if args.profile:
            profile_path = Path(args.profile)
            if _paths_collide(profile_path, Path(args.output)):
                raise LayoutError("output must not overwrite its source profile")
            if profile_path.suffix.lower() == ".bin":
                raise ProfileError("profile: refusing .bin input; only sanitized JSON profiles are accepted")
            if not profile_path.is_file():
                raise ProfileError(f"profile: not a readable regular file: {args.profile}")
            size = profile_path.stat().st_size
            if size > MAX_PROFILE_BYTES:
                raise ProfileError(
                    f"profile: {size} bytes exceeds bound {MAX_PROFILE_BYTES}"
                )
            data = profile_path.read_bytes()
            profile = load_profile_bytes(data)
            source_sha = profile_sha256(data)
            layout = build_layout(profile, args.strategy, args.seed, source_sha256=source_sha)
        else:
            if args.expert_count is None:
                raise LayoutError(
                    "no --profile supplied; --expert-count is required for explicit identity fallback"
                )
            layout = build_layout(
                None, args.strategy, args.seed, expert_count=args.expert_count
            )
        validate_layout(layout)
        write_layout(args.output, layout)
    except (ProfileError, LayoutError, OSError) as exc:
        json.dump(_error_output(str(exc)), sys.stderr, indent=2)
        sys.stderr.write("\n")
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
