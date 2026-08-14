#!/usr/bin/env python3
"""Reject mutation or deletion of canonical namespace records."""

from __future__ import annotations

import argparse
import json
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


def _normalize_remote(remote: str) -> str:
    value = remote.strip().rstrip("/")
    ssh_match = re.fullmatch(r"git@github\.com:(.+)", value)
    if ssh_match:
        value = f"https://github.com/{ssh_match.group(1)}"
    ssh_url_match = re.fullmatch(r"ssh://git@github\.com/(.+)", value)
    if ssh_url_match:
        value = f"https://github.com/{ssh_url_match.group(1)}"
    return value.removesuffix(".git").rstrip("/").lower()


def _canonical_base(repo: Path) -> str:
    registry_path = repo / "registry.json"
    try:
        registry = json.loads(registry_path.read_text(encoding="utf-8"))
        expected = registry["repository"]["canonical_remote"]
        default_branch = registry["repository"]["default_branch"]
    except (FileNotFoundError, json.JSONDecodeError, KeyError, TypeError) as exc:
        raise GateError(f"cannot read canonical repository data from {registry_path}") from exc
    if not isinstance(expected, str) or not isinstance(default_branch, str):
        raise GateError(f"invalid canonical repository data in {registry_path}")

    matches: list[str] = []
    for remote in _git(repo, ["remote"]).splitlines():
        url = _git(repo, ["remote", "get-url", remote])
        if _normalize_remote(url) == _normalize_remote(expected):
            matches.append(remote)
    if not matches:
        raise GateError(f"no configured remote matches {expected}")

    priority = {"origin": 0, "upstream": 1}
    remote = min(matches, key=lambda name: (priority.get(name, 2), name))
    base_ref = f"{remote}/{default_branch}"
    _git(repo, ["rev-parse", "--verify", base_ref])
    return base_ref


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Ensure existing namespace manifests and claims were not changed"
    )
    parser.add_argument("--repo", type=Path, default=_repo_default())
    parser.add_argument(
        "--base-ref",
        help=(
            "merge-base reference, for example origin/main or a base commit SHA; "
            "defaults to the configured canonical remote and branch"
        ),
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
        repo = args.repo.resolve()
        base_ref = args.base_ref or _canonical_base(repo)
        violations = check(repo, base_ref)
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
