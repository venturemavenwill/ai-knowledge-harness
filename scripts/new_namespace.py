#!/usr/bin/env python3
"""Scaffold an additive knowledge namespace."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Sequence

NAMESPACE_PATTERN = re.compile(r"^[a-z0-9]+(?:[._-][a-z0-9]+)*$")
KINDS = (
    "capability-procedure",
    "design-substrate",
    "empirical-findings",
    "working-discipline",
)
AUTHORITIES = (
    "hand-authored-unmeasured",
    "primary-measurement",
    "reference-only",
)


def _repo_default() -> Path:
    return Path(__file__).resolve().parents[1]


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Create generation 1 of a new append-only knowledge namespace"
    )
    parser.add_argument("namespace")
    parser.add_argument("--repo", type=Path, default=_repo_default())
    parser.add_argument("--title", required=True)
    parser.add_argument("--kind", choices=KINDS, required=True)
    parser.add_argument("--authority", choices=AUTHORITIES, required=True)
    parser.add_argument("--extends")
    parser.add_argument("--consult-when", action="append", required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    repo = args.repo.resolve()
    if not NAMESPACE_PATTERN.fullmatch(args.namespace):
        print(
            "namespace must be lowercase dotted/dashed segments with no path separators",
            file=sys.stderr,
        )
        return 2
    if args.extends and not NAMESPACE_PATTERN.fullmatch(args.extends):
        print("--extends must name a valid namespace", file=sys.stderr)
        return 2
    namespaces_root = repo / "namespaces"
    if not namespaces_root.is_dir():
        print(f"missing namespaces directory: {namespaces_root}", file=sys.stderr)
        return 2
    if args.extends and not (namespaces_root / args.extends / "manifests").is_dir():
        print(f"parent namespace does not exist: {args.extends}", file=sys.stderr)
        return 2

    target = namespaces_root / args.namespace
    if target.exists():
        print(f"namespace already exists: {target}", file=sys.stderr)
        return 2
    manifests = target / "manifests"
    claims = target / "claims"
    manifests.mkdir(parents=True)
    claims.mkdir()
    (claims / ".gitkeep").write_text("", encoding="utf-8")
    manifest = {
        "$schema": "../../../schema/namespace-manifest.schema.json",
        "schema_version": 1,
        "namespace": args.namespace,
        "generation": 1,
        "supersedes": None,
        "title": args.title,
        "kind": args.kind,
        "authority": args.authority,
        "extends": args.extends,
        "consult_when": args.consult_when,
        "entry_points": [],
        "search_paths": ["claims"],
    }
    manifest_path = manifests / "0001.json"
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=True, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(f"created {manifest_path}")
    print(f"created {claims}")
    print("next:")
    print(f"  1. copy templates/claim.md into {claims}")
    print("  2. replace every placeholder and add the claim path to entry_points")
    print("  3. run: python bin/aikb.py validate")
    print("  4. run: python bin/aikb.py refresh")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
