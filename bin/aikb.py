#!/usr/bin/env python3
"""Git-backed, namespace-aware AI knowledge harness."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Iterator, Sequence

SCHEMA_VERSION = 1
NAMESPACE_PATTERN = re.compile(r"^[a-z0-9]+(?:[._-][a-z0-9]+)*$")
SEMVER_PATTERN = re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+$")
DATE_PATTERN = re.compile(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}$")
CONTRIBUTION_SLUG_PATTERN = re.compile(r"^[a-z0-9]+(?:[._-][a-z0-9]+)*$")
CLAIM_HEADER_PATTERN = re.compile(r"\A<!-- aikb\r?\n(.*?)\r?\n-->\r?\n?", re.DOTALL)
CODEC_FIELDS = frozenset({"codec_version", "z", "z_ref"})
MANIFEST_KINDS = frozenset(
    {
        "capability-procedure",
        "design-substrate",
        "empirical-findings",
        "working-discipline",
    }
)
MANIFEST_AUTHORITIES = frozenset(
    {"hand-authored-unmeasured", "primary-measurement", "reference-only"}
)
CLAIM_AUTHORITIES = frozenset({"hand-authored", "primary-measurement", "reference-only"})
CLAIM_STATUSES = frozenset({"active", "superseded", "withdrawn"})
EVIDENCE_CLASSES = frozenset(
    {"primary-result", "reported-summary", "design-reference", "operator-authored"}
)
ALLOWED_SHOW_ROOT_FILES = frozenset(
    {
        "AGENTS.md",
        "ARCHITECTURE.md",
        "CITATION.cff",
        "CODE_OF_CONDUCT.md",
        "CONTRIBUTING.md",
        "GOVERNANCE.md",
        "INDEX.md",
        "LICENSE",
        "README.md",
        "SECURITY.md",
        "SUPPORT.md",
        "catalog.json",
        "llms.txt",
        "registry.json",
    }
)


class HarnessError(RuntimeError):
    """A characterized harness failure."""


@dataclass(frozen=True)
class ManifestRecord:
    path: Path
    data: dict[str, Any]


@dataclass(frozen=True)
class ClaimRecord:
    path: Path
    data: dict[str, Any]
    body: str

    @property
    def ref(self) -> str:
        return f"{self.data['claim_id']}@{self.data['version']}"


@dataclass(frozen=True)
class NamespaceRecord:
    root: Path
    manifests: tuple[ManifestRecord, ...]
    active: ManifestRecord
    claims: tuple[ClaimRecord, ...]

    @property
    def namespace(self) -> str:
        return str(self.active.data["namespace"])


@dataclass(frozen=True)
class RepositoryState:
    repo: Path
    registry: dict[str, Any]
    namespaces: tuple[NamespaceRecord, ...]

    def by_namespace(self) -> dict[str, NamespaceRecord]:
        return {record.namespace: record for record in self.namespaces}


def _repo_default() -> Path:
    configured = os.environ.get("AI_KB_REPO")
    if configured:
        return Path(configured)
    return Path(__file__).resolve().parents[1]


def _read_canonical_text(path: Path) -> str:
    try:
        raw = path.read_bytes()
    except FileNotFoundError as exc:
        raise HarnessError(f"missing required file: {path}") from exc
    if b"\r" in raw:
        raise HarnessError(f"canonical text must use LF line endings: {path}")
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise HarnessError(f"canonical text is not UTF-8: {path}") from exc


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(_read_canonical_text(path))
    except json.JSONDecodeError as exc:
        raise HarnessError(f"invalid JSON at {path}:{exc.lineno}:{exc.colno}: {exc.msg}") from exc
    if not isinstance(value, dict):
        raise HarnessError(f"expected a JSON object at {path}")
    return value


def _canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=True, indent=2, sort_keys=True) + "\n"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _relative(repo: Path, path: Path) -> str:
    return path.resolve().relative_to(repo.resolve()).as_posix()


def _inside(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


def _safe_existing_path(root: Path, relative: str, label: str) -> Path:
    candidate = Path(relative)
    if candidate.is_absolute() or ".." in candidate.parts:
        raise HarnessError(f"{label} escapes its namespace: {relative}")
    resolved_root = root.resolve()
    try:
        resolved = (root / candidate).resolve(strict=True)
    except FileNotFoundError as exc:
        raise HarnessError(f"{label} does not exist: {relative}") from exc
    if not _inside(resolved, resolved_root):
        raise HarnessError(f"{label} resolves outside its namespace: {relative}")
    return resolved


def _extract_claim(path: Path) -> ClaimRecord:
    text = _read_canonical_text(path)
    match = CLAIM_HEADER_PATTERN.match(text)
    if not match:
        raise HarnessError(f"claim is missing the '<!-- aikb' JSON header: {path}")
    try:
        metadata = json.loads(match.group(1))
    except json.JSONDecodeError as exc:
        raise HarnessError(
            f"invalid claim metadata at {path}:{exc.lineno}:{exc.colno}: {exc.msg}"
        ) from exc
    if not isinstance(metadata, dict):
        raise HarnessError(f"claim metadata must be a JSON object: {path}")
    return ClaimRecord(path=path, data=metadata, body=text[match.end() :])


def _required_keys(
    value: dict[str, Any],
    required: set[str],
    allowed: set[str],
    label: str,
    errors: list[str],
) -> None:
    for key in sorted(required - value.keys()):
        errors.append(f"{label}: missing required field '{key}'")
    for key in sorted(value.keys() - allowed):
        errors.append(f"{label}: unknown field '{key}'")


def _string_list(
    value: Any, label: str, errors: list[str], *, allow_empty: bool = True
) -> bool:
    if not isinstance(value, list) or any(not isinstance(item, str) or not item for item in value):
        errors.append(f"{label}: must be a list of non-empty strings")
        return False
    if not allow_empty and not value:
        errors.append(f"{label}: must not be empty")
    if len(value) != len(set(value)):
        errors.append(f"{label}: contains duplicates")
    return True


def _find_forbidden_fields(value: Any, path: str = "") -> Iterator[str]:
    if isinstance(value, dict):
        for key, nested in value.items():
            current = f"{path}.{key}" if path else key
            if key in CODEC_FIELDS:
                yield current
            yield from _find_forbidden_fields(nested, current)
    elif isinstance(value, list):
        for index, nested in enumerate(value):
            yield from _find_forbidden_fields(nested, f"{path}[{index}]")


def _validate_registry(repo: Path, registry: dict[str, Any], errors: list[str]) -> None:
    label = "registry.json"
    required = {
        "schema_version",
        "repository",
        "namespaces_root",
        "trust",
        "index_extensions",
        "exclude_directories",
    }
    _required_keys(registry, required, required | {"$schema"}, label, errors)
    if registry.get("schema_version") != SCHEMA_VERSION:
        errors.append(f"{label}: schema_version must be {SCHEMA_VERSION}")

    repository = registry.get("repository")
    if not isinstance(repository, dict):
        errors.append(f"{label}.repository: must be an object")
    else:
        expected = {"canonical_remote", "default_branch"}
        _required_keys(repository, expected, expected, f"{label}.repository", errors)
        for key in expected:
            if not isinstance(repository.get(key), str) or not repository.get(key):
                errors.append(f"{label}.repository.{key}: must be a non-empty string")

    namespaces_root = registry.get("namespaces_root")
    if not isinstance(namespaces_root, str) or not NAMESPACE_PATTERN.fullmatch(namespaces_root):
        errors.append(f"{label}.namespaces_root: must be one safe path segment")
    elif not (repo / namespaces_root).is_dir():
        errors.append(f"{label}.namespaces_root: directory does not exist: {namespaces_root}")

    trust = registry.get("trust")
    if not isinstance(trust, dict):
        errors.append(f"{label}.trust: must be an object")
    else:
        expected = {"policy", "note"}
        _required_keys(trust, expected, expected, f"{label}.trust", errors)
        if trust.get("policy") != "reference-only":
            errors.append(f"{label}.trust.policy: must be 'reference-only'")
        if not isinstance(trust.get("note"), str) or not trust.get("note"):
            errors.append(f"{label}.trust.note: must be a non-empty string")

    extensions = registry.get("index_extensions")
    if _string_list(
        extensions,
        f"{label}.index_extensions",
        errors,
        allow_empty=False,
    ):
        for extension in extensions:
            if not re.fullmatch(r"\.[a-z0-9]+", extension):
                errors.append(f"{label}.index_extensions: invalid extension '{extension}'")
    _string_list(registry.get("exclude_directories"), f"{label}.exclude_directories", errors)


def _validate_manifest(
    repo: Path,
    namespace_root: Path,
    record: ManifestRecord,
    expected_namespace: str,
    errors: list[str],
) -> None:
    data = record.data
    label = _relative(repo, record.path)
    required = {
        "schema_version",
        "namespace",
        "generation",
        "supersedes",
        "title",
        "kind",
        "authority",
        "extends",
        "consult_when",
        "entry_points",
        "search_paths",
    }
    _required_keys(data, required, required | {"$schema"}, label, errors)
    if data.get("schema_version") != SCHEMA_VERSION:
        errors.append(f"{label}: schema_version must be {SCHEMA_VERSION}")
    namespace = data.get("namespace")
    if not isinstance(namespace, str) or not NAMESPACE_PATTERN.fullmatch(namespace):
        errors.append(f"{label}.namespace: invalid namespace")
    elif namespace != expected_namespace:
        errors.append(
            f"{label}.namespace: '{namespace}' does not match directory '{expected_namespace}'"
        )
    generation = data.get("generation")
    if not isinstance(generation, int) or isinstance(generation, bool) or generation < 1:
        errors.append(f"{label}.generation: must be a positive integer")
    else:
        expected_name = f"{generation:04d}.json"
        if record.path.name != expected_name:
            errors.append(f"{label}: filename must be '{expected_name}'")
        expected_supersedes = None if generation == 1 else f"manifests/{generation - 1:04d}.json"
        if data.get("supersedes") != expected_supersedes:
            errors.append(
                f"{label}.supersedes: expected {expected_supersedes!r}, got {data.get('supersedes')!r}"
            )
    if not isinstance(data.get("title"), str) or not data.get("title"):
        errors.append(f"{label}.title: must be a non-empty string")
    if data.get("kind") not in MANIFEST_KINDS:
        errors.append(f"{label}.kind: unsupported value {data.get('kind')!r}")
    if data.get("authority") not in MANIFEST_AUTHORITIES:
        errors.append(f"{label}.authority: unsupported value {data.get('authority')!r}")
    parent = data.get("extends")
    if parent is not None and (
        not isinstance(parent, str) or not NAMESPACE_PATTERN.fullmatch(parent)
    ):
        errors.append(f"{label}.extends: must be null or a valid namespace")
    for field in ("entry_points", "search_paths"):
        values = data.get(field)
        if not _string_list(
            values,
            f"{label}.{field}",
            errors,
            allow_empty=field != "search_paths",
        ):
            continue
        for relative in values:
            try:
                _safe_existing_path(namespace_root, relative, f"{label}.{field}")
            except HarnessError as exc:
                errors.append(str(exc))
    _string_list(data.get("consult_when"), f"{label}.consult_when", errors)


def _validate_claim(
    repo: Path,
    record: ClaimRecord,
    expected_namespace: str,
    namespace_kind: str,
    errors: list[str],
) -> None:
    data = record.data
    label = _relative(repo, record.path)
    required = {
        "schema_version",
        "claim_id",
        "namespace",
        "version",
        "expression",
        "authority",
        "scope",
        "confidence",
        "confidence_method",
        "provenance",
        "lineage",
        "relationships",
        "retrieval",
    }
    _required_keys(data, required, required, label, errors)
    if data.get("schema_version") != SCHEMA_VERSION:
        errors.append(f"{label}: schema_version must be {SCHEMA_VERSION}")
    claim_id = data.get("claim_id")
    if not isinstance(claim_id, str) or not NAMESPACE_PATTERN.fullmatch(claim_id):
        errors.append(f"{label}.claim_id: invalid identifier")
    namespace = data.get("namespace")
    if namespace != expected_namespace:
        errors.append(
            f"{label}.namespace: {namespace!r} does not match directory {expected_namespace!r}"
        )
    version = data.get("version")
    if not isinstance(version, str) or not SEMVER_PATTERN.fullmatch(version):
        errors.append(f"{label}.version: must be semantic x.y.z")
    if isinstance(claim_id, str) and isinstance(version, str):
        expected_name = f"{claim_id}--{version}.md"
        if record.path.name != expected_name:
            errors.append(f"{label}: filename must be '{expected_name}'")
    if not isinstance(data.get("expression"), str) or not data.get("expression"):
        errors.append(f"{label}.expression: must be a non-empty string")
    authority = data.get("authority")
    if authority not in CLAIM_AUTHORITIES:
        errors.append(f"{label}.authority: unsupported value {authority!r}")
    confidence = data.get("confidence")
    if confidence is not None and (
        isinstance(confidence, bool)
        or not isinstance(confidence, (int, float))
        or not 0 <= confidence <= 1
    ):
        errors.append(f"{label}.confidence: must be null or a number in [0, 1]")
    confidence_method = data.get("confidence_method")
    if not isinstance(confidence_method, str) or not confidence_method:
        errors.append(f"{label}.confidence_method: must be a non-empty string")
    if authority == "hand-authored":
        if confidence is not None:
            errors.append(f"{label}: hand-authored claims must have null confidence")
        if isinstance(confidence_method, str) and not confidence_method.endswith("unmeasured"):
            errors.append(
                f"{label}: hand-authored null confidence must use an unmeasured method"
            )

    scope = data.get("scope")
    if not isinstance(scope, dict):
        errors.append(f"{label}.scope: must be an object")
    else:
        expected = {"holds_when", "expires"}
        _required_keys(scope, expected, expected, f"{label}.scope", errors)
        if not isinstance(scope.get("holds_when"), str) or not scope.get("holds_when"):
            errors.append(f"{label}.scope.holds_when: must be a non-empty string")
        if scope.get("expires") is not None and not isinstance(scope.get("expires"), str):
            errors.append(f"{label}.scope.expires: must be null or a string")

    provenance = data.get("provenance")
    if not isinstance(provenance, dict):
        errors.append(f"{label}.provenance: must be an object")
    else:
        expected = {"producer", "producer_version", "authored_utc", "derived_from"}
        _required_keys(provenance, expected, expected, f"{label}.provenance", errors)
        for field in ("producer", "producer_version"):
            if not isinstance(provenance.get(field), str) or not provenance.get(field):
                errors.append(f"{label}.provenance.{field}: must be a non-empty string")
        authored = provenance.get("authored_utc")
        if not isinstance(authored, str) or not DATE_PATTERN.fullmatch(authored):
            errors.append(f"{label}.provenance.authored_utc: must be YYYY-MM-DD")
        sources = provenance.get("derived_from")
        if not isinstance(sources, list):
            errors.append(f"{label}.provenance.derived_from: must be a list")
        else:
            for index, source in enumerate(sources):
                source_label = f"{label}.provenance.derived_from[{index}]"
                if not isinstance(source, dict):
                    errors.append(f"{source_label}: must be an object")
                    continue
                expected_source = {"source", "locator", "evidence_class"}
                _required_keys(source, expected_source, expected_source, source_label, errors)
                for field in ("source", "locator"):
                    if not isinstance(source.get(field), str) or not source.get(field):
                        errors.append(f"{source_label}.{field}: must be a non-empty string")
                if source.get("evidence_class") not in EVIDENCE_CLASSES:
                    errors.append(
                        f"{source_label}.evidence_class: unsupported value "
                        f"{source.get('evidence_class')!r}"
                    )

    lineage = data.get("lineage")
    if not isinstance(lineage, dict):
        errors.append(f"{label}.lineage: must be an object")
    else:
        expected = {"status", "generation", "parent_refs"}
        _required_keys(lineage, expected, expected, f"{label}.lineage", errors)
        if lineage.get("status") not in CLAIM_STATUSES:
            errors.append(f"{label}.lineage.status: unsupported value {lineage.get('status')!r}")
        generation = lineage.get("generation")
        if not isinstance(generation, int) or isinstance(generation, bool) or generation < 1:
            errors.append(f"{label}.lineage.generation: must be a positive integer")
        parent_refs = lineage.get("parent_refs")
        if _string_list(parent_refs, f"{label}.lineage.parent_refs", errors):
            for parent_ref in parent_refs:
                if not re.fullmatch(
                    r"[a-z0-9]+(?:[._-][a-z0-9]+)*@[0-9]+\.[0-9]+\.[0-9]+",
                    parent_ref,
                ):
                    errors.append(
                        f"{label}.lineage.parent_refs: invalid ref '{parent_ref}'"
                    )

    relationships = data.get("relationships")
    if not isinstance(relationships, list):
        errors.append(f"{label}.relationships: must be a list")
    else:
        for index, relationship in enumerate(relationships):
            relationship_label = f"{label}.relationships[{index}]"
            if not isinstance(relationship, dict):
                errors.append(f"{relationship_label}: must be an object")
                continue
            expected = {"kind", "target"}
            _required_keys(relationship, expected, expected, relationship_label, errors)
            for field in expected:
                if not isinstance(relationship.get(field), str) or not relationship.get(field):
                    errors.append(f"{relationship_label}.{field}: must be a non-empty string")

    retrieval = data.get("retrieval")
    if not isinstance(retrieval, dict):
        errors.append(f"{label}.retrieval: must be an object")
    else:
        expected = {"tags"}
        _required_keys(retrieval, expected, expected, f"{label}.retrieval", errors)
        tags = retrieval.get("tags")
        if _string_list(tags, f"{label}.retrieval.tags", errors):
            for tag in tags:
                if not NAMESPACE_PATTERN.fullmatch(tag):
                    errors.append(f"{label}.retrieval.tags: invalid tag '{tag}'")

    for forbidden in _find_forbidden_fields(data):
        errors.append(f"{label}: codec-produced field is forbidden: {forbidden}")

    lowered_body = record.body.lower()
    if not record.body.strip():
        errors.append(f"{label}: claim body must not be empty")
    for placeholder in ("replace with", "yyyy-mm-dd", "todo"):
        if placeholder in lowered_body:
            errors.append(f"{label}: unresolved template placeholder '{placeholder}'")
    if namespace_kind == "capability-procedure" and "Falsified if:" not in record.body:
        errors.append(f"{label}: capability procedures require a 'Falsified if:' condition")


def _load_state(repo: Path) -> tuple[RepositoryState | None, list[str]]:
    repo = repo.resolve()
    errors: list[str] = []
    try:
        registry = _read_json(repo / "registry.json")
    except HarnessError as exc:
        return None, [str(exc)]
    _validate_registry(repo, registry, errors)
    namespaces_root_value = registry.get("namespaces_root")
    if not isinstance(namespaces_root_value, str):
        return None, errors
    namespaces_root = repo / namespaces_root_value
    if not namespaces_root.is_dir():
        return None, errors

    namespace_records: list[NamespaceRecord] = []
    for namespace_root in sorted(
        (path for path in namespaces_root.iterdir() if path.is_dir()),
        key=lambda path: path.name,
    ):
        namespace = namespace_root.name
        if not NAMESPACE_PATTERN.fullmatch(namespace):
            errors.append(
                f"{_relative(repo, namespace_root)}: directory is not a valid namespace"
            )
            continue
        manifest_dir = namespace_root / "manifests"
        manifest_paths = sorted(manifest_dir.glob("*.json")) if manifest_dir.is_dir() else []
        if not manifest_paths:
            errors.append(f"{_relative(repo, namespace_root)}: no manifests found")
            continue
        manifests: list[ManifestRecord] = []
        for manifest_path in manifest_paths:
            try:
                manifest = ManifestRecord(manifest_path, _read_json(manifest_path))
            except HarnessError as exc:
                errors.append(str(exc))
                continue
            manifests.append(manifest)
            _validate_manifest(repo, namespace_root, manifest, namespace, errors)
        if not manifests:
            continue
        generations = [
            record.data.get("generation")
            for record in manifests
            if isinstance(record.data.get("generation"), int)
            and not isinstance(record.data.get("generation"), bool)
        ]
        if generations != list(range(1, len(manifests) + 1)):
            errors.append(
                f"{_relative(repo, manifest_dir)}: generations must be contiguous from 1"
            )
        active = max(
            manifests,
            key=lambda record: (
                record.data.get("generation")
                if isinstance(record.data.get("generation"), int)
                else -1
            ),
        )
        claims_dir = namespace_root / "claims"
        claim_paths = sorted(claims_dir.glob("*.md")) if claims_dir.is_dir() else []
        claims: list[ClaimRecord] = []
        for claim_path in claim_paths:
            try:
                claim = _extract_claim(claim_path)
            except HarnessError as exc:
                errors.append(str(exc))
                continue
            claims.append(claim)
            _validate_claim(
                repo,
                claim,
                namespace,
                str(active.data.get("kind", "")),
                errors,
            )
        namespace_records.append(
            NamespaceRecord(
                root=namespace_root,
                manifests=tuple(manifests),
                active=active,
                claims=tuple(claims),
            )
        )

    state = RepositoryState(repo=repo, registry=registry, namespaces=tuple(namespace_records))
    if errors:
        return state, errors
    by_namespace = state.by_namespace()
    for namespace, record in sorted(by_namespace.items()):
        parent = record.active.data.get("extends")
        if parent is not None and parent not in by_namespace:
            errors.append(
                f"{_relative(repo, record.active.path)}.extends: missing namespace '{parent}'"
            )
        if parent == namespace:
            errors.append(
                f"{_relative(repo, record.active.path)}.extends: namespace cannot extend itself"
            )

    for namespace in sorted(by_namespace):
        seen: list[str] = []
        current: str | None = namespace
        while current is not None and current in by_namespace:
            if current in seen:
                cycle = " -> ".join(seen[seen.index(current) :] + [current])
                errors.append(f"namespace specialization cycle: {cycle}")
                break
            seen.append(current)
            parent = by_namespace[current].active.data.get("extends")
            current = parent if isinstance(parent, str) else None

    refs: dict[str, ClaimRecord] = {}
    for namespace_record in state.namespaces:
        for claim in namespace_record.claims:
            if claim.ref in refs:
                errors.append(
                    f"duplicate claim ref '{claim.ref}': "
                    f"{_relative(repo, refs[claim.ref].path)} and {_relative(repo, claim.path)}"
                )
            refs[claim.ref] = claim
    for namespace_record in state.namespaces:
        for claim in namespace_record.claims:
            lineage = claim.data.get("lineage")
            if not isinstance(lineage, dict):
                continue
            for parent_ref in lineage.get("parent_refs", []):
                if isinstance(parent_ref, str) and parent_ref not in refs:
                    errors.append(
                        f"{_relative(repo, claim.path)}.lineage.parent_refs: "
                        f"missing claim '{parent_ref}'"
                    )

    return state, errors


def _ancestors(state: RepositoryState, namespace: str) -> list[str]:
    by_namespace = state.by_namespace()
    if namespace not in by_namespace:
        raise HarnessError(f"unknown namespace '{namespace}'. Run: aikb list")
    lineage: list[str] = []
    seen: set[str] = set()
    current: str | None = namespace
    while current is not None:
        if current in seen:
            cycle = " -> ".join(lineage[lineage.index(current) :] + [current])
            raise HarnessError(f"namespace specialization cycle: {cycle}")
        record = by_namespace.get(current)
        if record is None:
            raise HarnessError(
                f"namespace '{lineage[-1]}' extends missing namespace '{current}'"
            )
        seen.add(current)
        lineage.append(current)
        parent = record.active.data.get("extends")
        current = parent if isinstance(parent, str) else None
    lineage.reverse()
    return lineage


def _build_catalog(state: RepositoryState) -> dict[str, Any]:
    namespaces: list[dict[str, Any]] = []
    for namespace_record in sorted(state.namespaces, key=lambda record: record.namespace):
        active = namespace_record.active
        claims: list[dict[str, Any]] = []
        for claim in sorted(
            namespace_record.claims,
            key=lambda record: (
                str(record.data.get("claim_id", "")),
                tuple(int(part) for part in str(record.data.get("version", "0.0.0")).split(".")),
            ),
        ):
            claims.append(
                {
                    "authority": claim.data["authority"],
                    "claim_id": claim.data["claim_id"],
                    "claim_ref": claim.ref,
                    "confidence": claim.data["confidence"],
                    "confidence_method": claim.data["confidence_method"],
                    "expression": claim.data["expression"],
                    "generation": claim.data["lineage"]["generation"],
                    "parent_refs": sorted(claim.data["lineage"]["parent_refs"]),
                    "path": _relative(state.repo, claim.path),
                    "sha256": _sha256(claim.path),
                    "status": claim.data["lineage"]["status"],
                    "tags": sorted(claim.data["retrieval"]["tags"]),
                    "version": claim.data["version"],
                }
            )
        manifest_history = [
            {
                "generation": manifest.data["generation"],
                "path": _relative(state.repo, manifest.path),
                "sha256": _sha256(manifest.path),
                "supersedes": manifest.data["supersedes"],
            }
            for manifest in sorted(
                namespace_record.manifests,
                key=lambda record: int(record.data.get("generation", 0)),
            )
        ]
        namespaces.append(
            {
                "authority": active.data["authority"],
                "claims": claims,
                "consult_when": sorted(active.data["consult_when"]),
                "entry_points": sorted(active.data["entry_points"]),
                "extends": active.data["extends"],
                "kind": active.data["kind"],
                "lineage": _ancestors(state, namespace_record.namespace),
                "manifest": manifest_history[-1],
                "manifest_history": manifest_history,
                "namespace": namespace_record.namespace,
                "search_paths": sorted(active.data["search_paths"]),
                "title": active.data["title"],
            }
        )
    return {
        "projection": {
            "authority": "derived",
            "generator": "bin/aikb.py refresh",
            "rebuildable_from": "namespaces/",
        },
        "repository": state.registry["repository"],
        "schema_version": SCHEMA_VERSION,
        "trust": state.registry["trust"],
        "namespaces": namespaces,
    }


def _markdown_link(path: str, text: str) -> str:
    escaped_path = path.replace(" ", "%20")
    return f"[{text}]({escaped_path})"


def _build_index(state: RepositoryState, catalog: dict[str, Any]) -> str:
    lines = [
        "# AI KNOWLEDGE BASE",
        "",
        "> Deterministic projection generated by `aikb refresh`. Do not hand-edit.",
        "> Counts and hashes derive from repository files; this projection has no authority.",
        "",
        "## Trust boundary",
        "",
        state.registry["trust"]["note"],
        "",
        "## Read commands",
        "",
        "```text",
        "aikb list",
        "aikb search \"query\" [--namespace id]",
        "aikb show namespaces/<id>/claims/<file> --start 1 --end 80",
        "aikb lineage <namespace>",
        "aikb status",
        "aikb check",
        "```",
        "",
        "## Namespace map",
        "",
        "| Namespace | Kind | Extends | Claims |",
        "|---|---|---|---:|",
    ]
    for namespace in catalog["namespaces"]:
        manifest_path = namespace["manifest"]["path"]
        parent = namespace["extends"] or "-"
        lines.append(
            "| "
            + _markdown_link(manifest_path, f"`{namespace['namespace']}`")
            + f" | {namespace['kind']} | {parent} | {len(namespace['claims'])} |"
        )

    for namespace in catalog["namespaces"]:
        lines.extend(
            [
                "",
                f"## `{namespace['namespace']}`",
                "",
                namespace["title"],
                "",
                f"- **Kind:** {namespace['kind']}",
                f"- **Authority:** {namespace['authority']}",
                f"- **Extends:** {namespace['extends'] or 'none'}",
                f"- **Lineage:** {' -> '.join(namespace['lineage'])}",
                "- **Consult when:**",
            ]
        )
        if namespace["consult_when"]:
            lines.extend(f"  - {item}" for item in namespace["consult_when"])
        else:
            lines.append("  - no routing hints declared")
        lines.append("- **Claims:**")
        if namespace["claims"]:
            for claim in namespace["claims"]:
                link = _markdown_link(claim["path"], f"`{claim['claim_ref']}`")
                lines.append(
                    f"  - {link} [{claim['authority']}; {claim['status']}] — "
                    f"{claim['expression']}"
                )
        else:
            lines.append("  - none yet")
    return "\n".join(lines) + "\n"


def _projection_texts(state: RepositoryState) -> tuple[str, str]:
    catalog = _build_catalog(state)
    return _canonical_json(catalog), _build_index(state, catalog)


def _validate_projection(state: RepositoryState) -> list[str]:
    expected_catalog, expected_index = _projection_texts(state)
    errors: list[str] = []
    for name, expected in (("catalog.json", expected_catalog), ("INDEX.md", expected_index)):
        path = state.repo / name
        if not path.is_file():
            errors.append(f"{name}: generated projection is missing; run: aikb refresh")
            continue
        actual = path.read_text(encoding="utf-8")
        if actual != expected:
            errors.append(f"{name}: generated projection is stale; run: aikb refresh")
    return errors


def _print_errors(errors: Iterable[str]) -> None:
    for error in errors:
        print(f"FAIL  {error}", file=sys.stderr)


def _require_valid_state(repo: Path, *, projection: bool) -> RepositoryState:
    state, errors = _load_state(repo)
    if state is None or errors:
        _print_errors(errors)
        raise HarnessError(f"{len(errors)} validation violation(s)")
    if projection:
        errors.extend(_validate_projection(state))
        if errors:
            _print_errors(errors)
            raise HarnessError(f"{len(errors)} validation violation(s)")
    return state


def _selected_namespaces(
    state: RepositoryState, namespace: str | None, exact_namespace: bool
) -> list[NamespaceRecord]:
    by_namespace = state.by_namespace()
    if namespace is None:
        return sorted(state.namespaces, key=lambda record: record.namespace)
    lineage = [namespace] if exact_namespace else _ancestors(state, namespace)
    return [by_namespace[item] for item in lineage]


def _search_files(
    state: RepositoryState, namespaces: Sequence[NamespaceRecord], extensions: set[str]
) -> list[tuple[str, Path]]:
    excluded = set(state.registry["exclude_directories"])
    seen: set[Path] = set()
    files: list[tuple[str, Path]] = []
    for namespace_record in namespaces:
        for relative in namespace_record.active.data["search_paths"]:
            target = _safe_existing_path(
                namespace_record.root,
                relative,
                f"{namespace_record.namespace}.search_paths",
            )
            candidates = [target] if target.is_file() else target.rglob("*")
            for candidate in candidates:
                if not candidate.is_file() or candidate.suffix.lower() not in extensions:
                    continue
                resolved = candidate.resolve()
                repository_parts = resolved.relative_to(state.repo.resolve()).parts
                if any(part in excluded for part in repository_parts):
                    continue
                if resolved in seen:
                    continue
                if not _inside(resolved, namespace_record.root.resolve()):
                    raise HarnessError(f"search path escaped namespace: {candidate}")
                seen.add(resolved)
                files.append((namespace_record.namespace, candidate))
    return sorted(files, key=lambda item: (item[0], _relative(state.repo, item[1])))


def _run_git(repo: Path, args: Sequence[str], *, check: bool = True) -> str:
    try:
        completed = subprocess.run(
            ["git", "-C", str(repo), *args],
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
    except FileNotFoundError as exc:
        raise HarnessError("git is required but was not found on PATH") from exc
    if check and completed.returncode != 0:
        detail = completed.stderr.strip() or completed.stdout.strip()
        raise HarnessError(f"git {' '.join(args)} failed: {detail}")
    return completed.stdout.strip()


def _normalize_remote(remote: str) -> str:
    value = remote.strip().rstrip("/")
    ssh_match = re.fullmatch(r"git@github\.com:(.+)", value)
    if ssh_match:
        value = f"https://github.com/{ssh_match.group(1)}"
    ssh_url_match = re.fullmatch(r"ssh://git@github\.com/(.+)", value)
    if ssh_url_match:
        value = f"https://github.com/{ssh_url_match.group(1)}"
    return value.removesuffix(".git").rstrip("/").lower()


def _remote_names(repo: Path) -> list[str]:
    return sorted(name for name in _run_git(repo, ["remote"]).splitlines() if name)


def _canonical_remote(repo: Path, expected: str) -> tuple[str, str]:
    matches: list[tuple[str, str]] = []
    for name in _remote_names(repo):
        url = _run_git(repo, ["remote", "get-url", name])
        if _normalize_remote(url) == _normalize_remote(expected):
            matches.append((name, url))
    if not matches:
        raise HarnessError(
            f"canonical remote missing: expected a configured remote for {expected}; "
            "fork clones should keep the source repository as 'upstream'"
        )
    priority = {"origin": 0, "upstream": 1}
    return min(matches, key=lambda match: (priority.get(match[0], 2), match[0]))


def _github_repository(remote: str) -> str | None:
    normalized = _normalize_remote(remote)
    prefix = "https://github.com/"
    if normalized.startswith(prefix):
        return normalized.removeprefix(prefix)
    return None


def command_list(args: argparse.Namespace) -> int:
    state = _require_valid_state(args.repo, projection=True)
    print("AI knowledge namespaces")
    print(f"repository: {state.repo}")
    print()
    for namespace in sorted(state.namespaces, key=lambda record: record.namespace):
        parent = namespace.active.data["extends"] or "-"
        print(f"{namespace.namespace}")
        print(f"  {namespace.active.data['title']}")
        print(
            f"  kind={namespace.active.data['kind']} "
            f"authority={namespace.active.data['authority']} extends={parent}"
        )
        print(f"  claims={len(namespace.claims)}")
    print()
    print(f"Trust policy: {state.registry['trust']['policy']}")
    print(state.registry["trust"]["note"])
    return 0


def command_index(args: argparse.Namespace) -> int:
    _require_valid_state(args.repo, projection=True)
    print((args.repo / "INDEX.md").read_text(encoding="utf-8"), end="")
    return 0


def command_search(args: argparse.Namespace) -> int:
    state = _require_valid_state(args.repo, projection=True)
    query = " ".join(args.query).strip()
    if not query:
        raise HarnessError("search query must not be empty")
    extensions = {
        (extension if extension.startswith(".") else f".{extension}").lower()
        for extension in (args.ext or state.registry["index_extensions"])
    }
    namespaces = _selected_namespaces(state, args.namespace, args.exact_namespace)
    try:
        pattern = re.compile(query if args.regex else re.escape(query), re.IGNORECASE)
    except re.error as exc:
        raise HarnessError(f"invalid regular expression: {exc}") from exc
    hits = 0
    for namespace, path in _search_files(state, namespaces, extensions):
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except UnicodeDecodeError as exc:
            raise HarnessError(f"search target is not UTF-8: {path}") from exc
        for index, line in enumerate(lines):
            if not pattern.search(line):
                continue
            if hits >= args.max:
                break
            hits += 1
            relative = _relative(state.repo, path)
            print(f"{namespace}:{relative}:{index + 1}")
            first = max(0, index - args.context)
            last = min(len(lines), index + args.context + 1)
            for line_index in range(first, last):
                marker = ">" if line_index == index else "|"
                print(f"  {marker} {line_index + 1:5d} {lines[line_index]}")
        if hits >= args.max:
            break
    capped = f" (capped at --max {args.max})" if hits >= args.max else ""
    print(f"\n{hits} hit(s){capped}")
    return 0


def _resolve_show_path(state: RepositoryState, value: str) -> Path:
    by_namespace = state.by_namespace()
    namespace_prefix, separator, namespace_relative = value.partition(":")
    if separator and namespace_prefix in by_namespace:
        candidate = _safe_existing_path(
            by_namespace[namespace_prefix].root,
            namespace_relative,
            "show path",
        )
    else:
        raw = Path(value)
        if raw.is_absolute() or ".." in raw.parts:
            raise HarnessError("show path must be repository-relative and may not contain '..'")
        try:
            candidate = (state.repo / raw).resolve(strict=True)
        except FileNotFoundError as exc:
            raise HarnessError(f"not found: {value}") from exc
    namespaces_root = (state.repo / state.registry["namespaces_root"]).resolve()
    allowed_root_file = (
        candidate.parent == state.repo.resolve() and candidate.name in ALLOWED_SHOW_ROOT_FILES
    )
    if not _inside(candidate, namespaces_root) and not allowed_root_file:
        raise HarnessError(
            "refused: show is confined to namespaces and documented generated entry points"
        )
    if not candidate.is_file():
        raise HarnessError(f"show target is not a file: {value}")
    return candidate


def command_show(args: argparse.Namespace) -> int:
    state = _require_valid_state(args.repo, projection=True)
    path = _resolve_show_path(state, args.path)
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except UnicodeDecodeError as exc:
        raise HarnessError(f"show target is not UTF-8: {path}") from exc
    start = max(1, args.start)
    end = min(len(lines), args.end if args.end > 0 else len(lines))
    if end < start:
        raise HarnessError(f"invalid line range: start={start}, end={end}")
    print(f"--- {_relative(state.repo, path)} (lines {start}-{end} of {len(lines)})")
    for line_number in range(start, end + 1):
        print(f"{line_number:6d}  {lines[line_number - 1]}")
    return 0


def command_lineage(args: argparse.Namespace) -> int:
    state = _require_valid_state(args.repo, projection=True)
    lineage = _ancestors(state, args.namespace)
    for index, namespace in enumerate(lineage):
        marker = "\\-" if index == len(lineage) - 1 else "|-"
        print(f"{marker} {namespace}")
    return 0


def command_validate(args: argparse.Namespace) -> int:
    state, errors = _load_state(args.repo)
    if state is None or errors:
        _print_errors(errors)
        print(f"\n{len(errors)} validation violation(s)", file=sys.stderr)
        return 1
    if args.projection:
        errors.extend(_validate_projection(state))
        if errors:
            _print_errors(errors)
            print(f"\n{len(errors)} validation violation(s)", file=sys.stderr)
            return 1
    claim_count = sum(len(namespace.claims) for namespace in state.namespaces)
    suffix = " including projections" if args.projection else ""
    print(
        f"OK    {len(state.namespaces)} namespace(s), {claim_count} claim(s){suffix}"
    )
    return 0


def command_refresh(args: argparse.Namespace) -> int:
    state = _require_valid_state(args.repo, projection=False)
    catalog, index = _projection_texts(state)
    targets = (("catalog.json", catalog), ("INDEX.md", index))
    stale = [
        name
        for name, expected in targets
        if not (state.repo / name).is_file()
        or (state.repo / name).read_text(encoding="utf-8") != expected
    ]
    if args.check:
        if stale:
            for name in stale:
                print(f"STALE {name}", file=sys.stderr)
            return 1
        print("OK    generated projections are byte-current")
        return 0
    for name, expected in targets:
        path = state.repo / name
        if name in stale:
            path.write_text(expected, encoding="utf-8", newline="\n")
            print(f"wrote {path}")
        else:
            print(f"ok    {path}")
    return 0


def command_contribute(args: argparse.Namespace) -> int:
    state = _require_valid_state(args.repo, projection=True)
    if (
        len(args.slug) > 64
        or not CONTRIBUTION_SLUG_PATTERN.fullmatch(args.slug)
    ):
        raise HarnessError(
            "contribution slug must be at most 64 characters and use lowercase "
            "letters, numbers, dots, dashes, or underscores"
        )

    expected = state.registry["repository"]["canonical_remote"]
    canonical_remote, _ = _canonical_remote(state.repo, expected)
    push_remote = args.push_remote
    if push_remote not in _remote_names(state.repo):
        raise HarnessError(
            f"contribution refused: push remote '{push_remote}' is not configured"
        )

    default_branch = state.registry["repository"]["default_branch"]
    current_branch = _run_git(state.repo, ["branch", "--show-current"])
    if current_branch != default_branch:
        raise HarnessError(
            f"contribution refused: canonical checkout must be on "
            f"'{default_branch}', found '{current_branch or 'detached HEAD'}'"
        )
    if _run_git(state.repo, ["status", "--porcelain"]):
        raise HarnessError("contribution refused: canonical checkout has local changes")

    branch = f"improvement/{args.slug}"
    target_input = (
        args.worktree
        if args.worktree is not None
        else state.repo.parent / f"{state.repo.name}-{args.slug}"
    )
    target = target_input.expanduser()
    if not target.is_absolute():
        target = Path.cwd() / target
    target = target.resolve()
    if _inside(target, state.repo.resolve()):
        raise HarnessError("contribution worktree must be outside the canonical checkout")
    if target.exists():
        raise HarnessError(f"contribution worktree already exists: {target}")

    local_ref = f"refs/heads/{branch}"
    if _run_git(
        state.repo,
        ["show-ref", "--verify", local_ref],
        check=False,
    ):
        raise HarnessError(f"contribution branch already exists locally: {branch}")
    if _run_git(
        state.repo,
        ["ls-remote", "--heads", push_remote, local_ref],
    ):
        raise HarnessError(
            f"contribution branch already exists on {push_remote}: {branch}"
        )

    remote_default = f"refs/remotes/{canonical_remote}/{default_branch}"
    _run_git(
        state.repo,
        [
            "fetch",
            "--no-tags",
            canonical_remote,
            f"+refs/heads/{default_branch}:{remote_default}",
        ],
    )
    _run_git(
        state.repo,
        [
            "worktree",
            "add",
            "-b",
            branch,
            str(target),
            f"{canonical_remote}/{default_branch}",
        ],
    )

    print("OK    isolated contribution worktree created")
    print(f"worktree: {target}")
    print(f"branch:   {branch}")
    print(f"base:     {canonical_remote}/{default_branch}")
    print(f"push:     {push_remote}")
    print()
    print("next:")
    print(f'  cd "{target}"')
    print("  read CONTRIBUTING.md")
    print("  python bin/aikb.py --repo . validate --projection")
    print("  python -m unittest discover -s tests -v")
    print(f"  git push --set-upstream {push_remote} {branch}")
    repository = _github_repository(expected)
    if repository is None:
        print("  gh pr create --fill")
    else:
        print(f"  gh pr create --repo {repository} --fill")
    return 0


def command_status(args: argparse.Namespace) -> int:
    state = _require_valid_state(args.repo, projection=True)
    branch = _run_git(state.repo, ["branch", "--show-current"])
    head = _run_git(state.repo, ["rev-parse", "HEAD"])
    origin = _run_git(state.repo, ["remote", "get-url", "origin"])
    dirty = _run_git(state.repo, ["status", "--porcelain"])
    print(f"repository: {state.repo}")
    print(f"branch:     {branch}")
    print(f"commit:     {head}")
    print(f"origin:     {origin}")
    print(f"worktree:   {'dirty' if dirty else 'clean'}")
    return 0


def command_check(args: argparse.Namespace) -> int:
    state, errors = _load_state(args.repo)
    if state is None or errors:
        _print_errors(errors)
        print(f"\n{len(errors)} health violation(s)", file=sys.stderr)
        return 1
    errors.extend(_validate_projection(state))
    try:
        canonical_remote, _ = _canonical_remote(
            state.repo, state.registry["repository"]["canonical_remote"]
        )
    except HarnessError as exc:
        errors.append(str(exc))
    hooks_path = _run_git(
        state.repo,
        ["config", "--local", "--get", "core.hooksPath"],
        check=False,
    )
    if hooks_path.replace("\\", "/").rstrip("/") != ".githooks":
        errors.append(
            "local append-only hook is not enabled; run the repository bootstrap"
        )
    if errors:
        _print_errors(errors)
        print(f"\n{len(errors)} health violation(s)", file=sys.stderr)
        return 1
    print(
        "OK    registry, namespace lineage, claims, projections, and canonical "
        f"remote '{canonical_remote}' are healthy"
    )
    return 0


def command_sync(args: argparse.Namespace) -> int:
    state = _require_valid_state(args.repo, projection=True)
    dirty = _run_git(state.repo, ["status", "--porcelain"])
    if dirty:
        raise HarnessError("sync refused: checkout has local changes")
    expected = state.registry["repository"]["canonical_remote"]
    canonical_remote, _ = _canonical_remote(state.repo, expected)
    branch = _run_git(state.repo, ["branch", "--show-current"])
    expected_branch = state.registry["repository"]["default_branch"]
    if branch != expected_branch:
        raise HarnessError(
            f"sync refused: expected branch '{expected_branch}', found '{branch}'"
        )
    output = _run_git(
        state.repo,
        ["pull", "--ff-only", canonical_remote, expected_branch],
    )
    if output:
        print(output)
    refreshed_state = _require_valid_state(args.repo, projection=True)
    print(
        f"OK    synced {refreshed_state.registry['repository']['canonical_remote']} "
        f"({expected_branch})"
    )
    return 0


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="aikb",
        description="Git-backed, namespace-aware AI knowledge harness",
    )
    parser.add_argument(
        "--repo",
        type=Path,
        default=_repo_default(),
        help="repository checkout (default: AI_KB_REPO or this script's repository)",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    list_parser = subparsers.add_parser("list", help="list namespaces and health")
    list_parser.set_defaults(handler=command_list)

    index_parser = subparsers.add_parser("index", help="print the generated index")
    index_parser.set_defaults(handler=command_index)

    search_parser = subparsers.add_parser("search", help="search namespace text")
    search_parser.add_argument("query", nargs="+")
    search_parser.add_argument("--namespace")
    search_parser.add_argument(
        "--exact-namespace",
        action="store_true",
        help="do not include specialization ancestors",
    )
    search_parser.add_argument("--ext", action="append")
    search_parser.add_argument("--max", type=int, default=40)
    search_parser.add_argument("--regex", action="store_true")
    search_parser.add_argument("--context", type=int, default=0)
    search_parser.set_defaults(handler=command_search)

    show_parser = subparsers.add_parser("show", help="show a confined knowledge file")
    show_parser.add_argument("path")
    show_parser.add_argument("--start", type=int, default=1)
    show_parser.add_argument("--end", type=int, default=0)
    show_parser.set_defaults(handler=command_show)

    lineage_parser = subparsers.add_parser(
        "lineage", help="show namespace specialization ancestors"
    )
    lineage_parser.add_argument("namespace")
    lineage_parser.set_defaults(handler=command_lineage)

    validate_parser = subparsers.add_parser("validate", help="validate canonical records")
    validate_parser.add_argument(
        "--projection",
        action="store_true",
        help="also require catalog.json and INDEX.md to be current",
    )
    validate_parser.set_defaults(handler=command_validate)

    refresh_parser = subparsers.add_parser("refresh", help="rebuild derived projections")
    refresh_parser.add_argument(
        "--check",
        action="store_true",
        help="write nothing; return non-zero when projections are stale",
    )
    refresh_parser.set_defaults(handler=command_refresh)

    contribute_parser = subparsers.add_parser(
        "contribute",
        help="create an isolated worktree from the canonical remote",
    )
    contribute_parser.add_argument(
        "slug",
        help="short lowercase identifier used in the branch and worktree names",
    )
    contribute_parser.add_argument(
        "--worktree",
        type=Path,
        help="worktree path (default: a sibling of the canonical checkout)",
    )
    contribute_parser.add_argument(
        "--push-remote",
        default="origin",
        help="remote that will receive the contribution branch (default: origin)",
    )
    contribute_parser.set_defaults(handler=command_contribute)

    status_parser = subparsers.add_parser("status", help="show Git provenance")
    status_parser.set_defaults(handler=command_status)

    check_parser = subparsers.add_parser("check", help="run the complete health check")
    check_parser.set_defaults(handler=command_check)

    sync_parser = subparsers.add_parser(
        "sync", help="fast-forward the clean checkout from its canonical remote"
    )
    sync_parser.set_defaults(handler=command_sync)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = _parser()
    args = parser.parse_args(argv)
    args.repo = args.repo.resolve()
    if hasattr(args, "max") and args.max < 1:
        parser.error("--max must be at least 1")
    if hasattr(args, "context") and args.context < 0:
        parser.error("--context must not be negative")
    try:
        return int(args.handler(args))
    except HarnessError as exc:
        print(f"ABSTENTION  {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
