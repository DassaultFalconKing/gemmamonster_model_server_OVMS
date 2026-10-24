"""Streaming moe_otd_trace v1 parser (E/C field indices).

E,<call>,<t_ns>,<layer>,<expert>,<slot>,<hit>,<evicted>,<bytes>,<reads>,<read_ns>,<transform_ns>,<copy_ns>
C,<call>,<t_ns>,<layer>,<kind>,<routed>,<status>,<unique_experts...>
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterator, TextIO


def _open_text(path: Path) -> TextIO:
    return path.open("r", encoding="utf-8", errors="replace", newline="")


def stream_e_records(path: Path) -> Iterator[list[str]]:
    """Yield E-record parts lists without loading the whole file."""
    if not path.is_file():
        return
    with _open_text(path) as fh:
        for line in fh:
            if not line or line[0] == "#" or line[0] != "E":
                continue
            parts = line.rstrip("\n\r").split(",")
            if len(parts) >= 13:
                yield parts


def stream_c_records(path: Path) -> Iterator[list[str]]:
    if not path.is_file():
        return
    with _open_text(path) as fh:
        for line in fh:
            if not line or line[0] != "C":
                continue
            parts = line.rstrip("\n\r").split(",")
            if len(parts) >= 7:
                yield parts


def aggregate_delta(before: dict, after: dict) -> dict:
    hits = int(after.get("hits", 0)) - int(before.get("hits", 0))
    misses = int(after.get("misses", 0)) - int(before.get("misses", 0))
    touches = hits + misses
    return {
        "hits": hits,
        "misses": misses,
        "touches": touches,
        "hit_rate": round(hits / touches, 4) if touches else None,
        "miss_bytes": int(after.get("miss_bytes", 0)) - int(before.get("miss_bytes", 0)),
        "miss_read_s": round(float(after.get("miss_read_s", 0)) - float(before.get("miss_read_s", 0)), 4),
        "miss_transform_s": round(
            float(after.get("miss_transform_s", 0)) - float(before.get("miss_transform_s", 0)), 4
        ),
        "miss_copy_s": round(float(after.get("miss_copy_s", 0)) - float(before.get("miss_copy_s", 0)), 4),
    }


def parse_moe_otd_trace(
    path: Path,
    *,
    skip_e: int = 0,
    take_e: int | None = None,
) -> dict:
    """Aggregate expert hit/miss from moe_otd_trace v1 (streaming).

    skip_e/take_e select an E-record window by cumulative E count (0-based skip).
    """
    if not path.is_file():
        return {"present": False, "path": str(path), "error": "missing"}

    hits = misses = 0
    bytes_miss = 0
    read_ns_miss = transform_ns_miss = copy_ns_miss = 0
    e_lines = 0
    c_ok = c_overflow = 0
    e_seen = 0

    try:
        with _open_text(path) as fh:
            for line in fh:
                if not line or line[0] == "#":
                    continue
                parts = line.rstrip("\n\r").split(",")
                if not parts:
                    continue
                kind = parts[0]
                if kind == "C" and len(parts) >= 7:
                    status = parts[6]
                    if status == "ok":
                        c_ok += 1
                    elif status == "overflow":
                        c_overflow += 1
                elif kind == "E" and len(parts) >= 13:
                    if e_seen < skip_e:
                        e_seen += 1
                        continue
                    if take_e is not None and e_lines >= take_e:
                        # Still count remaining C lines? Window is E-only; stop after take_e E's
                        # but continue scanning for C in prefix-only mode is unused.
                        # For full-file after skip, take_e=None. When take_e set, stop early.
                        break
                    e_seen += 1
                    e_lines += 1
                    hit = parts[6] in ("1", "true", "True")
                    if hit:
                        hits += 1
                    else:
                        misses += 1
                        try:
                            bytes_miss += int(parts[8])
                            read_ns_miss += int(parts[10])
                            transform_ns_miss += int(parts[11])
                            copy_ns_miss += int(parts[12])
                        except ValueError:
                            pass
    except OSError as exc:
        return {"present": False, "path": str(path), "error": str(exc)}

    total = hits + misses
    return {
        "present": True,
        "path": str(path),
        "e_records": e_lines,
        "hits": hits,
        "misses": misses,
        "hit_rate": round(hits / total, 4) if total else None,
        "miss_rate": round(misses / total, 4) if total else None,
        "miss_bytes": bytes_miss,
        "miss_read_s": round(read_ns_miss / 1e9, 4) if read_ns_miss else 0.0,
        "miss_transform_s": round(transform_ns_miss / 1e9, 4) if transform_ns_miss else 0.0,
        "miss_copy_s": round(copy_ns_miss / 1e9, 4) if copy_ns_miss else 0.0,
        "calls_ok": c_ok,
        "calls_overflow": c_overflow,
        "bytes": path.stat().st_size,
        "skip_e": skip_e,
        "take_e": take_e,
    }


@dataclass
class Percentiles:
    mean: float
    p50: float
    p95: float
    p99: float
    n: int


def _percentiles_us(values_ns: list[int]) -> Percentiles | None:
    if not values_ns:
        return None
    xs = sorted(values_ns)
    n = len(xs)

    def at(p: float) -> float:
        if n == 1:
            return xs[0] / 1e3
        idx = min(n - 1, max(0, int(round((p / 100.0) * (n - 1)))))
        return xs[idx] / 1e3

    return Percentiles(
        mean=sum(xs) / n / 1e3,
        p50=at(50),
        p95=at(95),
        p99=at(99),
        n=n,
    )


@dataclass
class LayerStats:
    touches: int = 0
    hits: int = 0
    misses: int = 0
    evictions: int = 0
    bytes_loaded: int = 0
    read_ns: int = 0
    transform_ns: int = 0
    copy_ns: int = 0
    reload_counts: dict[int, int] = field(default_factory=lambda: defaultdict(int))
    eviction_reloads: int = 0  # miss where evicted!=-1 and expert reloaded later tracked separately


def reanalyze_window(
    path: Path,
    *,
    skip_e: int,
    take_e: int,
    eviction_reload_window: int = 64,
) -> dict:
    """Full offline window analysis: transfer stats, per-layer, eviction reload hints."""
    if not path.is_file():
        return {"validation_status": "INCOMPLETE", "error": "missing_trace", "path": str(path)}

    copy_ns_list: list[int] = []
    read_ns_list: list[int] = []
    bytes_list: list[int] = []
    layers: dict[int, LayerStats] = defaultdict(LayerStats)
    # recent miss history per layer for eviction-reload detection: list of (expert,)
    recent_evicted: dict[int, list[int]] = defaultdict(list)

    hits = misses = 0
    e_count = 0
    e_seen = 0
    total_read = total_xform = total_copy = 0
    total_bytes = 0
    first_t_ns = last_t_ns = None

    with _open_text(path) as fh:
        for line in fh:
            if not line or line[0] != "E":
                continue
            parts = line.rstrip("\n\r").split(",")
            if len(parts) < 13:
                continue
            if e_seen < skip_e:
                e_seen += 1
                continue
            if e_count >= take_e:
                break
            e_seen += 1
            e_count += 1

            try:
                t_ns = int(parts[2])
                layer = int(parts[3])
                expert = int(parts[4])
                hit = parts[6] in ("1", "true", "True")
                evicted = int(parts[7])
                nbytes = int(parts[8])
                read_ns = int(parts[10])
                xform_ns = int(parts[11])
                copy_ns = int(parts[12])
            except ValueError:
                continue

            if first_t_ns is None:
                first_t_ns = t_ns
            last_t_ns = t_ns

            ls = layers[layer]
            ls.touches += 1
            if hit:
                hits += 1
                ls.hits += 1
            else:
                misses += 1
                ls.misses += 1
                ls.bytes_loaded += nbytes
                ls.read_ns += read_ns
                ls.transform_ns += xform_ns
                ls.copy_ns += copy_ns
                ls.reload_counts[expert] += 1
                copy_ns_list.append(copy_ns)
                read_ns_list.append(read_ns)
                bytes_list.append(nbytes)
                total_read += read_ns
                total_xform += xform_ns
                total_copy += copy_ns
                total_bytes += nbytes
                hist = recent_evicted[layer]
                if expert in hist:
                    ls.eviction_reloads += 1
                if evicted >= 0:
                    ls.evictions += 1
                    hist.append(evicted)
                    if len(hist) > eviction_reload_window:
                        del hist[0 : len(hist) - eviction_reload_window]

    touches = hits + misses
    if e_count != take_e:
        status = "INCOMPLETE"
    else:
        status = "OK"

    copy_pct = _percentiles_us(copy_ns_list)
    read_pct = _percentiles_us(read_ns_list)
    miss_n = max(misses, 1)
    copy_bytes_per_miss = total_bytes / miss_n
    logical_read_mibs = (total_bytes / (1024 * 1024)) / (total_read / 1e9) if total_read else None
    effective_copy_mibs = (total_bytes / (1024 * 1024)) / (total_copy / 1e9) if total_copy else None

    layer_rows = []
    for layer_id, ls in sorted(layers.items(), key=lambda kv: kv[1].copy_ns + kv[1].read_ns, reverse=True):
        top20 = sorted(ls.reload_counts.items(), key=lambda kv: kv[1], reverse=True)[:20]
        lt = ls.touches
        layer_rows.append(
            {
                "layer": layer_id,
                "touches": ls.touches,
                "hits": ls.hits,
                "misses": ls.misses,
                "hit_rate": round(ls.hits / lt, 4) if lt else None,
                "evictions": ls.evictions,
                "eviction_reloads": ls.eviction_reloads,
                "bytes_loaded": ls.bytes_loaded,
                "read_s": round(ls.read_ns / 1e9, 4),
                "transform_s": round(ls.transform_ns / 1e9, 4),
                "copy_s": round(ls.copy_ns / 1e9, 4),
                "top20_reloaded_experts": [{"expert": e, "misses": c} for e, c in top20],
            }
        )

    return {
        "validation_status": status,
        "window": {
            "skip_e": skip_e,
            "take_e": take_e,
            "e_records_parsed": e_count,
            "first_t_ns": first_t_ns,
            "last_t_ns": last_t_ns,
            "wall_span_s": round((last_t_ns - first_t_ns) / 1e9, 4) if first_t_ns is not None and last_t_ns is not None else None,
        },
        "cache": {
            "hits": hits,
            "misses": misses,
            "touches": touches,
            "hit_rate": round(hits / touches, 4) if touches else None,
        },
        "memory_transfer": {
            "miss_bytes": total_bytes,
            "miss_read_s": round(total_read / 1e9, 4),
            "miss_transform_s": round(total_xform / 1e9, 4),
            "miss_copy_s": round(total_copy / 1e9, 4),
            "miss_read_transform_copy_s": round((total_read + total_xform + total_copy) / 1e9, 4),
            "copy_us_per_miss": None
            if copy_pct is None
            else {
                "mean": round(copy_pct.mean, 3),
                "p50": round(copy_pct.p50, 3),
                "p95": round(copy_pct.p95, 3),
                "p99": round(copy_pct.p99, 3),
                "n": copy_pct.n,
            },
            "read_us_per_miss": None
            if read_pct is None
            else {
                "mean": round(read_pct.mean, 3),
                "p50": round(read_pct.p50, 3),
                "p95": round(read_pct.p95, 3),
                "p99": round(read_pct.p99, 3),
                "n": read_pct.n,
            },
            "copy_bytes_per_miss": round(copy_bytes_per_miss, 1),
            "read_bytes_per_miss": round(copy_bytes_per_miss, 1),
            "logical_read_MiB_s": round(logical_read_mibs, 2) if logical_read_mibs is not None else None,
            "effective_copy_MiB_s": round(effective_copy_mibs, 2) if effective_copy_mibs is not None else None,
            "notes": [
                "copy_ns is wall time of blocking copy_from(..., true); may include GPU queue wait, not pure DMA",
                "logical_read_MiB_s uses miss_bytes / miss_read_s — not physical NVMe bandwidth",
                "effective_copy_MiB_s uses miss_bytes / miss_copy_s — not physical GPU bandwidth",
            ],
        },
        "layers_by_transfer_cost": layer_rows,
        "eviction_reload_window": eviction_reload_window,
        "total_eviction_reloads": sum(ls.eviction_reloads for ls in layers.values()),
    }
