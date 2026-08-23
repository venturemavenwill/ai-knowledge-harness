#!/usr/bin/env python3
"""Scaffold an append-only claim inside an existing namespace.

Adding a claim is the most common capture action and the easiest one to get
wrong. The metadata header has thirteen required keys, the filename must equal
``<claim_id>--<version>.md``, canonical text must be LF-only, and the claim has
to be reachable from the namespace manifest's ``entry_points``.

That last step is the trap. Manifests are append-only once committed, so a
claim added to an established namespace needs a *new manifest generation* that
supersedes the current one -- editing the existing file in place corrupts the
canonical record. This script decides which of those two paths applies and
takes it, rather than leaving an agent to rediscover the rule.

The emitted body deliberately retains unresolved placeholders so that
``aikb validate`` fails until a human or agent writes the actual knowledge. A
scaffold must not be able to masquerade as a finished claim.
"""

from __future__ import annotations

import argparse
import datetime as _datetime
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

IDENTIFIER_PATTERN = re.compile(r"^[a-z0-9]+(?:[._-][a-z0-9]+)*$")
SEMVER_PATTERN = re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+$")
PARENT_REF_PATTERN = re.compile(r"^[a-z0-9]+(?:[._-][a-z0-9]+)*@[0-9]+\.[0-9]+\.[0-9]+$")

AUTHORITIES = ("hand-authored", "primary-measurement", "reference-only")
EVIDENCE_CLASSES = (
    "primary-result",
    "reported-summary",
    "design-reference",
    "operator-authored",
)

# Kept in sync with the validator, which rejects a body still containing any of
# these. The scaffold uses them on purpose.
UNRESOLVED = "Replace with"


class ScaffoldError(RuntimeError):
    """A characterized scaffolding failure."""


def _repo_default() -> Path:
    return Path(__file__).resolve().parents[1]


def _write_canonical(path: Path, text: str) -> None:
    """Write UTF-8 with LF endings and exactly one trailing newline."""
    body = text.replace("\r\n", "\n").replace("\r", "\n").rstrip("\n") + "\n"
    path.write_text(body, encoding="utf-8", newline="\n")


def _load_manifests(namespace_dir: Path) -> List[Path]:
    manifests = sorted((namespace_dir / "manifests").glob("*.json"))
    if not manifests:
        raise ScaffoldError(f"namespace has no manifests: {namespace_dir}")
    return manifests


def _active_manifest(manifests: Sequence[Path]) -> tuple:
    active_path: Optional[Path] = None
    active: Optional[Dict[str, Any]] = None
    for path in manifests:
        try:
            record = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ScaffoldError(f"unreadable manifest: {path}: {exc}") from exc
        if active is None or record.get("generation", 0) > active.get("generation", 0):
            active_path, active = path, record
    if active is None or active_path is None:
        raise ScaffoldError("no readable manifest generation found")
    return active_path, active


def _git(repo: Path, args: Sequence[str]) -> Optional[str]:
    """Run a read-only Git command, returning None when it cannot answer."""
    try:
        completed = subprocess.run(
            ["git", *args],
            cwd=str(repo),
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            check=False,
        )
    except (OSError, ValueError):
        return None
    if completed.returncode != 0:
        return None
    return completed.stdout.decode("utf-8", "replace").strip()


def _is_tracked(repo: Path, path: Path) -> bool:
    """True when the path exists in HEAD, i.e. the record is already canonical.

    Three states must stay distinct, because ``git cat-file`` reports the last
    two identically:

    * the file is in HEAD -- committed, so the manifest is append-only;
    * the repository has no HEAD yet -- provably nothing is committed;
    * Git cannot answer at all -- no Git, no repository, or a *different*
      enclosing repository whose HEAD says nothing about this tree.

    Only the middle case permits an in-place edit. The last case is unprovable
    and fails closed to the superseding-generation path, which is always safe.
    """
    try:
        relative = path.resolve().relative_to(repo.resolve()).as_posix()
    except ValueError:
        return True

    toplevel = _git(repo, ["rev-parse", "--show-toplevel"])
    if toplevel is None:
        return True
    try:
        if Path(toplevel).resolve() != repo.resolve():
            return True
    except OSError:
        return True

    if _git(repo, ["rev-parse", "--verify", "HEAD"]) is None:
        return False

    return _git(repo, ["cat-file", "-e", "HEAD:{0}".format(relative)]) is not None


