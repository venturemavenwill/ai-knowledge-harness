#!/usr/bin/env python3
"""Opt-in local capture and reviewed, resumable knowledge contributions."""

from __future__ import annotations

import argparse
import contextlib
import datetime
import hashlib
import io
import importlib.util
import json
import os
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

TRIGGERS = ("interaction", "verified", "correction", "workaround", "abandoned")
FIELDS = {
    "trigger", "namespace", "title", "expression", "scope", "procedure",
    "verification", "uncertainty", "evidence", "search_terms",
}
MAX_INPUT = 24000
MAX_CANDIDATES = 1000
ID = re.compile(r"^[0-9a-f]{24}$")
TRAILER = "Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"


class LearningError(RuntimeError):
    """A visible, characterized learning failure."""


def canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=True, indent=2, sort_keys=True) + "\n"


def digest(value: Any) -> str:
    return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()


def now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def atomic(path: Path, text: str, *, encoding: str = "utf-8") -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd, temporary = tempfile.mkstemp(prefix=".aikb-", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding=encoding, newline="\n") as stream:
            stream.write(text)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def checked(
    argv: list[str], cwd: Path, *, input_text: str | None = None, strip: bool = True,
    env: dict[str, str] | None = None,
) -> str:
    try:
        result = subprocess.run(
            argv, cwd=str(cwd), input=input_text, text=True, encoding="utf-8",
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=180, env=env,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise LearningError(f"{argv[0]} could not complete: {type(exc).__name__}") from exc
    if result.returncode:
        raise LearningError(
            f"{argv[0]} failed ({result.returncode}): {result.stderr.strip()[:2000]}"
        )
    return result.stdout.strip() if strip else result.stdout


class Store:
    def __init__(self, root: Path):
        self.root = root
        self.path = root / "inbox.json"

    def read(self) -> dict[str, Any]:
        if not self.path.exists():
            return {
                "version": 1,
                "config": {"capture": False, "publish": False, "push_remote": "origin"},
                "checkpoints": {}, "candidates": {}, "last_run": None,
            }
        data = json.loads(self.path.read_text(encoding="utf-8"))
        if not isinstance(data, dict) or data.get("version") != 1:
            raise LearningError("unsupported learning inbox; preserved without changes")
        if not all(key in data for key in ("config", "checkpoints", "candidates", "last_run")):
            raise LearningError("incomplete learning inbox; preserved without changes")
        config = data["config"]
        if (
            not isinstance(config, dict)
            or any(type(config.get(key)) is not bool for key in ("capture", "publish"))
            or not isinstance(config.get("push_remote"), str)
            or not isinstance(data["checkpoints"], dict)
            or not isinstance(data["candidates"], dict)
        ):
            raise LearningError("invalid learning inbox structure; preserved without changes")
        statuses = {"pending", "preparing", "prepared", "approved", "submitted",
                    "rejected", "merged", "closed"}
        for identifier, item in data["candidates"].items():
            if (
                not isinstance(identifier, str) or not ID.fullmatch(identifier)
                or not isinstance(item, dict) or not isinstance(item.get("status"), str)
                or item["status"] not in statuses
                or not isinstance(item.get("value"), dict) or set(item["value"]) != FIELDS
                or not isinstance(item.get("created"), str)
                or type(item.get("seen")) is not int or item["seen"] < 0
            ):
                raise LearningError("invalid candidate record; inbox preserved without changes")
        if any(type(count) is not int or count < 0 for count in data["checkpoints"].values()):
            raise LearningError("invalid checkpoint counters; inbox preserved without changes")
        return data

    def save(self, data: dict[str, Any]) -> None:
        atomic(self.path, canonical(data))

    @contextlib.contextmanager
    def locked(self, wait_seconds: float = 0):
        self.root.mkdir(parents=True, exist_ok=True, mode=0o700)
        with (self.root / "worker.lock").open("a+b") as stream:
            if stream.seek(0, 2) == 0:
                stream.write(b"0")
                stream.flush()
            stream.seek(0)
            deadline = time.monotonic() + wait_seconds
            while True:
                try:
                    if os.name == "nt":
                        import msvcrt
                        msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
                    else:
                        import fcntl
                        fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                    break
                except OSError as exc:
                    if time.monotonic() >= deadline:
                        raise LearningError("learning inbox busy; retry after the active operation") from exc
                    time.sleep(0.1)
            try:
                yield
            finally:
                stream.seek(0)
                if os.name == "nt":
                    import msvcrt
                    msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
                else:
                    import fcntl
                    fcntl.flock(stream.fileno(), fcntl.LOCK_UN)


class Workflow:
    def __init__(self, repo: Path, root: Path, api: Any):
        self.repo = repo
        self.store = Store(root)
        self.api = api

    def git(self, *args: str, cwd: Path | None = None) -> str:
        return checked(["git", *args], cwd or self.repo)

    def gh(self, *args: str) -> str:
        return checked(["gh", *args], self.repo)

    def candidate(self, data: dict[str, Any], identifier: str) -> dict[str, Any]:
        if not ID.fullmatch(identifier):
            raise LearningError("candidate id must be 24 lowercase hexadecimal characters")
        if identifier not in data["candidates"]:
            raise LearningError("unknown candidate")
        item = data["candidates"][identifier]
        if digest(item["value"])[:24] != identifier:
            raise LearningError("candidate summary changed; capture a revised candidate instead")
        return item

    def clean_text(self, text: str) -> None:
        cleaned, counts = self.api._load_sanitizer(self.repo).sanitize_text(text)
        if cleaned != text:
            finding = "tag-character finding; report to the operator" if counts["tag"] else "hidden characters"
            raise LearningError(f"{finding}; correct the input before capture or publication")
        if any(ord(char) < 32 and char not in "\n\t" for char in text):
            raise LearningError("control characters are not permitted")

    def validate_candidate(self, value: Any) -> dict[str, str]:
        if not isinstance(value, dict) or set(value) != FIELDS:
            raise LearningError("candidate must contain exactly: " + ", ".join(sorted(FIELDS)))
        if len(canonical(value).encode("utf-8")) > MAX_INPUT:
            raise LearningError("candidate exceeds 24000 bytes")
        if any(not isinstance(v, str) or not v.strip() for v in value.values()):
            raise LearningError("every candidate field must be a nonempty string")
        value = {key: text.strip().replace("\r\n", "\n") for key, text in value.items()}
        self.clean_text("\n".join(value.values()))
        if value["trigger"] not in TRIGGERS:
            raise LearningError("unknown capture trigger")
        if not self.api.NAMESPACE_PATTERN.fullmatch(value["namespace"]):
            raise LearningError("invalid namespace")
        if len(value["title"]) > 120 or "\n" in value["title"]:
            raise LearningError("title must be one line, at most 120 characters")
        if len(value["search_terms"]) > 200:
            raise LearningError("search_terms must be at most 200 characters")
        state = self.api._require_valid_state(self.repo, projection=True)
        if value["namespace"] not in state.by_namespace():
            raise LearningError("namespace does not exist; use a reviewed manual contribution")
        return value

    def configure(self, capture: str | None, publish: str | None, remote: str | None):
        with self.store.locked():
            data = self.store.read()
            config = data["config"]
            if remote is not None:
                if not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9_.-]{0,63}", remote):
                    raise LearningError("invalid push remote name")
                self.git("remote", "get-url", remote)
                config["push_remote"] = remote
            for key, value in (("capture", capture), ("publish", publish)):
                if value is not None:
                    config[key] = value == "on"
            self.store.save(data)
            return config

    def capture(self, value: Any = None, nothing: str | None = None) -> str:
        with self.store.locked():
            data = self.store.read()
            if not data["config"]["capture"]:
                raise LearningError("local capture disabled; enable with learn configure --capture on")
            if nothing:
                if nothing not in TRIGGERS:
                    raise LearningError("unknown checkpoint")
                key = f"{nothing}:nothing"
                data["checkpoints"][key] = data["checkpoints"].get(key, 0) + 1
                self.store.save(data)
                return "nothing durable; checkpoint counted locally"
            value = self.validate_candidate(value)
            identifier = digest(value)[:24]
            if identifier not in data["candidates"]:
                if len(data["candidates"]) >= MAX_CANDIDATES:
                    raise LearningError("inbox full (1000 candidates); run learn archive for terminal records")
                data["candidates"][identifier] = {
                    "value": value, "created": now(), "status": "pending",
                    "seen": 0, "error": None,
                }
            item = data["candidates"][identifier]
            item["seen"] += 1
            key = f"{value['trigger']}:candidate"
            data["checkpoints"][key] = data["checkpoints"].get(key, 0) + 1
            self.store.save(data)
            return identifier

    def destination(self, data: dict[str, Any]) -> dict[str, str]:
        state = self.api._require_valid_state(self.repo, projection=True)
        repository = state.registry["repository"]
        expected = repository["canonical_remote"]
        self.api._canonical_remote(self.repo, expected)
        target = self.api._github_repository(expected)
        push = self.git("remote", "get-url", "--push", data["config"]["push_remote"])
        fork = self.api._github_repository(push)
        if not target or not fork:
            raise LearningError("publication requires GitHub canonical and push remotes")
        if any(not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", name)
               for name in (target, fork)):
            raise LearningError("publication requires an unambiguous owner/repository destination")
        # Tokens embedded in HTTPS remotes must never enter review packages or logs.
        if "://" in push and "@" in push.split("://", 1)[1]:
            raise LearningError("credential-bearing push URLs are not permitted")
        return {
            "repository": target, "push_repository": fork, "push_url": push,
            "push_remote": data["config"]["push_remote"],
            "base": repository["default_branch"],
        }

    def canonical_head(self, destination: dict[str, str]) -> str:
        state = self.api._require_valid_state(self.repo, projection=True)
        remote, _ = self.api._canonical_remote(
            self.repo, state.registry["repository"]["canonical_remote"]
        )
        result = self.git("ls-remote", "--exit-code", remote,
                          f"refs/heads/{destination['base']}").split()
        if len(result) != 2 or not re.fullmatch(r"[0-9a-f]{40,64}", result[0]):
            raise LearningError("canonical default-branch identity could not be verified")
        return result[0]

    def build(self, data: dict[str, Any], identifier: str) -> dict[str, Any]:
        item = self.candidate(data, identifier)
        value = self.validate_candidate(item["value"])
        destination = self.destination(data)
        if self.git("status", "--porcelain"):
            raise LearningError("prepare requires a clean canonical checkout")
        if self.git("branch", "--show-current") != destination["base"]:
            raise LearningError("prepare requires the canonical default-branch checkout")
        if self.git("rev-parse", "HEAD") != self.canonical_head(destination):
            raise LearningError("checkout differs from canonical main; review updates before preparing")
        if item["status"] in ("submitted", "merged", "closed"):
            raise LearningError("candidate already submitted; use status or reconcile")
        state = self.api._require_valid_state(self.repo, projection=True)
        normalized = " ".join(value["expression"].lower().split())
        for namespace in state.namespaces:
            for claim in namespace.claims:
                if " ".join(claim.data["expression"].lower().split()) == normalized:
                    raise LearningError(f"duplicate canonical expression: {claim.ref}")
        matches = []
        terms = value["search_terms"].lower().split()
        for namespace in state.namespaces:
            for claim in namespace.claims:
                if any(term in claim.data["expression"].lower() for term in terms):
                    matches.append(claim.ref)
        attempt = item.get("attempt", 0) + 1
        worktree = self.store.root / "worktrees" / f"{identifier}-{attempt}"
        branch = f"improvement/learning-{identifier}-{attempt}"
        item.pop("approval", None)
        item.pop("package", None)
        item.pop("commit", None)
        item["attempt"] = attempt
        item.update(worktree=str(worktree), branch=branch, base_commit=self.git("rev-parse", "HEAD"))
        # Persist identity before creation. An interrupted preparation is visible and
        # is never reconstructed by deleting or overwriting the operator's work.
        item["status"] = "preparing"
        self.store.save(data)
        self.git("worktree", "add", "-b", branch, str(worktree), item["base_commit"])
        namespace = state.by_namespace()[value["namespace"]]
        claim_id = f"method.learning.{identifier}"
        relative = f"namespaces/{value['namespace']}/claims/{claim_id}--1.0.0.md"
        metadata = {
            "schema_version": 1, "claim_id": claim_id, "namespace": value["namespace"],
            "version": "1.0.0", "expression": value["expression"], "authority": "hand-authored",
            "scope": {"holds_when": value["scope"], "expires": None},
            "confidence": None, "confidence_method": "assistant-proposed-unmeasured",
            "provenance": {
                "producer": "assistant-assessment://reviewed-learning",
                "producer_version": "1.0.0", "authored_utc": item["created"][:10],
                "derived_from": [{
                    "source": "reviewed learning summary", "locator": value["evidence"],
                    "evidence_class": "reported-summary",
                }],
            },
            "lineage": {"status": "active", "generation": 1, "parent_refs": []},
            "relationships": [], "retrieval": {"tags": ["reviewed-learning"]},
        }
        text = "<!-- aikb\n" + canonical(metadata) + "-->\n\n# " + value["title"] + "\n\n"
        for heading, key in (("Activation", "scope"), ("Procedure", "procedure"),
                             ("Verification", "verification"), ("Limitations", "uncertainty")):
            text += f"## {heading}\n\n{value[key]}\n\n"
        text += "**Falsified if:** the stated verification contradicts the procedure.\n"
        atomic(worktree / relative, text)
        scaffold_path = self.repo / "scripts" / "new_claim.py"
        spec = importlib.util.spec_from_file_location("aikb_learning_scaffold", scaffold_path)
        if spec is None or spec.loader is None:
            raise LearningError("claim scaffold helper could not be loaded")
        scaffold = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(scaffold)
        namespace_dir = worktree / "namespaces" / value["namespace"]
        try:
            scaffold._register_entry_point(
                worktree, namespace_dir, scaffold._load_manifests(namespace_dir),
                f"claims/{claim_id}--1.0.0.md",
            )
        except scaffold.ScaffoldError as exc:
            raise LearningError(f"claim entry-point preparation failed: {exc}") from exc
        generation = namespace.active.data["generation"] + 1
        manifest_path = f"namespaces/{value['namespace']}/manifests/{generation:04d}.json"
        with contextlib.redirect_stdout(io.StringIO()):
            self.api.command_refresh(argparse.Namespace(repo=worktree, check=False))
        self.api._require_valid_state(worktree, projection=True)
        # refresh also considers surfaces: never admit installed or executable
        # content to a periodic learning submission.
        files = {
            name: (worktree / name).read_text(encoding="utf-8")
            for name in (relative, manifest_path, "INDEX.md", "catalog.json")
        }
        title = "Learning: " + value["title"]
        body = (
            "## Reusable lesson\n\n" + value["expression"] + "\n\n"
            "## Evidence and limitations\n\n" + value["evidence"] + "\n\n"
            + value["uncertainty"] + "\n\n"
            "Assistant-proposed, unmeasured; retained summary is not a primary measurement.\n"
            "The submitter approved the exact content and destination for public disclosure.\n"
            "Maintainer review and required CI remain mandatory; no automatic merge is requested.\n\n"
            "## Existing knowledge considered\n\n" + (", ".join(matches[:30]) or "No lexical matches.")
            + "\n\nAI assistance: structured capture and deterministic contribution preparation.\n"
        )
        package = {
            "candidate": identifier, "destination": destination, "branch": branch,
            "base_commit": item["base_commit"], "files": files, "title": title, "body": body,
            "commit_message": title + "\n\n" + TRAILER + "\n",
            "author_ident": self.git("var", "GIT_AUTHOR_IDENT"),
            "committer_ident": self.git("var", "GIT_COMMITTER_IDENT"),
        }
        for text in [*files.values(), title, body, package["commit_message"],
                     package["author_ident"], package["committer_ident"]]:
            self.clean_text(text)
        item.update(package=package, status="prepared", error=None)
        self.store.save(data)
        return package

    def verify_package(self, data: dict[str, Any], item: dict[str, Any]) -> dict[str, Any]:
        package = item.get("package")
        required = {"candidate", "destination", "branch", "base_commit", "files",
                    "title", "body", "commit_message", "author_ident", "committer_ident"}
        if (
            not isinstance(package, dict) or set(package) != required
            or not isinstance(package.get("files"), dict)
            or any(not isinstance(key, str) or not isinstance(text, str)
                   for key, text in package.get("files", {}).items())
            or any(not isinstance(package.get(key), str)
                   for key in required - {"files", "destination"})
        ):
            raise LearningError("candidate has no complete review package")
        identifier = digest(item["value"])[:24]
        if (
            package["candidate"] != identifier
            or not re.fullmatch(rf"improvement/learning-{identifier}-[1-9][0-9]*", package["branch"])
        ):
            raise LearningError("review package has an invalid contribution identity")
        if package["destination"] != self.destination(data):
            raise LearningError("publication destination changed; reject and prepare a new candidate")
        worktree = Path(item["worktree"])
        if self.git("branch", "--show-current", cwd=worktree) != package["branch"]:
            raise LearningError("prepared branch changed")
        allowed = set(package["files"])
        namespace = item["value"]["namespace"]
        expected_claim = f"namespaces/{namespace}/claims/method.learning.{package['candidate']}--1.0.0.md"
        expected_manifest = re.compile(
            rf"^namespaces/{re.escape(namespace)}/manifests/[0-9]{{4,}}\.json$"
        )
        if (
            len(allowed) != 4 or expected_claim not in allowed
            or not {"INDEX.md", "catalog.json"}.issubset(allowed)
            or len([p for p in allowed if expected_manifest.fullmatch(p)]) != 1
        ):
            raise LearningError("review package contains non-knowledge paths")
        for name, expected in package["files"].items():
            path = worktree / name
            if path.is_symlink() or not self.api._inside(path.resolve(), worktree.resolve()):
                raise LearningError("prepared file escapes the contribution worktree")
            if path.read_bytes() != expected.encode("utf-8"):
                raise LearningError("prepared content changed; approval invalid")
            self.clean_text(expected)
        record = self.api._extract_claim(worktree / expected_claim)
        if (
            record.data["authority"] != "hand-authored" or record.data["confidence"] is not None
            or any(source["evidence_class"] != "reported-summary"
                   for source in record.data["provenance"]["derived_from"])
        ):
            raise LearningError("periodic learning must remain an unmeasured summary proposal")
        changed = set(self.git("diff", "--name-only", package["base_commit"], cwd=worktree).splitlines())
        untracked = set(self.git("ls-files", "--others", "--exclude-standard", cwd=worktree).splitlines())
        if not changed.union(untracked).issubset(allowed):
            raise LearningError("contribution contains unreviewed changes")
        self.api._require_valid_state(worktree, projection=True)
        return package

    def preview(self, identifier: str, refresh: bool = False) -> dict[str, Any]:
        with self.store.locked():
            data = self.store.read()
            item = self.candidate(data, identifier)
            if item["status"] == "rejected" and not refresh:
                raise LearningError("candidate rejected; preview --refresh explicitly reopens review")
            try:
                package = item.get("package")
                if refresh or package is None:
                    package = self.build(data, identifier)
                self.verify_package(data, item)
            except (LearningError, self.api.HarnessError, OSError, ValueError) as exc:
                item["error"] = str(exc)
                self.store.save(data)
                raise
            return {"sha256": digest(package), "package": package}

    def approve(self, identifier: str, sha256: str) -> None:
        with self.store.locked():
            data = self.store.read()
            item = self.candidate(data, identifier)
            if item["status"] not in ("prepared", "approved"):
                raise LearningError("only a complete prepared candidate can be approved")
            package = self.verify_package(data, item)
            if sha256 != digest(package):
                raise LearningError("review hash mismatch; preview the current exact content")
            item.update(approval=sha256, status="approved", error=None)
            self.store.save(data)

    def pull_request(self, package: dict[str, Any]) -> list[dict[str, Any]]:
        destination = package["destination"]
        owner = destination["push_repository"].split("/")[0]
        # gh pr list --head does not support owner:branch; the REST endpoint
        # does, including closed/merged PRs whose branch has since been deleted.
        result = self.gh(
            "api", "--method", "GET", f"repos/{destination['repository']}/pulls",
            "-f", "state=all", "-f", f"head={owner}:{package['branch']}",
            "-f", "per_page=100",
        )
        records = json.loads(result)
        if not isinstance(records, list):
            raise LearningError("invalid GitHub pull-request response")
        value = []
        for record in records:
            head = record["head"]
            repository = head.get("repo")
            if (
                not repository
                or repository["full_name"].casefold() != destination["push_repository"].casefold()
            ):
                continue
            value.append({
                "url": record["html_url"],
                "state": "MERGED" if record["merged_at"] else record["state"].upper(),
                "headRefOid": head["sha"], "title": record["title"],
                "body": record["body"] or "", "baseRefName": record["base"]["ref"],
            })
        if len(value) > 1:
            raise LearningError("ambiguous existing learning pull request")
        return value

    def submit(self, data: dict[str, Any], identifier: str) -> None:
        item = self.candidate(data, identifier)
        package = self.verify_package(data, item)
        if item.get("approval") != digest(package):
            raise LearningError("missing or invalid exact-content approval")
        worktree = Path(item["worktree"])
        commit = item.get("commit")
        if not commit:
            head = self.git("rev-parse", "HEAD", cwd=worktree)
            if head == package["base_commit"]:
                self.git("add", "--", *sorted(package["files"]), cwd=worktree)
                self.git("diff", "--cached", "--check", cwd=worktree)
                environment = os.environ.copy()
                for kind in ("author", "committer"):
                    identity = re.fullmatch(
                        r"(.+) <([^<>\n]+)> ([0-9]+ [+-][0-9]{4})", package[kind + "_ident"]
                    )
                    if identity is None:
                        raise LearningError("reviewed Git identity is malformed")
                    for field, content in zip(("NAME", "EMAIL", "DATE"), identity.groups()):
                        environment[f"GIT_{kind.upper()}_{field}"] = content
                checked(["git", "commit", "--file", "-"], worktree,
                        input_text=package["commit_message"], env=environment)
                head = self.git("rev-parse", "HEAD", cwd=worktree)
            # This also recovers a crash after commit but before the state receipt.
            if self.git("rev-list", "--count", f"{package['base_commit']}..{head}", cwd=worktree) != "1":
                raise LearningError("expected exactly one learning commit")
            self.git("merge-base", "--is-ancestor", package["base_commit"], head, cwd=worktree)
            if self.git("show", "-s", "--format=%B", head, cwd=worktree) != package["commit_message"].strip():
                raise LearningError("commit message is not the approved message")
            item["commit"] = commit = head
            self.store.save(data)
        if self.git("rev-parse", "HEAD", cwd=worktree) != commit:
            raise LearningError("prepared commit changed; approval invalid")
        headers = self.git("cat-file", "-p", commit, cwd=worktree).split("\n\n", 1)[0].splitlines()
        if any(f"{kind} {package[kind + '_ident']}" not in headers for kind in ("author", "committer")):
            raise LearningError("commit attribution differs from the approved identities")
        # Verify the committed tree too, not merely its currently checked-out files.
        names = set(self.git("diff", "--name-only", package["base_commit"], commit, cwd=worktree).splitlines())
        if names != set(package["files"]):
            raise LearningError("commit contains a different file set")
        for name, expected in package["files"].items():
            actual = checked(["git", "show", f"{commit}:{name}"], worktree, strip=False)
            if actual != expected:
                raise LearningError("committed content differs from the approved package")
        if self.git("status", "--porcelain", cwd=worktree):
            raise LearningError("prepared worktree is not clean")
        destination = package["destination"]
        existing = self.pull_request(package)
        if not existing:
            # The pre-push policy requires a named source ref. Pin the reviewed
            # object in a dedicated ref instead of trusting a movable branch.
            source = f"refs/aikb-approved/{item['approval']}"
            pinned = self.git("for-each-ref", "--format=%(objectname)", source, cwd=worktree)
            if pinned and pinned != commit:
                raise LearningError("approved source ref points to a different commit")
            if not pinned:
                self.git("update-ref", source, commit, "0" * len(commit), cwd=worktree)
            self.git("push", "--no-follow-tags", destination["push_url"],
                     f"{source}:refs/heads/{package['branch']}", cwd=worktree)
            owner = destination["push_repository"].split("/")[0]
            self.gh(
                "pr", "create", "--repo", destination["repository"],
                "--head", f"{owner}:{package['branch']}", "--base", destination["base"],
                "--title", package["title"], "--body", package["body"],
            )
            existing = self.pull_request(package)
        if not existing:
            raise LearningError("PR creation returned without a discoverable pull request; retry")
        pr = existing[0]
        if (
            pr["title"] != package["title"] or pr["body"] != package["body"]
            or pr["baseRefName"] != destination["base"]
            or (pr["state"] != "MERGED" and pr["headRefOid"] != commit)
        ):
            raise LearningError("existing PR does not match the approved package")
        item.update(
            status={"MERGED": "merged", "CLOSED": "closed"}.get(pr["state"], "submitted"),
            url=pr["url"], error=None, submitted=now(),
        )
        self.store.save(data)

    def run(self) -> int:
        with self.store.locked():
            data = self.store.read()
            if not data["config"]["publish"]:
                raise LearningError("periodic publication disabled; nothing was exported")
            failures = 0
            processed = 0
            started = time.monotonic()
            pending = sorted(
                ((identifier, item) for identifier, item in data["candidates"].items()
                 if item["status"] in ("approved", "submitted")),
                key=lambda pair: pair[1].get("last_attempt", ""),
            )
            for identifier, item in pending:
                if processed >= 5 or time.monotonic() - started >= 300:
                    break
                processed += 1
                item["last_attempt"] = now()
                self.store.save(data)
                try:
                    if item["status"] == "approved":
                        self.submit(data, identifier)
                    else:
                        matches = self.pull_request(item["package"])
                        if matches:
                            item["status"] = {
                                "MERGED": "merged", "CLOSED": "closed",
                            }.get(matches[0]["state"], "submitted")
                            item["error"] = None
                            self.store.save(data)
                except (LearningError, self.api.HarnessError, OSError, ValueError) as exc:
                    # Retain the phase and approval for idempotent retry, not a
                    # success-shaped "submitted" state when the network failed.
                    item["error"] = str(exc)
                    failures += 1
                    self.store.save(data)
            data["last_run"] = {"utc": now(), "failures": failures, "processed": processed}
            self.store.save(data)
            print(canonical(data["last_run"]), end="")
            return 1 if failures else 0


