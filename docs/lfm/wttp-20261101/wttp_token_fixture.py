#!/usr/bin/env python3
"""WTTP research harness. Tokenizer-derived SYNTHETIC streams, never model output.

Reads a local Hugging Face tokenizer.json (or a tokenizer-contract inspector directory).
Does not download weights, run inference, execute tools or modify the tokenizer.
Optional: `pip install tokenizers` for exact decoding of modern tokenizers.

Usage:
  python wttp_token_fixture.py generate /path/to/tokenizer.json -o fixtures.json --family lfm2
  python wttp_token_fixture.py replay fixtures.json --allow-composite
"""
from __future__ import annotations

import argparse
import ast
from collections import deque
import hashlib
import json
from pathlib import Path
import re
from typing import Any

PROTOCOLS = {
    "lfm2": {"start": "<|tool_call_start|>", "end": "<|tool_call_end|>", "syntax": "lfm_python"},
    "lfm25": {"start": "<|tool_call_start|>", "end": "<|tool_call_end|>", "syntax": "lfm_python"},
    "lfm3": {"start": "<tool_call>", "end": "</tool_call>", "syntax": "lfm3_xml"},
}
# A preference only: it must never override unambiguous, fully validated evidence.
PRIOR = {"lfm2": "lfm2", "lfm25": "lfm25", "lfm3": "lfm3"}


def _base_vocab(data: dict) -> dict[int, str]:
    model = data.get("model", {})
    v = model.get("vocab", {})
    if isinstance(v, dict):
        return {i: s for s, i in v.items() if isinstance(i, int)}
    if isinstance(v, list):
        return {i: item[0] for i, item in enumerate(v) if isinstance(item, list) and item and isinstance(item[0], str)}
    raise ValueError("tokenizer.json model.vocab is unavailable")


def _byte_level_map():
    # GPT-2 byte-to-unicode mapping, as used by Hugging Face ByteLevel decoder.
    bs = list(range(ord("!"), ord("~") + 1)) + list(range(ord("¡"), ord("¬") + 1)) + list(range(ord("®"), ord("ÿ") + 1))
    cs = bs[:]
    n = 0
    for b in range(256):
        if b not in bs:
            bs.append(b)
            cs.append(256 + n)
            n += 1
    return {chr(c): b for b, c in zip(bs, cs)}

_BYTE_MAP = _byte_level_map()


class TokenizerInventory:
    def __init__(self, tokenizer_file: Path):
        self.file = tokenizer_file
        self.raw = tokenizer_file.read_bytes()
        self.sha256 = hashlib.sha256(self.raw).hexdigest()
        self.data = json.loads(self.raw)
        self.base = _base_vocab(self.data)
        self.added = {int(x["id"]): x for x in self.data.get("added_tokens", [])
                      if isinstance(x, dict) and isinstance(x.get("id"), int) and isinstance(x.get("content"), str)}
        self.by_id = {**self.base, **{idx: x["content"] for idx, x in self.added.items()}}
        self.decoder = self.data.get("decoder") or {}
        self.backend = None
        try:
            from tokenizers import Tokenizer
            self.backend = Tokenizer.from_file(str(tokenizer_file))
        except ImportError:
            pass
        except Exception as ex:
            raise ValueError(f"Invalid tokenizer.json for tokenizers library: {ex}") from ex
        self.backend_mode = "hf_tokenizers" if self.backend else "stdlib_ascii_verified_subset"

    def _piece(self, idx: int) -> str:
        if idx in self.added:
            return self.added[idx]["content"]
        s = self.base[idx]
        if self.decoder.get("type") == "ByteLevel":
            try:
                return bytes(_BYTE_MAP[c] for c in s).decode("utf-8")
            except (ValueError, UnicodeDecodeError, KeyError):
                return ""  # Incomplete byte sequences must use tokenizers backend.
        if self.decoder.get("type") == "Metaspace":
            return s.replace(self.decoder.get("replacement", "▁"), " ")
        if self.decoder.get("type") in (None, "WordPiece", "Fuse"):
            if s.startswith("##"):
                return s[2:]
            return s
        return ""  # Do not guess arbitrary decoder semantics.

    def decode(self, ids: list[int]) -> str:
        if self.backend:
            return self.backend.decode(ids, skip_special_tokens=False)
        if not all(self._piece(idx) for idx in ids):
            raise ValueError("Cannot decode this token sequence without `tokenizers`; install the dependency")
        return "".join(self._piece(idx) for idx in ids)

    def dedicated(self, marker: str) -> list[int]:
        ids = [i for i, t in self.by_id.items() if t == marker]
        return [i for i in sorted(ids) if self.decode([i]) == marker]

    def composed(self, text: str, *, forbid: set[int] | None = None, max_tokens: int = 80) -> list[int] | None:
        """Shortest path using *base vocab* pieces; validates full decode on completion.

        Not a reproduction of model sampling or standard tokenizer.encode().
        Represents physically possible token IDs whose decoded concatenation equals text.
        """
        forbid = forbid or set()
        vocab = sorted(((i, self._piece(i)) for i in self.base if i not in forbid),
                       key=lambda x: (-len(x[1]), x[0]))
        choices: dict[str, list[tuple[int, str]]] = {}
        for i, piece in vocab:
            if piece and piece in text:
                choices.setdefault(piece[0], []).append((i, piece))
        q = deque([(0, ())]); attempts = 0
        while q and attempts < 100000:
            offset, path = q.popleft()
            attempts += 1
            if offset == len(text):
                ids = list(path)
                try:
                    if self.decode(ids) == text:
                        return ids
                except ValueError:
                    pass
                continue
            if len(path) >= max_tokens:
                continue
            for idx, piece in choices.get(text[offset], []):
                nxt = offset + len(piece)
                if text.startswith(piece, offset):
                    q.append((nxt, path + (idx,)))
        return None

    def any_encoding(self, text: str) -> list[int] | None:
        if self.backend:
            try:
                ids = self.backend.encode(text, add_special_tokens=False).ids
                if self.decode(ids) == text:
                    return ids
            except Exception:
                pass
        return self.composed(text)


