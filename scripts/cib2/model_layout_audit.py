# Copyright (C) 2018-2026 Intel Corporation
# SPDX-License-Identifier: Apache-2.0
"""CIB2 P1: inspect a local HF/Optimum config, never infer Pack eligibility from names.

Read-only; does not fetch checkpoints, open BIN, compile graphs, or create packs.
The compiled GPU MOECompressed + nine native slices gate remains mandatory.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path


class ModelLayoutError(ValueError):
    pass


MAX_CONFIG_BYTES = 1024 * 1024
MOE_TYPES = {"qwen3_5_moe_text", "qwen4_exp_text"}
KNOWN_TYPES = MOE_TYPES | {"qwen3_5_text", "gemma4_text"}


def _unique(pairs):
    result = {}
    for k, v in pairs:
        if k in result:
            raise ModelLayoutError(f"duplicate config key: {k}")
        result[k] = v
    return result


def _positive_int(value, where, minimum=1, maximum=16384):
    if type(value) is not int or not minimum <= value <= maximum:
        raise ModelLayoutError(f"{where} out of supported range")
    return value


def inspect_config(config: dict, model_id: str = "") -> dict:
    if type(config) is not dict or not isinstance(config.get("text_config"), dict):
        raise ModelLayoutError("expected HF/Optimum text_config object")
    text = config["text_config"]
    kind = text.get("model_type")
    if kind not in KNOWN_TYPES:
        raise ModelLayoutError(f"unsupported decoder type: {kind!r}")
    layers = _positive_int(text.get("num_hidden_layers"), "num_hidden_layers", maximum=1024)
    hidden = _positive_int(text.get("hidden_size"), "hidden_size", maximum=65536)
    attn = text.get("layer_types")
    if attn is not None:
        if type(attn) is not list or len(attn) != layers or any(
            a not in ("linear_attention", "full_attention", "sliding_attention") for a in attn
        ):
            raise ModelLayoutError("layer_types differ from decoder layer count")
        pattern = {"linear_attention": attn.count("linear_attention"),
                   "full_attention": attn.count("full_attention"),
                   "sliding_attention": attn.count("sliding_attention")}
    else:
        pattern = None
    if kind in MOE_TYPES or (kind == "gemma4_text" and text.get("enable_moe_block") is True):
        experts = _positive_int(text.get("num_experts"), "num_experts")
        topk_key = "top_k_experts" if kind == "gemma4_text" else "num_experts_per_tok"
        topk = _positive_int(text.get(topk_key), topk_key)
        if topk > experts:
            raise ModelLayoutError("router top-k exceeds expert count")
        moe_ffn = _positive_int(text.get("moe_intermediate_size"),
                                "moe_intermediate_size", maximum=131072)
        shared = "shared_expert_intermediate_size" in text or kind == "gemma4_text"
        status = "MOE_CANDIDATE_COMPILED_GATE_REQUIRED"
    else:
        if kind == "gemma4_text" and text.get("enable_moe_block") not in (False, None):
            raise ModelLayoutError("invalid gemma4 enable_moe_block")
        if text.get("num_experts", 0) not in (None, 0):
            raise ModelLayoutError("dense decoder declares routed experts")
        experts, topk, moe_ffn, shared = 0, 0, None, False
        status = "DENSE_NO_ROUTED_MOE"
    wrapper = config.get("model_type", "")
    if type(wrapper) is not str:
        raise ModelLayoutError("invalid wrapper type")
    allowed_wrappers = {
        "qwen3_5_moe": {"qwen3_5_moe_text"},
        "qwen3_5": {"qwen3_5_text"},
        "gemma4": {"gemma4_text"},
        "minicpmv4_7": {"qwen3_5_moe_text", "qwen3_5_text"},
        "qwen4_exp": {"qwen4_exp_text"},
    }
    if wrapper in allowed_wrappers and kind not in allowed_wrappers[wrapper]:
        raise ModelLayoutError("decoder type mismatches declared model wrapper")
    return {
        "schema": "cib2.model_layout_audit.v1",
        "model_id_claim": model_id,
        "wrapper_model_type": wrapper,
        "decoder_model_type": kind,
        "num_hidden_layers": layers,
        "hidden_size": hidden,
        "attention_layer_counts": pattern,
        "routed_experts_per_moe_layer": experts,
        "top_k": topk,
        "expert_intermediate_size": moe_ffn,
        "has_shared_expert": shared,
        "vision_encoder_layers": config.get("vision_config", {}).get("num_hidden_layers")
            if isinstance(config.get("vision_config"), dict) else None,
        "compiled_kind": "UNKNOWN",
        "nine_slice_compiled_eligibility": "NOT_RUN",
        "runtime_acceptance": "NO",
        "status": status,
    }


def inspect_file(path: Path, model_id: str = "") -> dict:
    if path.is_symlink() or not path.is_file() or path.stat().st_size > MAX_CONFIG_BYTES:
        raise ModelLayoutError("missing, oversized or symlinked config")
    try:
        config = json.loads(path.read_text("utf-8"), object_pairs_hook=_unique,
                            parse_constant=lambda x: (_ for _ in ()).throw(
                                ModelLayoutError("nonfinite config literal")))
    except (UnicodeError, json.JSONDecodeError) as e:
        raise ModelLayoutError("malformed config") from e
    return inspect_config(config, model_id)


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("config", type=Path)
    p.add_argument("--model-id", default="", help="display claim only, never classifier")
    a = p.parse_args(argv)
    try:
        print(json.dumps(inspect_file(a.config, a.model_id), indent=2, sort_keys=True))
    except ModelLayoutError as e:
        p.exit(2, f"CIB2 layout rejected: {e}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