def registry_store() -> Store:
    return Store(Path.home() / ".ai-knowledge-harness" / "schedules")


def read_schedules(store: Store) -> dict[str, Any]:
    path = store.root / "registry.json"
    if not path.exists():
        return {}
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict) or any(
        not isinstance(name, str) or not isinstance(record, dict)
        or not isinstance(record.get("repo"), str)
        or not isinstance(record.get("state_dir"), str)
        or type(record.get("minutes")) is not int
        for name, record in value.items()
    ):
        raise LearningError("invalid schedule registry; preserved without changes")
    return value


def installation_schedules(workflow: Workflow) -> list[dict[str, Any]]:
    return [
        record for record in read_schedules(registry_store()).values()
        if Path(record["repo"]).resolve() == workflow.repo.resolve()
    ]


def schedule(workflow: Workflow, action: str, minutes: int) -> dict[str, Any]:
    registry = registry_store()
    if action in ("check", "uninstall"):
        results = []
        for record in installation_schedules(workflow):
            other = Workflow(workflow.repo, Path(record["state_dir"]), workflow.api)
            results.append(schedule(other, "remove" if action == "uninstall" else "status",
                                    record["minutes"]))
        return {"schedules": results}
    key = hashlib.sha256(str(workflow.store.root).encode("utf-8")).hexdigest()[:12]
    name = "aikb-learning-" + key
    if action == "status":
        if not workflow.store.read().get("scheduler") and name not in read_schedules(registry):
            return {"state": "not-installed"}
        return native_schedule(workflow, action, minutes)
    # Registry -> inbox is the installation lock order. Removal must stop an
    # active worker BEFORE acquiring the inbox lock that worker owns.
    with registry.locked():
        records = read_schedules(registry)
        data = workflow.store.read()
        if action == "remove":
            if not data.get("scheduler") and name not in records:
                return {"state": "not-installed"}
            result = native_schedule(workflow, "remove", minutes)
            # Native stop requests can return before the process releases its
            # file handles. Wait boundedly rather than treating that as success.
            with workflow.store.locked(wait_seconds=30):
                data = workflow.store.read()
                data["scheduler"] = None
                workflow.store.save(data)
            records.pop(name, None)
            atomic(registry.root / "registry.json", canonical(records))
            return result
        with workflow.store.locked():
            data = workflow.store.read()
            if not data["config"]["publish"]:
                raise LearningError("enable publication explicitly before scheduling")
            descriptor = {
                "repo": str(workflow.repo), "state_dir": str(workflow.store.root),
                "minutes": minutes, "state": "install-pending",
            }
            records[name] = descriptor
            atomic(registry.root / "registry.json", canonical(records))
            data["scheduler"] = dict(descriptor)
            workflow.store.save(data)
            try:
                result = native_schedule(workflow, "install", minutes)
                native_schedule(workflow, "status", minutes)
                descriptor.update(state="installed", **result)
                data["scheduler"] = dict(descriptor)
                workflow.store.save(data)
                atomic(registry.root / "registry.json", canonical(records))
                return result
            except (LearningError, OSError, ValueError) as exc:
                descriptor["error"] = str(exc)
                data["scheduler"] = dict(descriptor)
                workflow.store.save(data)
                atomic(registry.root / "registry.json", canonical(records))
                raise


