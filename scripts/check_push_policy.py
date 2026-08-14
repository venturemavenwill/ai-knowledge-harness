#!/usr/bin/env python3
"""Reject direct pushes to the harness default branch."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Sequence, TextIO

OID_PATTERN = re.compile(r"^(?:[0-9a-fA-F]{40}|[0-9a-fA-F]{64})$")


def _repo_default() -> Path:
    return Path(__file__).resolve().parents[1]


def _default_branch(repo: Path) -> str:
    registry_path = repo / "registry.json"
    try:
        registry = json.loads(registry_path.read_text(encoding="utf-8"))
        branch = registry["repository"]["default_branch"]
    except (FileNotFoundError, json.JSONDecodeError, KeyError, TypeError) as exc:
        raise ValueError(f"cannot read the default branch from {registry_path}") from exc
    if not isinstance(branch, str) or not branch:
        raise ValueError(f"invalid default branch in {registry_path}")
    return branch


def check_updates(stream: TextIO, default_branch: str) -> list[str]:
    protected_ref = f"refs/heads/{default_branch}"
    errors: list[str] = []
    for line_number, raw_line in enumerate(stream, start=1):
        line = raw_line.strip()
        if not line:
            continue
        fields = line.split()
        if len(fields) != 4:
            errors.append(f"malformed pre-push input at line {line_number}")
            continue
        local_ref, local_oid, remote_ref, remote_oid = fields
        valid_local_ref = local_ref == "(delete)" or local_ref.startswith("refs/")
        if (
            not valid_local_ref
            or not remote_ref.startswith("refs/")
            or not OID_PATTERN.fullmatch(local_oid)
            or not OID_PATTERN.fullmatch(remote_oid)
        ):
            errors.append(f"malformed pre-push input at line {line_number}")
            continue
        if remote_ref == protected_ref:
            action = "delete" if local_ref == "(delete)" else "update"
            errors.append(
                f"direct {action} of {protected_ref} is not allowed; "
                "push an improvement branch and merge it through a pull request"
            )
    return errors


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=_repo_default())
    args = parser.parse_args(argv)
    try:
        default_branch = _default_branch(args.repo.resolve())
    except ValueError as exc:
        print(f"BLOCKED  {exc}", file=sys.stderr)
        return 2

    errors = check_updates(sys.stdin, default_branch)
    if errors:
        for error in errors:
            print(f"BLOCKED  {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