def _claim_metadata(args: argparse.Namespace, evidence: List[Dict[str, str]]) -> Dict[str, Any]:
    return {
        "schema_version": 1,
        "claim_id": args.claim_id,
        "namespace": args.namespace,
        "version": args.version,
        "expression": args.expression,
        "authority": args.authority,
        "scope": {"holds_when": args.holds_when, "expires": args.expires},
        "confidence": args.confidence,
        "confidence_method": args.confidence_method,
        "provenance": {
            "producer": args.producer,
            "producer_version": "1.0.0",
            "authored_utc": args.authored,
            "derived_from": evidence,
        },
        "lineage": {
            "status": "active",
            "generation": args.generation,
            "parent_refs": list(args.parent_ref or []),
        },
        "relationships": [],
        "retrieval": {"tags": sorted(set(args.tag))},
    }


def _render_claim(metadata: Dict[str, Any], title: str, procedure_kind: bool) -> str:
    header = json.dumps(metadata, ensure_ascii=True, indent=2)
    falsifier = (
        "\n**Falsified if:** {0} a concrete observation that would refute this "
        "claim.\n".format(UNRESOLVED.lower())
        if procedure_kind
        else ""
    )
    return (
        "<!-- aikb\n"
        + header
        + "\n-->\n\n"
        + "# {0}\n\n".format(title)
        + "{0} the retained source, procedure, or finding. State it directly "
        "instead of\ndepending on a summary that exists only in another "
        "agent's context.\n\n".format(UNRESOLVED)
        + "## Activation\n\n"
        + "{0} the precise conditions under which this should and should not "
        "be\nconsulted.\n\n".format(UNRESOLVED)
        + "## Procedure or finding\n\n"
        + "{0} the full knowledge, including scope and known limitations.\n\n".format(UNRESOLVED)
        + "## Verification\n\n"
        + "{0} an executable check that could establish whether this is "
        "load-bearing.\n".format(UNRESOLVED)
        + falsifier
    )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Scaffold an append-only claim inside an existing namespace"
    )
    parser.add_argument("claim_id")
    parser.add_argument("--repo", type=Path, default=_repo_default())
    parser.add_argument("--namespace", required=True)
    parser.add_argument("--title", required=True)
    parser.add_argument(
        "--expression",
        required=True,
        help="one falsifiable sentence stating the claim",
    )
    parser.add_argument(
        "--holds-when",
        required=True,
        help="the precise activation scope for the claim",
    )
    parser.add_argument("--expires", default=None)
    parser.add_argument("--authority", choices=AUTHORITIES, default="hand-authored")
    parser.add_argument("--version", default="1.0.0")
    parser.add_argument("--generation", type=int, default=1)
    parser.add_argument("--parent-ref", action="append")
    parser.add_argument("--tag", action="append", required=True)
    parser.add_argument("--producer", default="hand-authored://operator")
    parser.add_argument("--confidence", type=float, default=None)
    parser.add_argument("--confidence-method")
    parser.add_argument("--authored", help="authoring date as YYYY-MM-DD (default: today, UTC)")
    parser.add_argument(
        "--evidence",
        nargs=3,
        action="append",
        metavar=("SOURCE", "LOCATOR", "CLASS"),
        help="retained evidence; CLASS is one of {0}".format(", ".join(EVIDENCE_CLASSES)),
    )
    parser.add_argument(
        "--no-entry-point",
        action="store_true",
        help="write the claim without making it reachable from the manifest",
    )
    return parser