def native_schedule(
    workflow: Workflow, action: str, minutes: int, *, platform: str | None = None,
) -> dict[str, Any]:
    """Install only on explicit request; no process is started by bootstrap."""
    import plistlib
    import xml.etree.ElementTree as ET

    if not 15 <= minutes <= 1440:
        raise LearningError("schedule interval must be 15..1440 minutes")
    key = hashlib.sha256(str(workflow.store.root).encode("utf-8")).hexdigest()[:12]
    name = "aikb-learning-" + key
    argv = [
        sys.executable, str(workflow.repo / "bin" / "aikb.py"),
        "--repo", str(workflow.repo), "learn", "--state-dir",
        str(workflow.store.root), "run",
    ]
    if action == "install":
        data = workflow.store.read()
        if not data["config"]["publish"]:
            raise LearningError("enable publication explicitly before scheduling")
        target = workflow.destination(data)
        if workflow.git("branch", "--show-current") != target["base"] or workflow.git("status", "--porcelain"):
            raise LearningError("schedule only from the clean, installed default-branch checkout")
    platform = platform or ("windows" if os.name == "nt" else sys.platform)
    if platform == "windows":
        if action == "remove":
            # Deleting a task registration alone leaves a running worker alive.
            command = (
                "$ErrorActionPreference='Stop';"
                "$s=New-Object -ComObject Schedule.Service;$s.Connect();"
                "$f=$s.GetFolder('\\');"
                f"try{{$t=$f.GetTask('{name}')}}"
                "catch [System.IO.FileNotFoundException]{exit 0};"
                "if($t.State -eq 4){$t.Stop(0)};"
                f"$f.DeleteTask('{name}',0)"
            )
            checked(["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", command],
                    workflow.repo)
        elif action == "status":
            return {"scheduler": "Windows Task Scheduler", "result": checked(
                ["schtasks", "/Query", "/TN", name, "/FO", "LIST"], workflow.repo)}
        else:
            namespace = "http://schemas.microsoft.com/windows/2004/02/mit/task"
            ET.register_namespace("", namespace)
            root = ET.Element("{" + namespace + "}Task", version="1.2")

            def node(parent, tag, text=None):
                element = ET.SubElement(parent, "{" + namespace + "}" + tag)
                if text is not None:
                    element.text = text
                return element

            triggers = node(root, "Triggers")
            trigger = node(triggers, "TimeTrigger")
            repetition = node(trigger, "Repetition")
            node(repetition, "Interval", f"PT{minutes}M")
            node(trigger, "StartBoundary", datetime.datetime.now().astimezone().isoformat(timespec="seconds"))
            node(trigger, "Enabled", "true")
            principals = node(root, "Principals")
            principal = node(principals, "Principal")
            principal.set("id", "Author")
            import csv
            identity = checked(["whoami", "/user", "/fo", "csv", "/nh"], workflow.repo)
            node(principal, "UserId", next(csv.reader([identity]))[1])
            # InteractiveToken avoids passwords and uses the operator's own gh login.
            node(principal, "LogonType", "InteractiveToken")
            node(principal, "RunLevel", "LeastPrivilege")
            settings = node(root, "Settings")
            node(settings, "MultipleInstancesPolicy", "IgnoreNew")
            node(settings, "ExecutionTimeLimit", "PT30M")
            actions = node(root, "Actions")
            actions.set("Context", "Author")
            command = node(actions, "Exec")
            node(command, "Command", argv[0])
            node(command, "Arguments", subprocess.list2cmdline(argv[1:]))
            node(command, "WorkingDirectory", str(workflow.repo))
            path = workflow.store.root / "schedule.xml"
            atomic(path, '<?xml version="1.0" encoding="UTF-16"?>\n'
                   + ET.tostring(root, encoding="unicode"), encoding="utf-16")
            checked(["schtasks", "/Create", "/TN", name, "/XML", str(path), "/F"], workflow.repo)
    elif platform == "darwin":
        path = Path.home() / "Library" / "LaunchAgents" / (name + ".plist")
        domain = f"gui/{os.getuid()}"
        if action == "remove":
            checked(["launchctl", "bootout", f"{domain}/{name}"], workflow.repo)
            path.unlink()
        elif action == "status":
            return {"scheduler": "launchd", "result": checked(
                ["launchctl", "print", f"{domain}/{name}"], workflow.repo)}
        else:
            if path.exists():
                raise LearningError("schedule already exists; remove it before reinstalling")
            value = {
                "Label": name, "ProgramArguments": argv,
                "StartInterval": minutes * 60, "WorkingDirectory": str(workflow.repo),
                "StandardOutPath": str(workflow.store.root / "worker.stdout.log"),
                "StandardErrorPath": str(workflow.store.root / "worker.stderr.log"),
                "EnvironmentVariables": {"PATH": os.environ.get("PATH", "")},
            }
            atomic(path, plistlib.dumps(value).decode("utf-8"))
            checked(["launchctl", "bootstrap", domain, str(path)], workflow.repo)
    else:
        directory = Path.home() / ".config" / "systemd" / "user"
        service = directory / (name + ".service")
        timer = directory / (name + ".timer")
        if action == "remove":
            checked(["systemctl", "--user", "stop", service.name], workflow.repo)
            checked(["systemctl", "--user", "disable", "--now", timer.name], workflow.repo)
            service.unlink()
            timer.unlink()
            checked(["systemctl", "--user", "daemon-reload"], workflow.repo)
        elif action == "status":
            return {"scheduler": "systemd user timer", "result": checked(
                ["systemctl", "--user", "status", timer.name, "--no-pager"], workflow.repo)}
        else:
            if service.exists() or timer.exists():
                raise LearningError("schedule already exists; remove it before reinstalling")
            # systemd expands % and $, even inside quoted ExecStart arguments.
            def quote(value):
                return '"' + value.replace("\\", "\\\\").replace('"', '\\"').replace(
                    "%", "%%").replace("$", "$$").replace("\n", "\\n") + '"'
            environment = quote("PATH=" + os.environ.get("PATH", "")).replace("$$", "$")
            atomic(service, "[Unit]\nDescription=Reviewed AIKB learning submissions\n"
                   "[Service]\nType=oneshot\nEnvironment=" + environment + "\nExecStart="
                   + " ".join(map(quote, argv)) + "\n")
            atomic(timer, "[Unit]\nDescription=Periodic reviewed AIKB learning submissions\n"
                   f"[Timer]\nOnBootSec=5m\nOnUnitActiveSec={minutes}m\n"
                   f"Unit={name}.service\n[Install]\nWantedBy=timers.target\n")
            checked(["systemctl", "--user", "daemon-reload"], workflow.repo)
            checked(["systemctl", "--user", "enable", "--now", timer.name], workflow.repo)
    return {"name": name, "action": action, "minutes": minutes}