def family_hint(model: str | None) -> str | None:
    if not model:
        return None
    m = model.lower()
    if "lfm3" in m:
        return "lfm3"
    if "lfm2.5" in m or "lfm25" in m:
        return "lfm25"
    if "lfm2" in m:
        return "lfm2"
    return None


def _literal_ok(n: ast.AST, depth: int = 0) -> bool:
    if depth > 32:
        return False
    if isinstance(n, ast.Constant):
        return isinstance(n.value, (str, int, float, bool, type(None)))
    if isinstance(n, ast.Name):
        return n.id in ("true", "false", "null", "True", "False", "None")
    if isinstance(n, ast.UnaryOp) and isinstance(n.op, (ast.UAdd, ast.USub)):
        return isinstance(n.operand, ast.Constant) and type(n.operand.value) in (int, float)
    if isinstance(n, (ast.List, ast.Tuple)):
        return all(_literal_ok(x, depth + 1) for x in n.elts)
    if isinstance(n, ast.Dict):
        return all(isinstance(k, ast.Constant) and isinstance(k.value, str) and
                   _literal_ok(v, depth + 1) for k, v in zip(n.keys, n.values)) and len({k.value for k in n.keys}) == len(n.keys)
    return False


def python_call_shape(body: str, tool_names: set[str]) -> list[str] | None:
    """Read-only syntax check, NOT the production retainer or a literal serializer."""
    if len(body) > (1 << 20):
        return None
    try:
        root = ast.parse(body, mode="eval").body
    except (SyntaxError, ValueError, RecursionError):
        return None
    if not isinstance(root, ast.List) or not root.elts or len(root.elts) > 128:
        return None
    names = []
    for expr in root.elts:
        if not isinstance(expr, ast.Call) or not isinstance(expr.func, ast.Name) or expr.func.id not in tool_names:
            return None
        if expr.args or any(x.arg is None or not re.fullmatch(r"[a-zA-Z_][a-zA-Z_0-9]*", x.arg) or
                            not _literal_ok(x.value) for x in expr.keywords):
            return None
        keys = [x.arg for x in expr.keywords]
        if len(keys) != len(set(keys)):
            return None
        names.append(expr.func.id)
    return names


def xml_call_shape(body: str, tool_names: set[str]) -> list[str] | None:
    """Tiny LFM3 shape probe; intentionally NOT a general XML/function parser."""
    pattern = re.compile(r"\s*<function=([A-Za-z_][A-Za-z_0-9]*)>\s*((?:<parameter=[A-Za-z_][A-Za-z_0-9]*>[^<>]*</parameter>\s*)*)</function>\s*", re.S)
    pos, names = 0, []
    while pos < len(body):
        m = pattern.match(body, pos)
        if not m or m.group(1) not in tool_names:
            return None
        names.append(m.group(1))
        pos = m.end()
    return names or None


