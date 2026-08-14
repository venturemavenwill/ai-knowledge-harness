from __future__ import annotations

import importlib.util
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from types import ModuleType

REPO = Path(__file__).resolve().parents[1]


def load_gate() -> ModuleType:
    path = REPO / "scripts" / "check_append_only.py"
    spec = importlib.util.spec_from_file_location("check_append_only", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def git(repo: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    return completed.stdout.strip()


def create_repository(root: Path) -> tuple[Path, str]:
    repo = root / "repo"
    repo.mkdir()
    git(repo, "init")
    git(repo, "config", "user.email", "tests@example.invalid")
    git(repo, "config", "user.name", "Harness Tests")
    manifest = repo / "namespaces" / "example.namespace" / "manifests" / "0001.json"
    claim = repo / "namespaces" / "example.namespace" / "claims" / "claim--1.0.0.md"
    manifest.parent.mkdir(parents=True)
    claim.parent.mkdir(parents=True)
    manifest.write_text("{}\n", encoding="utf-8")
    claim.write_text("# claim\n", encoding="utf-8")
    git(repo, "add", "namespaces")
    git(repo, "commit", "-m", "seed")
    return repo, git(repo, "rev-parse", "HEAD")


class AppendOnlyGateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.gate = load_gate()

    def test_new_claim_is_allowed(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            repo, base = create_repository(Path(temp))
            new_claim = (
                repo
                / "namespaces"
                / "example.namespace"
                / "claims"
                / "claim--2.0.0.md"
            )
            new_claim.write_text("# superseding claim\n", encoding="utf-8")
            git(repo, "add", "namespaces")
            git(repo, "commit", "-m", "add claim")
            self.assertEqual(self.gate.check(repo, base), [])

    def test_existing_claim_modification_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            repo, base = create_repository(Path(temp))
            claim = (
                repo
                / "namespaces"
                / "example.namespace"
                / "claims"
                / "claim--1.0.0.md"
            )
            claim.write_text("# changed in place\n", encoding="utf-8")
            git(repo, "add", "namespaces")
            git(repo, "commit", "-m", "mutate claim")
            violations = self.gate.check(repo, base)
            self.assertEqual(len(violations), 1)
            self.assertIn("canonical records are append-only", violations[0])

    def test_existing_manifest_deletion_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            repo, base = create_repository(Path(temp))
            manifest = (
                repo
                / "namespaces"
                / "example.namespace"
                / "manifests"
                / "0001.json"
            )
            manifest.unlink()
            git(repo, "add", "namespaces")
            git(repo, "commit", "-m", "delete manifest")
            violations = self.gate.check(repo, base)
            self.assertEqual(len(violations), 1)
            self.assertTrue(violations[0].startswith("D:"))

    def test_canonical_base_supports_a_fork_with_upstream_remote(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            repo, _ = create_repository(root)
            upstream = root / "upstream.git"
            fork = root / "fork.git"
            git(root, "init", "--bare", str(upstream))
            git(root, "init", "--bare", str(fork))
            (repo / "registry.json").write_text(
                json.dumps(
                    {
                        "repository": {
                            "canonical_remote": upstream.as_uri(),
                            "default_branch": "main",
                        }
                    }
                )
                + "\n",
                encoding="utf-8",
                newline="\n",
            )
            git(repo, "remote", "add", "origin", fork.as_uri())
            git(repo, "remote", "add", "upstream", upstream.as_uri())
            git(repo, "push", "upstream", "HEAD:main")
            git(
                repo,
                "fetch",
                "upstream",
                "main:refs/remotes/upstream/main",
            )

            self.assertEqual(self.gate._canonical_base(repo), "upstream/main")


if __name__ == "__main__":
    unittest.main()