def add_parser(subparsers: Any, handler: Any) -> None:
    parser = subparsers.add_parser("learn", help="opt-in capture and reviewed periodic contributions")
    parser.add_argument("--state-dir", type=Path, help="private local inbox (outside the checkout)")
    commands = parser.add_subparsers(dest="learning_command", required=True)
    config = commands.add_parser("configure", help="explicitly opt in/out; never installs a schedule")
    config.add_argument("--capture", choices=("on", "off"))
    config.add_argument("--publish", choices=("on", "off"))
    config.add_argument("--push-remote")
    capture = commands.add_parser("capture", help="capture a generic structured lesson, never a transcript")
    source = capture.add_mutually_exclusive_group(required=True)
    source.add_argument("--file", type=Path, help="JSON candidate, or '-' for UTF-8 stdin")
    source.add_argument("--nothing", choices=TRIGGERS)
    commands.add_parser("status", help="show opt-ins, checkpoint counts, backlog and worker errors")
    commands.add_parser("archive", help="move terminal candidates to private local archive files")
    search = commands.add_parser("search", help="search local proposals, clearly separate from canonical knowledge")
    search.add_argument("query")
    for name in ("show", "preview", "approve", "reject"):
        child = commands.add_parser(name)
        child.add_argument("id")
        if name == "preview":
            child.add_argument("--refresh", action="store_true",
                               help="invalidate approval and prepare a new worktree; preserve the old one")
        if name == "approve":
            child.add_argument("--sha256", required=True, help="exact reviewed preview hash")
            child.add_argument("--public", action="store_true", required=True,
                               help="confirm rights, license, privacy and exact public disclosure")
    commands.add_parser("run", help="one bounded, idempotent publication pass (suitable for schedulers)")
    scheduler = commands.add_parser("schedule", help="explicit native per-user timer; never enabled by install")
    scheduler.add_argument("action", choices=("install", "status", "remove", "check", "uninstall"))
    scheduler.add_argument("--minutes", type=int, default=60)
    parser.set_defaults(handler=handler)