class WeightedTokenProbe:
    """Read-only streaming marker hypotheses; *not* a production executable parser.

    Both text and exact ID paths are active, independent of family hint.
    The family only breaks ties between identically spelled protocol markers.
    """
    def __init__(self, token_map: dict[str, dict[str, Any]], family: str | None, tool_names: set[str],
                 allow_composite: bool = False):
        self.token_map = token_map
        self.family = family
        self.tool_names = tool_names
        self.allow_composite = allow_composite
        self.events: list[dict] = []
        self.state = "CONTENT"
        self.plain = ""
        self.pending = ""
        self.pending_origins: list[tuple[int, int]] = []
        self.body = ""
        self.opening: dict | None = None
        self.all_starts = []
        for proto, cfg in token_map.items():
            self.all_starts.append((proto, cfg["start"], set(cfg.get("start_ids", []))))
        self._quote = ""
        self._escape = False
        self._end_pending = ""
        self._end_origins: list[tuple[int, int]] = []
        self._sequence_number = 0
        self._prefix_bucket = -1
        self.max_bytes = 1 << 20

    @staticmethod
    def _ids(origins: list[tuple[int, int]]) -> list[int]:
        out, last_seq = [], None
        for seq, tid in origins:
            if seq != last_seq:
                out.append(tid)
                last_seq = seq
        return out

    def _emit_content(self):
        if self.plain:
            self.events.append({"event": "CONTENT", "text": self.plain})
            self.plain = ""

    def _open(self, proto: str, path: str, ids: list[int], alternatives: list[str]):
        self._emit_content()
        self.state = "TOOL"
        self.body = ""
        self._quote = ""
        self._escape = False
        self._end_pending = ""
        self._end_origins = []
        self._prefix_bucket = -1
        self.opening = {"protocol": proto, "recognition": path, "marker_token_ids": ids,
                        "compatible_protocol_hypotheses": sorted(alternatives),
                        "family_preference": proto == (PRIOR.get(self.family) if self.family else None)}
        self.events.append({"event": "ARMED", "protocol": proto, "recognition": path,
                            "marker_token_ids": ids, "compatible_protocol_hypotheses": sorted(alternatives),
                            "family_preference": self.opening["family_preference"]})

    def _close(self, path: str, ids: list[int]):
        assert self.opening
        proto = self.opening["protocol"]
        names = (python_call_shape(self.body, self.tool_names) if PROTOCOLS[proto]["syntax"] == "lfm_python"
                 else xml_call_shape(self.body, self.tool_names))
        valid = names is not None
        self.events.append({"event": "TOOL_CANDIDATE", "protocol": proto,
                            "start_recognition": self.opening["recognition"],
                            "end_recognition": path,
                            "start_marker_token_ids": self.opening["marker_token_ids"],
                            "end_marker_token_ids": ids,
                            "compatible_protocol_hypotheses": self.opening["compatible_protocol_hypotheses"],
                            "family_preference": self.opening["family_preference"],
                            "syntax_valid": valid, "tools": names or [], "raw_body": self.body,
                            "retainer_required": True,
                            "publication_eligible": bool(valid and (self.allow_composite or
                              (self.opening["recognition"] == "DEDICATED_ID" and path == "DEDICATED_ID")))})
        self.opening = None
        self.state = "CONTENT"
        self.body = ""
        self._quote = ""
        self._escape = False
        self._end_pending = ""
        self._end_origins = []

    def _try_text_starts(self):
        while self.pending:
            matches = [(p, marker) for p, marker, _ in self.all_starts if self.pending == marker]
            if matches:
                # For identical marker spellings, the family hint is a PRIOR,
                # never an exclusion rule. Preserve the other hypotheses.
                matches.sort(key=lambda x: (x[0] != self.family, x[0]))
                proto, marker = matches[0]
                ids = self._ids(self.pending_origins[:len(marker)])
                hypotheses = [p for p, _ in matches]
                self.pending = self.pending[len(marker):]
                self.pending_origins = self.pending_origins[len(marker):]
                self._open(proto, "COMPOSITE_TEXT", ids, hypotheses)
                return
            possibilities = [(p, m) for p, m, _ in self.all_starts if m.startswith(self.pending)]
            if possibilities:
                fraction = max(len(self.pending) / len(m) for _, m in possibilities)
                bucket = max(0, int(fraction * 4))
                if len(self.pending) == 1 or bucket > self._prefix_bucket:
                    self.events.append({"event": "PREFIX_PROGRESS", "matched_chars": len(self.pending),
                                        "progress_fraction": round(fraction, 3),
                                        "protocol_hypotheses": sorted({p for p, _ in possibilities}),
                                        "marker_token_ids": self._ids(self.pending_origins)})
                    self._prefix_bucket = bucket
                return
            self.plain += self.pending[0]
            self.pending = self.pending[1:]
            self.pending_origins = self.pending_origins[1:]
            self._prefix_bucket = -1
        self._emit_content()

    def _consume_tool_char(self, ch: str, origin: tuple[int, int]):
        assert self.opening
        end = self.token_map[self.opening["protocol"]]["end"]
        if self._quote:
            self.body += ch
            if self._escape:
                self._escape = False
            elif ch == "\\":
                self._escape = True
            elif ch == self._quote:
                self._quote = ""
            return
        if ch in ("'", '"'):
            self.body += self._end_pending
            self._end_pending = ""
            self._end_origins = []
            self._quote = ch
            self.body += ch
            return
        self._end_pending += ch
        self._end_origins.append(origin)
        while self._end_pending and not end.startswith(self._end_pending):
            self.body += self._end_pending[0]
            self._end_pending = self._end_pending[1:]
            self._end_origins = self._end_origins[1:]
        if self._end_pending == end:
            origins = self._end_origins
            self._end_pending = ""
            self._end_origins = []
            self._close("COMPOSITE_TEXT", self._ids(origins))
        if len(self.body) + len(self._end_pending) > self.max_bytes:
            self.events.append({"event": "REJECT", "reason": "candidate_too_large"})
            self.state = "CONTENT"
            self.opening = None
            self.body = ""
            self._end_pending = ""
            self._end_origins = []

    def _consume_text(self, text: str, token_id: int, token_seq: int):
        for ch in text:
            if self.state == "TOOL":
                self._consume_tool_char(ch, (token_seq, token_id))
            else:
                self.pending += ch
                self.pending_origins.append((token_seq, token_id))
                self._try_text_starts()

    def feed(self, token_id: int, delta_text: str):
        # Correctly aligned text deltas supplied by tokenizer-backed test harness.
        # A live adapter must handle non-prefix-stable detokenizers separately.
        self._sequence_number += 1
        if self.state == "CONTENT":
            direct = [(p, marker) for p, marker, ids in self.all_starts if token_id in ids]
            if direct:
                direct.sort(key=lambda x: (x[0] != self.family, x[0]))
                if self.pending:
                    self.plain += self.pending
                    self.pending = ""
                    self.pending_origins = []
                self._open(direct[0][0], "DEDICATED_ID", [token_id], [p for p, _ in direct])
                return
        else:
            assert self.opening
            end_ids = set(self.token_map[self.opening["protocol"]].get("end_ids", []))
            if token_id in end_ids and not self._quote and not self._end_pending:
                self._close("DEDICATED_ID", [token_id])
                return
        self._consume_text(delta_text, token_id, self._sequence_number)

    def finish(self):
        if self.state == "TOOL":
            self.events.append({"event": "INCOMPLETE", "protocol": self.opening["protocol"],
                                "raw_body": self.body + self._end_pending})
        else:
            self.plain += self.pending
            self.pending = ""
            self.pending_origins = []
            self._emit_content()
        return self.events


