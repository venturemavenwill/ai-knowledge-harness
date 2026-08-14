#!/usr/bin/env python3
"""Reject mutation or deletion of canonical namespace records."""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path
from typing import Sequence

PROTECTED = re.compile(
    r"^namespaces/[^/]+/(?:manifests/[0-9]{4}\.json|claims/[^/]+\.md)$"
)


class GateError(RuntimeError):
    """Append-only gate failure."""


def _repo_default() -> Path:
    return Path(__file__).resolve().parents[1]


def _git(repo: Path, args: Sequence[str]) -> str:
    try:
        completed = subprocess.run(
            ["git", "-C", str(repo), *args],
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
    except FileNotFoundError as exc:
        raise GateError("git was not found on PATH") from exc
    if completed.returncode != 0:
        detail = completed.stderr.strip() or completed.stdout.strip()
        raise GateError(f"git {' '.join(args)} failed: {detail}")
    return completed.stdout


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Ensure existing namespace manifests and claims were not changed"
    )
    parser.add_argument("--repo", type=Path, default=_repo_default())
    parser.add_argument(
        "--base-ref",
        required=True,
        help="merge-base reference, for example origin/main or a base commit SHA",
    )
    return parser


def check(repo: Path, base_ref: str) -> list[str]:
    merge_base = _git(repo, ["merge-base", base_ref, "HEAD"]).strip()
    if not merge_base:
        raise GateError(f"no merge base found for {base_ref}")
    output = _git(
        repo,
        [
            "diff",
            "--name-status",
            "--find-renames",
            f"{merge_base}...HEAD",
            "--",
            "namespaces",
        ],
    )
    violations: list[str] = []
    for line in output.splitlines():
        columns = line.split("\t")
        if len(columns) < 2:
            continue
        status = columns[0]
        paths = columns[1:]
        protected_paths = [path for path in paths if PROTECTED.fullmatch(path)]
        if protected_paths and status != "A":
            violations.append(
                f"{status}: {' -> '.join(protected_paths)} "
                "(canonical records are append-only; add a superseding record)"
            )
    return violations


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        violations = check(args.repo.resolve(), args.base_ref)
    except GateError as exc:
        print(f"FAIL  {exc}", file=sys.stderr)
        return 2
    if violations:
        for violation in violations:
            print(f"FAIL  {violation}", file=sys.stderr)
        print(f"\n{len(violations)} append-only violation(s)", file=sys.stderr)
        return 1
    print("OK    canonical namespace records are additive")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
