# Copyright (C) 2018-2026 Intel Corporation
# SPDX-License-Identifier: Apache-2.0

"""Bounded static component identity collector/validator for CIB2-00.

This tool only reads file bytes. It never imports OpenVINO, executes a target binary,
starts OVMS, inspects loaded modules, reads environment/credential stores, or changes
runtime state. It records four independent provenance categories:

* file bytes verified -- SHA256 computed from the exact resolved physical file;
* built-from-source association -- UNVERIFIED without an independent exact receipt;
* loaded DLL evidence -- NOT_RUN because no process is started;
* runtime acceptance -- NO; ``accepted`` always remains false.

A caller-supplied SHA256 is only an expected digest for comparison. It never becomes the
identity of a file, and a filename is never treated as provenance. Model-weight ``.bin``
inputs are refused.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

SCHEMA_VERSION = "cib2.component-manifest.v1"
MANIFEST_KIND = "cib2_component_manifest"
FROZEN_SOURCE_REVISION = "eb76a74f7aa39573d452d95443e189b1f5f4d9e8"

FILE_BYTES_VERIFIED = "VERIFIED"
SOURCE_BUILD_UNVERIFIED = "UNVERIFIED"
SOURCE_BUILD_VERIFIED = "VERIFIED"
LOADED_NOT_RUN = "NOT_RUN"
LOADED_VERIFIED = "VERIFIED"
RUNTIME_ACCEPTANCE_NO = "NO"

PROVENANCE_KEYS = (
    "file_bytes",
    "source_build_association",
    "loaded_dll_evidence",
    "runtime_acceptance",
)
ROLES = ("executable", "dll", "config")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
NAME_RE = re.compile(r"^[A-Za-z0-9._-]+$")
WEIGHT_SUFFIXES = {".bin"}


class ComponentError(ValueError):
    """A component cannot be collected under the static-only policy."""


class ManifestError(ValueError):
    """A manifest is missing required identity or makes an unsupported provenance claim."""


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _validate_sha256(value: str, where: str) -> str:
    if not isinstance(value, str) or not SHA256_RE.fullmatch(value):
        raise ManifestError(f"{where}: expected 64 lowercase hexadecimal characters")
    return value


def _role_for(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix == ".exe":
        return "executable"
    if suffix == ".dll":
        return "dll"
    return "config"


def _check_name(name: str) -> str:
    if not isinstance(name, str) or not name or not NAME_RE.fullmatch(name):
        raise ComponentError(
            "component name must be non-empty and match [A-Za-z0-9._-]+"
        )
    return name


def parse_component_spec(value: str) -> Tuple[str, str]:
    """Parse one ``NAME=PATH`` CLI/library component specification."""
    if "=" not in value:
        raise ComponentError(f"--component must be NAME=PATH, got {value!r}")
    name, path = value.split("=", 1)
    name = name.strip()
    if not path.strip():
        raise ComponentError(f"--component {name or '<empty>'} has an empty path")
    return _check_name(name), path


def collect_component(name: str, path: str,
                      expected_sha256: Optional[str] = None) -> dict:
    """Collect one static file identity without executing or loading it."""
    name = _check_name(name)
    if not isinstance(path, str) or not path:
        raise ComponentError(f"component {name}: empty path")
    requested = Path(path)
    if requested.suffix.lower() in WEIGHT_SUFFIXES:
        raise ComponentError(
            f"component {name}: refusing model-weight BIN input {requested.name!r}"
        )
    try:
        resolved = requested.resolve(strict=True)
    except (OSError, RuntimeError) as exc:
        raise ComponentError(f"component {name}: cannot resolve {path!r}: {exc}") from exc
    if not resolved.is_file():
        raise ComponentError(f"component {name}: {str(resolved)!r} is not a regular file")
    if resolved.suffix.lower() in WEIGHT_SUFFIXES:
        raise ComponentError(
            f"component {name}: refusing model-weight BIN input {resolved.name!r}"
        )
    if expected_sha256 is not None:
        _validate_sha256(expected_sha256, f"component {name} expected digest")
    size_bytes = resolved.stat().st_size
    digest = _sha256_file(resolved)
    if expected_sha256 is not None and digest != expected_sha256:
        raise ComponentError(
            f"component {name}: file bytes do not match the supplied expected digest "
            f"(computed {digest}, expected {expected_sha256}); caller digest is not identity"
        )
    return {
        "name": name,
        "role": _role_for(resolved),
        "requested_path": path,
        "resolved_path": str(resolved),
        "file_name": resolved.name,
        "size_bytes": size_bytes,
        "sha256": digest,
        "digest_verification": {
            "computed_from_file_bytes": True,
            "expected_sha256": expected_sha256,
            "match": None if expected_sha256 is None else True,
            "caller_supplied_sha_used_as_identity": False,
        },
        "provenance": {
            "file_bytes": FILE_BYTES_VERIFIED,
            "source_build_association": SOURCE_BUILD_UNVERIFIED,
            "loaded_dll_evidence": LOADED_NOT_RUN,
            "runtime_acceptance": RUNTIME_ACCEPTANCE_NO,
        },
    }


def _component_specs(components: Iterable[object]) -> List[Tuple[str, str]]:
    specs: List[Tuple[str, str]] = []
    for item in components:
        if isinstance(item, str):
            specs.append(parse_component_spec(item))
        elif isinstance(item, (tuple, list)) and len(item) == 2:
            specs.append((_check_name(str(item[0])), str(item[1])))
        else:
            raise ComponentError("components must be NAME=PATH strings or (name, path) pairs")
    return specs


def build_manifest(components: Iterable[object],
                   source_revision: str = FROZEN_SOURCE_REVISION,
                   captured_at: Optional[str] = None,
                   expected_digests: Optional[Mapping[str, str]] = None) -> dict:
    """Collect a new manifest. The result is never accepted and never runtime-verified."""
    specs = _component_specs(components)
    if not specs:
        raise ComponentError("at least one --component NAME=PATH is required")
    if not isinstance(source_revision, str) or not source_revision.strip():
        raise ComponentError("source revision must be a non-empty string")
    expected = dict(expected_digests or {})
    collected: List[dict] = []
    seen_names: Dict[str, str] = {}
    seen_paths: Dict[str, str] = {}
    for name, path in specs:
        if name.casefold() in seen_names:
            raise ComponentError(f"duplicate component name {name!r}")
        component = collect_component(name, path, expected.get(name))
        resolved_key = str(Path(component["resolved_path"])).casefold()
        if resolved_key in seen_paths:
            raise ComponentError(
                f"duplicate component file identity: {name!r} and {seen_paths[resolved_key]!r} "
                "both resolve to the same physical file"
            )
        seen_names[name.casefold()] = name
        seen_paths[resolved_key] = name
        collected.append(component)
    collected.sort(key=lambda c: c["name"].casefold())
    roles: Dict[str, int] = {}
    for component in collected:
        roles[component["role"]] = roles.get(component["role"], 0) + 1
    manifest = {
        "schema": SCHEMA_VERSION,
        "kind": MANIFEST_KIND,
        "accepted": False,
        "generated_at_utc": captured_at or _utc_now(),
        "source_revision": source_revision,
        "source_revision_reference_only": True,
        "provenance": {
            "file_bytes": {
                "status": FILE_BYTES_VERIFIED,
                "method": "SHA256 over the exact resolved physical file bytes",
                "evidence": "components[*].sha256",
            },
            "source_build_association": {
                "status": SOURCE_BUILD_UNVERIFIED,
                "requested_revision": source_revision,
                "reference_only": True,
                "evidence": None,
                "note": "a supplied revision is a reference, not proof that these bytes were built from it",
            },
            "loaded_dll_evidence": {
                "status": LOADED_NOT_RUN,
                "evidence": None,
                "note": "no OVMS process was started and no loaded-module list was captured",
            },
            "runtime_acceptance": {
                "status": RUNTIME_ACCEPTANCE_NO,
                "accepted": False,
                "evidence": None,
                "note": "static file identity only; not a runtime or benchmark acceptance",
            },
        },
        "components": collected,
        "summary": {
            "component_count": len(collected),
            "total_bytes": sum(c["size_bytes"] for c in collected),
            "roles": dict(sorted(roles.items())),
        },
        "notes": [
            "caller-supplied SHA256 and filenames are not used as identity",
            "old release/tag hashes are not identities for newly observed binaries",
            "runtime acceptance remains NO",
        ],
    }
    validate_manifest(manifest)
    return manifest


def _truthy_evidence(value) -> bool:
    if value is None:
        return False
    if isinstance(value, (str, list, tuple, dict)):
        return len(value) > 0
    return bool(value)


def validate_manifest(manifest: dict, verify_files: bool = False,
                      require_loaded_evidence: bool = False,
                      require_source_build_evidence: bool = False) -> dict:
    """Strictly validate a manifest without trusting caller-supplied hashes or names.

    ``verify_files=True`` re-hashes the resolved files and rejects any size/digest change.
    ``require_loaded_evidence`` / ``require_source_build_evidence`` turn absent independent
    evidence into a hard refusal. Even when all static checks pass, ``accepted`` must be false.
    """
    if not isinstance(manifest, dict):
        raise ManifestError("manifest must be a JSON object")
    if manifest.get("schema") != SCHEMA_VERSION:
        raise ManifestError(
            f"unsupported schema version {manifest.get('schema')!r}; expected {SCHEMA_VERSION!r}"
        )
    if manifest.get("kind") != MANIFEST_KIND:
        raise ManifestError(f"manifest kind must be {MANIFEST_KIND!r}")
    if manifest.get("accepted") is not False:
        raise ManifestError("accepted must remain false; this tool cannot grant acceptance")
    if not isinstance(manifest.get("generated_at_utc"), str) or not manifest["generated_at_utc"]:
        raise ManifestError("generated_at_utc must be a non-empty string")
    if not isinstance(manifest.get("source_revision"), str) or not manifest["source_revision"]:
        raise ManifestError("source_revision must be a non-empty string")
    if manifest.get("source_revision_reference_only") is not True:
        raise ManifestError("source_revision must be marked reference_only=true")

    provenance = manifest.get("provenance")
    if not isinstance(provenance, dict):
        raise ManifestError("provenance must be an object")
    missing = [key for key in PROVENANCE_KEYS if key not in provenance]
    if missing:
        raise ManifestError(f"provenance is missing categories: {', '.join(missing)}")

    file_bytes = provenance["file_bytes"]
    if not isinstance(file_bytes, dict) or file_bytes.get("status") != FILE_BYTES_VERIFIED:
        raise ManifestError("file_bytes provenance must be VERIFIED")
    for key in ("method", "evidence"):
        if not isinstance(file_bytes.get(key), str) or not file_bytes[key]:
            raise ManifestError(f"file_bytes provenance is missing {key}")

    source_build = provenance["source_build_association"]
    if not isinstance(source_build, dict):
        raise ManifestError("source_build_association must be an object")
    source_status = source_build.get("status")
    if source_status not in (SOURCE_BUILD_UNVERIFIED, SOURCE_BUILD_VERIFIED):
        raise ManifestError(f"unsupported source_build_association status {source_status!r}")
    if source_status == SOURCE_BUILD_VERIFIED:
        raise ManifestError(
            "source_build_association claims VERIFIED without independent evidence/receipt verification; "
            "this static collector cannot attest source builds, even from a nonempty caller assertion"
        )
    if require_source_build_evidence and source_status != SOURCE_BUILD_VERIFIED:
        raise ManifestError("strict refusal: source-build association evidence is absent")

    loaded = provenance["loaded_dll_evidence"]
    if not isinstance(loaded, dict):
        raise ManifestError("loaded_dll_evidence must be an object")
    loaded_status = loaded.get("status")
    if loaded_status not in (LOADED_NOT_RUN, LOADED_VERIFIED):
        raise ManifestError(f"unsupported loaded_dll_evidence status {loaded_status!r}")
    if loaded_status == LOADED_VERIFIED:
        raise ManifestError("loaded_dll_evidence claims VERIFIED without a module-list evidence verifier; "
                            "this static collector never observes a target process")
    if require_loaded_evidence and loaded_status != LOADED_VERIFIED:
        raise ManifestError("strict refusal: loaded DLL/module evidence is absent")

    runtime = provenance["runtime_acceptance"]
    if not isinstance(runtime, dict):
        raise ManifestError("runtime_acceptance must be an object")
    if runtime.get("status") != RUNTIME_ACCEPTANCE_NO or runtime.get("accepted") is not False:
        raise ManifestError("runtime_acceptance must remain NO with accepted=false")

    components = manifest.get("components")
    if not isinstance(components, list) or not components:
        raise ManifestError("components must be a non-empty list")
    names: Dict[str, str] = {}
    paths: Dict[str, str] = {}
    identity_fields = ("name", "role", "resolved_path", "size_bytes", "sha256")
    for index, component in enumerate(components):
        where = f"components[{index}]"
        if not isinstance(component, dict):
            raise ManifestError(f"{where}: component identity must be an object")
        absent = [field for field in identity_fields if field not in component]
        if absent:
            raise ManifestError(f"{where}: incomplete identity tuple, missing {', '.join(absent)}")
        name = component["name"]
        if not isinstance(name, str) or not name:
            raise ManifestError(f"{where}: empty component name")
        key = name.casefold()
        if key in names:
            raise ManifestError(f"{where}: duplicate component name {name!r}")
        names[key] = name
        resolved_path = component["resolved_path"]
        if not isinstance(resolved_path, str) or not resolved_path:
            raise ManifestError(f"{where}: empty resolved_path")
        path_key = str(Path(resolved_path)).casefold()
        if path_key in paths:
            raise ManifestError(
                f"{where}: duplicate physical file identity with component {paths[path_key]!r}"
            )
        paths[path_key] = name
        if component["role"] not in ROLES:
            raise ManifestError(f"{where}: unsupported role {component['role']!r}")
        size_bytes = component["size_bytes"]
        if isinstance(size_bytes, bool) or not isinstance(size_bytes, int) or size_bytes < 0:
            raise ManifestError(f"{where}: size_bytes must be a non-negative integer")
        digest = _validate_sha256(component["sha256"], f"{where}.sha256")
        if Path(resolved_path).suffix.lower() in WEIGHT_SUFFIXES:
            raise ManifestError(f"{where}: model-weight BIN inputs are not allowed")

        comp_provenance = component.get("provenance")
        if not isinstance(comp_provenance, dict):
            raise ManifestError(f"{where}: provenance must be an object")
        expected_provenance = {
            "file_bytes": FILE_BYTES_VERIFIED,
            "source_build_association": source_status,
            "loaded_dll_evidence": loaded_status,
            "runtime_acceptance": RUNTIME_ACCEPTANCE_NO,
        }
        for key_name, expected in expected_provenance.items():
            if comp_provenance.get(key_name) != expected:
                raise ManifestError(
                    f"{where}: provenance {key_name} must be {expected!r}, "
                    f"got {comp_provenance.get(key_name)!r}"
                )

        verification = component.get("digest_verification")
        if not isinstance(verification, dict):
            raise ManifestError(f"{where}: digest_verification must be an object")
        if verification.get("computed_from_file_bytes") is not True:
            raise ManifestError(f"{where}: digest must be computed from file bytes")
        if verification.get("caller_supplied_sha_used_as_identity") is not False:
            raise ManifestError(f"{where}: caller-supplied SHA must not be used as identity")
        expected_digest = verification.get("expected_sha256")
        if expected_digest is not None:
            _validate_sha256(expected_digest, f"{where}.expected_sha256")
            if expected_digest != digest:
                raise ManifestError(f"{where}: computed digest does not match supplied digest")

        if verify_files:
            try:
                current = Path(resolved_path).resolve(strict=True)
            except (OSError, RuntimeError) as exc:
                raise ManifestError(f"{where}: cannot resolve file for re-verification: {exc}") from exc
            if not current.is_file():
                raise ManifestError(f"{where}: resolved path is not a regular file")
            current_size = current.stat().st_size
            if current_size != size_bytes:
                raise ManifestError(
                    f"{where}: file size changed since collection "
                    f"({current_size} != {size_bytes})"
                )
            current_digest = _sha256_file(current)
            if current_digest != digest:
                raise ManifestError(
                    f"{where}: file bytes changed since collection; digest mismatch "
                    f"(current {current_digest}, manifest {digest})"
                )
    return manifest


def load_manifest(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as fh:
        try:
            data = json.load(fh)
        except json.JSONDecodeError as exc:
            raise ManifestError(f"invalid JSON manifest: {exc}") from exc
    return validate_manifest(data)


def _parse_expected(values: Iterable[str]) -> Dict[str, str]:
    expected: Dict[str, str] = {}
    for value in values:
        if "=" not in value:
            raise ComponentError(f"--expected must be NAME=SHA256, got {value!r}")
        name, digest = value.split("=", 1)
        name = _check_name(name.strip())
        if name in expected:
            raise ComponentError(f"duplicate --expected for component {name!r}")
        expected[name] = _validate_sha256(digest.strip(), f"--expected {name}")
    return expected


def write_manifest(path: str, manifest: dict) -> None:
    validate_manifest(manifest)
    output = Path(path)
    if output.parent and str(output.parent):
        output.parent.mkdir(parents=True, exist_ok=True)
    with open(output, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(manifest, fh, indent=2)
        fh.write("\n")


# Stable public aliases for the collector/validator pair.
collect_manifest = build_manifest
verify_manifest = validate_manifest


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--component", action="append", required=True, metavar="NAME=PATH",
                        help="component identity to collect; repeatable")
    parser.add_argument("--output", required=True, metavar="PATH",
                        help="write the private JSON manifest to this path")
    parser.add_argument("--source-revision", default=FROZEN_SOURCE_REVISION,
                        help="requested source revision (reference only, not build proof)")
    parser.add_argument("--expected", action="append", default=[], metavar="NAME=SHA256",
                        help="optional expected digest for comparison only; never identity")
    args = parser.parse_args(argv)
    try:
        expected = _parse_expected(args.expected)
        manifest = build_manifest(
            args.component,
            source_revision=args.source_revision,
            expected_digests=expected,
        )
        write_manifest(args.output, manifest)
    except (ComponentError, ManifestError, OSError) as exc:
        json.dump({
            "schema": SCHEMA_VERSION,
            "error": str(exc),
            "kind": "component_lock_error",
            "accepted": False,
            "runtime_acceptance": RUNTIME_ACCEPTANCE_NO,
        }, sys.stderr, indent=2)
        sys.stderr.write("\n")
        return 2
    summary = {
        "schema": SCHEMA_VERSION,
        "accepted": False,
        "components": manifest["summary"]["component_count"],
        "output": str(Path(args.output)),
        "source_revision": manifest["source_revision"],
        "source_build_association": SOURCE_BUILD_UNVERIFIED,
        "loaded_dll_evidence": LOADED_NOT_RUN,
        "runtime_acceptance": RUNTIME_ACCEPTANCE_NO,
    }
    json.dump(summary, sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