def _compose_fixture(tok: TokenizerInventory, label: str, start_ids: list[int], end_ids: list[int], body_ids: list[int], family: str):
    return {"name": label, "family_hint": family, "synthetic": True,
            "token_ids": start_ids + body_ids + end_ids,
            "segments": {"start": start_ids, "body": body_ids, "end": end_ids}}


def generate(tok: TokenizerInventory, hint: str | None, tool_name: str, args: str) -> dict:
    scenarios = []
    skips = []
    profiles = {}
    for proto, config in PROTOCOLS.items():
        start, end = config["start"], config["end"]
        sid, eid = tok.dedicated(start), tok.dedicated(end)
        start_comp = tok.composed(start, forbid=set(sid))
        end_comp = tok.composed(end, forbid=set(eid))
        profiles[proto] = {"start": start, "end": end, "start_ids": sid, "end_ids": eid,
                           "composite_start": start_comp, "composite_end": end_comp}
        if config["syntax"] == "lfm_python":
            body = f"[{tool_name}({args})]"
        else:
            body = f"<function={tool_name}><parameter=sample>hello</parameter></function>"
        body_ids = tok.any_encoding(body)
        if body_ids is None:
            skips.append({"protocol": proto, "reason": "cannot represent synthetic body with known decoder", "body": body})
            continue
        options_start = [("dedicated", [sid[0]])] if sid else []
        options_end = [("dedicated", [eid[0]])] if eid else []
        if start_comp and len(start_comp) > 1:
            options_start.append(("composite", start_comp))
        if end_comp and len(end_comp) > 1:
            options_end.append(("composite", end_comp))
        for sn, ss in options_start:
            for en, ee in options_end:
                ids = ss + body_ids + ee
                if tok.decode(ids) != start + body + end:
                    skips.append({"protocol": proto, "reason": "whole-sequence decode differs", "path": sn + "/" + en})
                    continue
                scenarios.append(_compose_fixture(tok, f"{proto}_{sn}_{en}", ss, ee, body_ids, hint or proto))
    return {"schema_version": "wttp-synthetic-fixtures/v1", "synthetic": True, "model_output": False,
            "source_tokenizer": str(tok.file), "tokenizer_sha256": tok.sha256,
            "decoder": tok.backend_mode, "family_hint": hint,
            "profiles": profiles, "available_tools": [tool_name], "scenarios": scenarios, "skipped": skips,
            "warning": "No model was run. Tokenizer-derived sequences are not learned generation probabilities or live traces."}


