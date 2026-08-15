#!/usr/bin/env python3
"""Assert that routing surfaces cover every routable namespace.

The instruction surfaces are hand-maintained while the namespace set is
canonical, so the two drift apart silently: a namespace can be merged with no
route pointing at it, and nothing fails. An agent then never consults knowledge
that exists.

This gate makes that failure automatic instead of dependent on a reviewer
noticing. It reads the current manifest generation directly rather than
catalog.json, so it does not depend on the projection being rebuilt first.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Iterable, Sequence

NAMESPACE_PATTERN = re.compile(r"^[a-z0-9]+(?:[._-][a-z0-9]+)*$")
BACKTICKED = re.compile(r"`([^`]+)`")

# Dotted tokens that are file names rather than namespaces.
NON_NAMESPACE_SUFFIXES = (".json", ".md", ".txt", ".py", ".cff", ".sh", ".ps1")

# Surfaces that must name every routable namespace, and the section each one
# keeps its routing in. Bounding the search to a section keeps unrelated
# backticked prose out of the comparison.
EXHAUSTIVE_SURFACES = (
    ("surfaces/skill/SKILL.md", "## Routing"),
    ("surfaces/vscode/ai-knowledge-base.instructions.md", "Consult:"),
    ("README.md", "## Capabilities available today"),
)

# AGENTS.md blocks are deliberately short: they name a few namespaces and defer
# the rest to `aikb list`. They are checked for that deferral and for typos,
# not for completeness.
PARTIAL_SURFACE = "surfaces/agents/AGENTS-block.md"
DEFERRAL_PHRASE = "the other namespaces listed by `aikb list`"


class RoutingError(RuntimeError):
    """A characterized routing-coverage failure."""


def routable_namespaces(repo: Path) -> set[str]:
    """Namespaces whose current manifest declares when to consult them."""
    root = repo / "namespaces"
    if not root.is_dir():
        raise RoutingError(f"missing namespaces directory: {root}")

    routable: set[str] = set()
    for directory in sorted(p for p in root.iterdir() if p.is_dir()):
        manifests = sorted((directory / "manifests").glob("*.json"))
        if not manifests:
            continue
        current = None
        for path in manifests:
            try:
                record = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                raise RoutingError(f"unreadable manifest: {path}: {exc}") from exc
            if current is None or record.get("generation", 0) > current.get("generation", 0):
                current = record
        if current is None:
            continue
        if current.get("consult_when"):
            routable.add(str(current.get("namespace", directory.name)))
    if not routable:
        raise RoutingError("no routable namespaces found; refusing to pass vacuously")
    return routable


def _section(text: str, heading: str) -> str:
    """Text from a heading up to the next heading, or the end of the file."""
    start = text.find(heading)
    if start == -1:
        raise RoutingError(f"missing section heading: {heading!r}")
    body = text[start + len(heading):]
    end = len(body)
    for marker in ("\n## ", "\n\nUse `aikb", "\n\nRun `aikb", "\n\nSearch before"):
        found = body.find(marker)
        if found != -1:
            end = min(end, found)
    return body[:end]


def _looks_like_namespace(token: str) -> bool:
    if "." not in token or not NAMESPACE_PATTERN.fullmatch(token):
        return False
    return not token.endswith(NON_NAMESPACE_SUFFIXES)


def declared_namespaces(text: str, heading: str) -> set[str]:
    return {
        token
        for token in BACKTICKED.findall(_section(text, heading))
        if _looks_like_namespace(token)
    }


def _read(repo: Path, relative: str) -> str:
    path = repo / relative
    if not path.is_file():
        raise RoutingError(f"missing routing surface: {relative}")
    return path.read_text(encoding="utf-8")


def check(repo: Path) -> list[str]:
    expected = routable_namespaces(repo)
    errors: list[str] = []

    for relative, heading in EXHAUSTIVE_SURFACES:
        declared = declared_namespaces(_read(repo, relative), heading)
        for namespace in sorted(expected - declared):
            errors.append(
                f"{relative}: no route for '{namespace}'; add it under {heading!r}"
            )
        for namespace in sorted(declared - expected):
            errors.append(
                f"{relative}: routes '{namespace}', which is not a routable namespace"
            )

    partial = _read(repo, PARTIAL_SURFACE)
    normalized = " ".join(partial.split())
    if DEFERRAL_PHRASE not in normalized:
        errors.append(
            f"{PARTIAL_SURFACE}: must defer the remaining namespaces with "
            f"{DEFERRAL_PHRASE!r}, otherwise its partial list reads as complete"
        )
    for token in sorted({t for t in BACKTICKED.findall(partial) if _looks_like_namespace(t)}):
        if token not in expected:
            errors.append(
                f"{PARTIAL_SURFACE}: names '{token}', which is not a routable namespace"
            )

    return errors


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Assert routing surfaces cover every routable namespace"
    )
    parser.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[1])
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        errors: Iterable[str] = check(args.repo.resolve())
    except RoutingError as exc:
        print(f"ABSTENTION  {exc}", file=sys.stderr)
        return 2

    errors = list(errors)
    if errors:
        for error in errors:
            print(f"FAIL  {error}", file=sys.stderr)
        print(f"\n{len(errors)} routing coverage violation(s)", file=sys.stderr)
        return 1

    print("OK    every routable namespace is reachable from the routing surfaces")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
