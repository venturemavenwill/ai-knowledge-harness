from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
CLI = REPO / "bin" / "aikb.py"
NEW_NAMESPACE = REPO / "scripts" / "new_namespace.py"


def run_cli(*args: str, repo: Path = REPO) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(CLI), "--repo", str(repo), *args],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=15,
    )


def copy_repository(target: Path) -> Path:
    copy = target / "repo"
    shutil.copytree(REPO, copy, ignore=shutil.ignore_patterns(".git", "__pycache__"))
    return copy


class HarnessTests(unittest.TestCase):
    def test_repository_and_projection_are_valid(self) -> None:
        result = run_cli("validate", "--projection")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertRegex(result.stdout, r"\d+ namespace\(s\), \d+ claim\(s\)")

    def test_refresh_check_is_deterministic(self) -> None:
        first = run_cli("refresh", "--check")
        second = run_cli("refresh", "--check")
        self.assertEqual(first.returncode, 0, first.stderr)
        self.assertEqual(second.returncode, 0, second.stderr)
        self.assertEqual(first.stdout, second.stdout)

    def test_specialization_search_includes_parent_by_default(self) -> None:
        inherited = run_cli(
            "search",
            "revert the fix",
            "--namespace",
            "engineering.repair.root-cause.python-packages",
        )
        exact = run_cli(
            "search",
            "revert the fix",
            "--namespace",
            "engineering.repair.root-cause.python-packages",
            "--exact-namespace",
        )
        self.assertEqual(inherited.returncode, 0, inherited.stderr)
        self.assertIn("engineering.repair.root-cause:", inherited.stdout)
        self.assertEqual(exact.returncode, 0, exact.stderr)
        self.assertIn("0 hit(s)", exact.stdout)

    def test_checkout_ancestor_named_build_does_not_hide_search_results(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            build_parent = Path(temp) / "build"
            build_parent.mkdir()
            repo = copy_repository(build_parent)
            result = run_cli(
                "search",
                "root cause",
                "--namespace",
                "engineering.repair.root-cause",
                repo=repo,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertNotIn("0 hit(s)", result.stdout)

    def test_show_rejects_parent_traversal(self) -> None:
        result = run_cli("show", "../README.md")
        self.assertEqual(result.returncode, 2)
        self.assertIn("ABSTENTION", result.stderr)
        self.assertIn("may not contain '..'", result.stderr)

    def test_claim_tamper_makes_projection_stale(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            repo = copy_repository(Path(temp))
            claim = (
                repo
                / "namespaces"
                / "knowledge.systems.integrity"
                / "claims"
                / "design.knowledge.systems.integrity--1.0.0.md"
            )
            claim.write_text(
                claim.read_text(encoding="utf-8") + "\nTampered after projection.\n",
                encoding="utf-8",
            )
            result = run_cli("validate", "--projection", repo=repo)
            self.assertEqual(result.returncode, 1)
            self.assertIn("catalog.json: generated projection is stale", result.stderr)

    def test_namespace_specialization_cycle_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            repo = copy_repository(Path(temp))
            manifest_path = (
                repo
                / "namespaces"
                / "engineering.repair.root-cause"
                / "manifests"
                / "0001.json"
            )
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["extends"] = "engineering.repair.root-cause.python-packages"
            manifest_path.write_text(
                json.dumps(manifest, indent=2) + "\n",
                encoding="utf-8",
            )
            result = run_cli("validate", "--projection", repo=repo)
            self.assertEqual(result.returncode, 1)
            self.assertIn("namespace specialization cycle", result.stderr)

    def test_missing_specialization_parent_fails_projection_cleanly(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            repo = copy_repository(Path(temp))
            manifest_path = (
                repo
                / "namespaces"
                / "engineering.repair.root-cause"
                / "manifests"
                / "0001.json"
            )
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["extends"] = "engineering.repair.root-cause.missing"
            manifest_path.write_text(
                json.dumps(manifest, indent=2) + "\n",
                encoding="utf-8",
            )
            result = run_cli("validate", "--projection", repo=repo)
            self.assertEqual(result.returncode, 1)
            self.assertIn("missing namespace", result.stderr)
            self.assertNotIn("Traceback", result.stderr)

    def test_malformed_claim_fails_before_projection_build(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            repo = copy_repository(Path(temp))
            claim_path = (
                repo
                / "namespaces"
                / "knowledge.systems.integrity"
                / "claims"
                / "design.knowledge.systems.integrity--1.0.0.md"
            )
            text = claim_path.read_text(encoding="utf-8")
            marker = '"parent_refs": []'
            claim_path.write_text(
                text.replace(marker, '"parent_refs": null', 1),
                encoding="utf-8",
            )
            result = run_cli("validate", "--projection", repo=repo)
            self.assertEqual(result.returncode, 1)
            self.assertIn("lineage.parent_refs: must be a list", result.stderr)
            self.assertNotIn("Traceback", result.stderr)

    def test_scaffold_forms_a_valid_child_namespace(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            repo = copy_repository(Path(temp))
            base_namespaces = len(
                [path for path in (repo / "namespaces").iterdir() if path.is_dir()]
            )
            base_claims = len(list((repo / "namespaces").glob("*/claims/*.md")))
            scaffold = subprocess.run(
                [
                    sys.executable,
                    str(NEW_NAMESPACE),
                    "engineering.repair.root-cause.go-packages",
                    "--repo",
                    str(repo),
                    "--title",
                    "Go package root-cause repair",
                    "--kind",
                    "capability-procedure",
                    "--authority",
                    "hand-authored-unmeasured",
                    "--extends",
                    "engineering.repair.root-cause",
                    "--consult-when",
                    "debugging or repairing a Go package",
                ],
                check=False,
                capture_output=True,
                text=True,
                encoding="utf-8",
            )
            self.assertEqual(scaffold.returncode, 0, scaffold.stderr)
            manifest_path = (
                repo
                / "namespaces"
                / "engineering.repair.root-cause.go-packages"
                / "manifests"
                / "0001.json"
            )
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            self.assertEqual(manifest["extends"], "engineering.repair.root-cause")
            result = run_cli("validate", repo=repo)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn(
                f"{base_namespaces + 1} namespace(s), {base_claims} claim(s)",
                result.stdout,
            )

    def test_template_placeholders_cannot_enter_canonical_claims(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            repo = copy_repository(Path(temp))
            destination = (
                repo
                / "namespaces"
                / "knowledge.systems.integrity"
                / "claims"
                / "replace.with.stable.claim.id--1.0.0.md"
            )
            shutil.copyfile(repo / "templates" / "claim.md", destination)
            result = run_cli("validate", repo=repo)
            self.assertEqual(result.returncode, 1)
            self.assertIn("unresolved template placeholder", result.stderr)

    def test_windows_installer_uses_bomless_utf8_writes(self) -> None:
        script = (REPO / "install" / "bootstrap.ps1").read_text(encoding="utf-8")
        self.assertIn("System.Text.UTF8Encoding($false)", script)
        self.assertIn("Write-Utf8NoBom $Destination $desired", script)
        self.assertNotIn("Set-Content -LiteralPath $Destination", script)


if __name__ == "__main__":
    unittest.main()