def replay(fixture: dict, allow_composite: bool, tokenizer_override: str | None = None) -> dict:
    result = []
    tok = TokenizerInventory(Path(tokenizer_override or fixture["source_tokenizer"]))
    if tok.sha256 != fixture["tokenizer_sha256"]:
        raise ValueError("Tokenizer SHA mismatch: synthetic fixture provenance is invalid")
    profiles = {k: v for k, v in fixture["profiles"].items() if v.get("start_ids") or v.get("composite_start")}
    for c in fixture["scenarios"]:
        # Fixture generation records exact synthetic token IDs; decoded text is replayed
        # from each segment. Normal byte-level streaming requires a tokenizer backend.
        # Reopening the original file refuses non-local source. No arbitrary file download.
        engine = WeightedTokenProbe(profiles, c["family_hint"], set(fixture["available_tools"]),
                                    allow_composite=allow_composite)
        seen = []
        for tid in c["token_ids"]:
            now = seen + [tid]
            before = tok.decode(seen) if seen else ""
            after = tok.decode(now)
            if not after.startswith(before):
                raise ValueError("Non-prefix-stable tokenizer decode. Use a genuine incremental decoder, not this harness")
            engine.feed(tid, after[len(before):])
            seen = now
        result.append({"scenario": c["name"], "events": engine.finish()})
    return {"schema_version": "wttp-probe-results/v1", "synthetic": True, "runs": result}


def resolve_tokenizer(spec: str, revision: str | None = None) -> Path:
    path = Path(spec)
    if path.is_dir():
        return path / "tokenizer.json"
    if path.is_file():
        return path
    if path.is_absolute() or spec.startswith(("./", ".\\", "../", "..\\")):
        raise FileNotFoundError(spec)
    try:
        from huggingface_hub import hf_hub_download
    except ImportError as exc:
        raise RuntimeError("Hugging Face IDs require: pip install huggingface_hub") from exc
    return Path(hf_hub_download(repo_id=spec, filename="tokenizer.json", revision=revision))


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="command", required=True)
    g = sub.add_parser("generate", help="Generate tokenizer-derived, not model-derived, synthetic fixtures")
    g.add_argument("tokenizer", help="local tokenizer.json or model directory")
    g.add_argument("-o", "--output", default="wttp_fixtures.json")
    g.add_argument("--family", choices=list(PROTOCOLS), help="hint only; never force a protocol")
    g.add_argument("--revision", help="Hugging Face revision; pin to a SHA for reproducibility")
    g.add_argument("--tool", default="get_weather")
    g.add_argument("--args", default='city="Paris"')
    r = sub.add_parser("replay", help="Replay synthetic fixtures; no tool execution")
    r.add_argument("fixtures")
    r.add_argument("-o", "--output", default="wttp_replay.json")
    r.add_argument("--allow-composite", action="store_true", help="Mark valid composite cases eligible for retainer; never executes")
    r.add_argument("--tokenizer", help="override source tokenizer path, SHA must match")
    a = p.parse_args(argv)
    if a.command == "generate":
        source = resolve_tokenizer(a.tokenizer, a.revision)
        obj = generate(TokenizerInventory(source), a.family, a.tool, a.args)
        out = a.output
        print(f"Generated {len(obj['scenarios'])} synthetic fixtures, {len(obj['skipped'])} skips")
    else:
        obj = replay(json.loads(Path(a.fixtures).read_text(encoding="utf-8")), a.allow_composite, a.tokenizer)
        out = a.output
        count = sum(sum(x["event"] == "TOOL_CANDIDATE" for x in c["events"]) for c in obj["runs"])
        print(f"Replayed {len(obj['runs'])} scenarios; {count} candidates; NO execution")
    Path(out).write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