def execute(args: argparse.Namespace, api: Any) -> int:
    try:
        state = api._require_valid_state(args.repo, projection=True)
        key = hashlib.sha256(
            state.registry["repository"]["canonical_remote"].encode("utf-8")
        ).hexdigest()[:16]
        root = (
            args.state_dir or Path.home() / ".ai-knowledge-harness" / "learning" / key
        ).expanduser().resolve()
        if api._inside(root, args.repo.resolve()):
            raise LearningError("learning inbox must be outside the Git checkout")
        workflow = Workflow(args.repo, root, api)
        command = args.learning_command
        if command == "configure":
            print(canonical(workflow.configure(args.capture, args.publish, args.push_remote)), end="")
        elif command == "capture":
            value = None
            if args.file is not None:
                if str(args.file) == "-":
                    raw = sys.stdin.buffer.read(MAX_INPUT + 1)
                else:
                    with args.file.open("rb") as stream:
                        raw = stream.read(MAX_INPUT + 1)
                if len(raw) > MAX_INPUT:
                    raise LearningError("candidate exceeds 24000 bytes")
                value = json.loads(raw.decode("utf-8"))
            print(workflow.capture(value, args.nothing))
        elif command == "status":
            data = workflow.store.read()
            print(canonical({
                "config": data["config"], "checkpoints": data["checkpoints"],
                "last_run": data["last_run"], "state_dir": str(root),
                "scheduler": data.get("scheduler"),
                "installation_schedules": installation_schedules(workflow),
                "candidates": [
                    {"id": identifier, **{k: item.get(k) for k in
                     ("status", "seen", "created", "error", "url")}}
                    for identifier, item in data["candidates"].items()
                ],
            }), end="")
        elif command == "show":
            print(canonical(workflow.candidate(workflow.store.read(), args.id)), end="")
        elif command == "search":
            if not args.query.strip():
                raise LearningError("local learning search must not be empty")
            data = workflow.store.read()
            print(canonical([
                {"id": identifier, "status": item["status"], "authority": "unreviewed-local-proposal",
                 "title": item["value"]["title"], "expression": item["value"]["expression"]}
                for identifier, item in data["candidates"].items()
                if item["status"] != "rejected"
                and args.query.casefold() in canonical(item["value"]).casefold()
            ][:40]), end="")
        elif command == "archive":
            with workflow.store.locked():
                data = workflow.store.read()
                archived = [
                    identifier for identifier, item in data["candidates"].items()
                    if item["status"] in ("rejected", "merged", "closed")
                ]
                for identifier in archived:
                    item = data["candidates"][identifier]
                    atomic(root / "archive" / f"{identifier}-{digest(item)[:16]}.json", canonical(item))
                    del data["candidates"][identifier]
                workflow.store.save(data)
            print(f"Archived {len(archived)} terminal candidates locally; worktrees preserved.")
        elif command == "preview":
            result = workflow.preview(args.id, args.refresh)
            print(canonical(result), end="")
        elif command == "approve":
            workflow.approve(args.id, args.sha256)
            print("Approved exact package for public submission; maintainer merge review still required.")
        elif command == "reject":
            with workflow.store.locked():
                data = workflow.store.read()
                item = workflow.candidate(data, args.id)
                if item["status"] in ("submitted", "merged", "closed"):
                    raise LearningError("already exported; manage the PR on GitHub (rejection cannot revoke it)")
                item.update(status="rejected", approval=None)
                workflow.store.save(data)
            print("Rejected locally; existing worktree and evidence preserved.")
        elif command == "run":
            return workflow.run()
        elif command == "schedule":
            print(canonical(schedule(workflow, args.action, args.minutes)), end="")
        return 0
    except (LearningError, OSError, ValueError) as exc:
        raise api.HarnessError(f"learning: {exc}") from exc