def _validate_args(args: argparse.Namespace) -> List[Dict[str, str]]:
    if not IDENTIFIER_PATTERN.fullmatch(args.claim_id):
        raise ScaffoldError("claim id must be lowercase dotted/dashed segments")
    if not IDENTIFIER_PATTERN.fullmatch(args.namespace):
        raise ScaffoldError("--namespace must name a valid namespace")
    if not SEMVER_PATTERN.fullmatch(args.version):
        raise ScaffoldError("--version must be semantic x.y.z")
    if args.generation < 1:
        raise ScaffoldError("--generation must be a positive integer")
    for ref in args.parent_ref or []:
        if not PARENT_REF_PATTERN.fullmatch(ref):
            raise ScaffoldError("--parent-ref must look like claim.id@1.0.0, got {0!r}".format(ref))
    for tag in args.tag:
        if not IDENTIFIER_PATTERN.fullmatch(tag):
            raise ScaffoldError("--tag must be lowercase dotted/dashed segments, got {0!r}".format(tag))

    if args.authority == "hand-authored":
        if args.confidence is not None:
            raise ScaffoldError("hand-authored claims must not carry a numeric confidence")
        if args.confidence_method is None:
            args.confidence_method = "hand-authored-unmeasured"
        if not args.confidence_method.endswith("unmeasured"):
            raise ScaffoldError("hand-authored claims require an unmeasured confidence method")
    elif not args.confidence_method:
        raise ScaffoldError(
            "--confidence-method is required for {0} claims".format(args.authority)
        )

    if args.confidence is not None and not 0 <= args.confidence <= 1:
        raise ScaffoldError("--confidence must fall within [0, 1]")

    if args.authored is None:
        args.authored = _datetime.datetime.now(_datetime.timezone.utc).strftime("%Y-%m-%d")
    elif not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", args.authored):
        raise ScaffoldError("--authored must be YYYY-MM-DD")

    evidence: List[Dict[str, str]] = []
    for source, locator, evidence_class in args.evidence or []:
        if evidence_class not in EVIDENCE_CLASSES:
            raise ScaffoldError(
                "evidence class {0!r} must be one of {1}".format(
                    evidence_class, ", ".join(EVIDENCE_CLASSES)
                )
            )
        evidence.append(
            {"source": source, "locator": locator, "evidence_class": evidence_class}
        )
    if not evidence:
        raise ScaffoldError(
            "at least one --evidence SOURCE LOCATOR CLASS is required; a claim "
            "without retained evidence cannot be reviewed"
        )
    return evidence


def _register_entry_point(
    repo: Path,
    namespace_dir: Path,
    manifests: Sequence[Path],
    relative_claim: str,
) -> str:
    active_path, active = _active_manifest(manifests)
    entry_points = list(active.get("entry_points") or [])
    if relative_claim in entry_points:
        return "already reachable from {0}".format(active_path.name)
    entry_points = sorted(entry_points + [relative_claim])

    if not _is_tracked(repo, active_path):
        active["entry_points"] = entry_points
        _write_canonical(active_path, json.dumps(active, ensure_ascii=True, indent=2))
        return "updated uncommitted manifest {0}".format(active_path.name)

    generation = int(active.get("generation", 0)) + 1
    successor = dict(active)
    successor["generation"] = generation
    successor["supersedes"] = "manifests/{0}".format(active_path.name)
    successor["entry_points"] = entry_points
    successor_path = namespace_dir / "manifests" / "{0:04d}.json".format(generation)
    if successor_path.exists():
        raise ScaffoldError("manifest generation already exists: {0}".format(successor_path))
    _write_canonical(successor_path, json.dumps(successor, ensure_ascii=True, indent=2))
    return "added manifest generation {0} superseding {1}".format(
        successor_path.name, active_path.name
    )


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = _parser().parse_args(argv)
    repo = args.repo.resolve()
    try:
        evidence = _validate_args(args)

        namespace_dir = repo / "namespaces" / args.namespace
        if not (namespace_dir / "manifests").is_dir():
            raise ScaffoldError(
                "namespace does not exist: {0}; create it with "
                "scripts/new_namespace.py".format(args.namespace)
            )
        manifests = _load_manifests(namespace_dir)
        _, active = _active_manifest(manifests)

        claims_dir = namespace_dir / "claims"
        claims_dir.mkdir(exist_ok=True)
        claim_path = claims_dir / "{0}--{1}.md".format(args.claim_id, args.version)
        if claim_path.exists():
            raise ScaffoldError(
                "claim already exists and records are append-only: {0}; publish a "
                "new version instead".format(claim_path)
            )

        metadata = _claim_metadata(args, evidence)
        procedure_kind = active.get("kind") == "capability-procedure"
        _write_canonical(claim_path, _render_claim(metadata, args.title, procedure_kind))
        print("created {0}".format(claim_path))

        if args.no_entry_point:
            note = "manifest untouched; the claim is not reachable yet"
        else:
            note = _register_entry_point(
                repo, namespace_dir, manifests, "claims/{0}".format(claim_path.name)
            )
        print("manifest: {0}".format(note))
    except ScaffoldError as exc:
        print("ABSTENTION  {0}".format(exc), file=sys.stderr)
        return 2

    print("next:")
    print("  1. write the claim body; validation fails while placeholders remain")
    print("  2. run: python bin/aikb.py validate")
    print("  3. run: python bin/aikb.py refresh")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
