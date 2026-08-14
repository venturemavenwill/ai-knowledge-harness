from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
CLI = REPO / "bin" / "aikb.py"
NEW_NAMESPACE = REPO / "scripts" / "new_namespace.py"


def run_cli(
    *args: str, repo: Path = REPO, env: dict[str, str] | None = None
) -> subprocess.CompletedProcess[str]:
    # Network-touching auto-update stays off unless a test opts in.
    environment = os.environ.copy()
    environment["AIKB_AUTO_UPDATE"] = "off"
    if env:
        environment.update(env)
    return subprocess.run(
        [sys.executable, str(CLI), "--repo", str(repo), *args],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=30,
        env=environment,
    )


def run_git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=15,
    )


def copy_repository(target: Path) -> Path:
    copy = target / "repo"
    shutil.copytree(REPO, copy, ignore=shutil.ignore_patterns(".git", "__pycache__"))
    return copy


def make_tracked_clone(root: Path) -> Path:
    """Build a checkout on `main` whose canonical remote is a local bare repo."""
    source_parent = root / "source"
    source_parent.mkdir()
    repo = copy_repository(source_parent)
    origin = root / "origin.git"

    registry_path = repo / "registry.json"
    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    registry["repository"]["canonical_remote"] = origin.as_uri()
    registry_path.write_text(
        json.dumps(registry, indent=2) + "\n", encoding="utf-8", newline="\n"
    )
    refreshed = run_cli("refresh", repo=repo)
    if refreshed.returncode != 0:
        raise AssertionError(refreshed.stderr)

    run_git(repo, "init", "-b", "main")
    run_git(repo, "config", "user.name", "Harness Test")
    run_git(repo, "config", "user.email", "harness@example.invalid")
    run_git(repo, "add", ".")
    run_git(repo, "commit", "-m", "test fixture")
    run_git(root, "init", "--bare", str(origin))
    run_git(repo, "remote", "add", "origin", origin.as_uri())
    run_git(repo, "push", "--set-upstream", "origin", "main")
    return repo


def publish_upstream_commit(repo: Path, relative: str, message: str) -> str:
    """Publish a commit to origin, then rewind the local branch behind it."""
    target = repo / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(f"# {message}\n", encoding="utf-8", newline="\n")
    run_git(repo, "add", "--all")
    run_git(repo, "commit", "-m", message)
    published = run_git(repo, "rev-parse", "HEAD").stdout.strip()
    run_git(repo, "push", "origin", "main")
    run_git(repo, "reset", "--hard", "HEAD~1")
    return published


def head_of(repo: Path) -> str:
    return run_git(repo, "rev-parse", "HEAD").stdout.strip()


KNOWLEDGE_FILE = "namespaces/knowledge.systems.integrity/NOTES.md"
CODE_FILE = "install/NOTE.txt"


class AutoUpdateTests(unittest.TestCase):
    def test_knowledge_only_update_applies_automatically(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            repo = make_tracked_clone(Path(temp))
            published = publish_upstream_commit(repo, KNOWLEDGE_FILE, "knowledge note")
            self.assertNotEqual(head_of(repo), published)

            result = run_cli("list", repo=repo, env={"AIKB_AUTO_UPDATE": "knowledge"})

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("applied 1 knowledge file(s)", result.stderr)
            self.assertEqual(head_of(repo), published)
            self.assertTrue((repo / KNOWLEDGE_FILE).is_file())

    def test_code_change_is_reported_but_never_auto_applied(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            repo = make_tracked_clone(Path(temp))
            published = publish_upstream_commit(repo, CODE_FILE, "tooling change")
            before = head_of(repo)

            result = run_cli("list", repo=repo, env={"AIKB_AUTO_UPDATE": "knowledge"})

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("change executable code or installed surfaces", result.stderr)
            self.assertIn(CODE_FILE, result.stderr)
            self.assertEqual(head_of(repo), before)
            self.assertNotEqual(head_of(repo), published)
            self.assertFalse((repo / CODE_FILE).exists())

    def test_auto_update_can_be_disabled(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            repo = make_tracked_clone(Path(temp))
            publish_upstream_commit(repo, KNOWLEDGE_FILE, "knowledge note")
            before = head_of(repo)

            result = run_cli("list", repo=repo, env={"AIKB_AUTO_UPDATE": "off"})

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertNotIn("UPDATE", result.stderr)
            self.assertEqual(head_of(repo), before)

    def test_dirty_checkout_is_never_auto_updated(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            repo = make_tracked_clone(Path(temp))
            publish_upstream_commit(repo, KNOWLEDGE_FILE, "knowledge note")
            before = head_of(repo)
            readme = repo / "README.md"
            readme.write_text(
                readme.read_text(encoding="utf-8") + "\nlocal edit\n",
                encoding="utf-8",
                newline="\n",
            )

            result = run_cli("list", repo=repo, env={"AIKB_AUTO_UPDATE": "knowledge"})

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(head_of(repo), before)

    def test_update_command_gates_code_changes_behind_all(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            repo = make_tracked_clone(Path(temp))
            published = publish_upstream_commit(repo, CODE_FILE, "tooling change")
            before = head_of(repo)

            gated = run_cli("update", repo=repo)
            self.assertEqual(gated.returncode, 1, gated.stderr)
            self.assertIn(CODE_FILE, gated.stdout)
            self.assertIn("aikb update --all", gated.stdout)
            self.assertEqual(head_of(repo), before)

            applied = run_cli("update", "--all", repo=repo)
            self.assertEqual(applied.returncode, 0, applied.stderr)
            self.assertEqual(head_of(repo), published)
            self.assertIn("re-run the installer bootstrap", applied.stdout)

    def test_update_check_reports_without_writing(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            repo = make_tracked_clone(Path(temp))
            publish_upstream_commit(repo, KNOWLEDGE_FILE, "knowledge note")
            before = head_of(repo)

            pending = run_cli("update", "--check", repo=repo)
            self.assertEqual(pending.returncode, 1, pending.stderr)
            self.assertEqual(head_of(repo), before)

            applied = run_cli("update", repo=repo)
            self.assertEqual(applied.returncode, 0, applied.stderr)

            current = run_cli("update", "--check", repo=repo)
            self.assertEqual(current.returncode, 0, current.stderr)
            self.assertIn("already current", current.stdout)


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

    def test_show_allows_contribution_guide(self) -> None:
        result = run_cli("show", "CONTRIBUTING.md")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Contributing to the AI Knowledge Harness", result.stdout)

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
                newline="\n",
            )
            result = run_cli("validate", "--projection", repo=repo)
            self.assertEqual(result.returncode, 1)
            self.assertIn("catalog.json: generated projection is stale", result.stderr)

    def test_canonical_claim_with_crlf_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            repo = copy_repository(Path(temp))
            claim = (
                repo
                / "namespaces"
                / "knowledge.systems.integrity"
                / "claims"
                / "design.knowledge.systems.integrity--1.0.0.md"
            )
            raw = claim.read_bytes()
            self.assertNotIn(b"\r", raw)
            claim.write_bytes(raw.replace(b"\n", b"\r\n"))

            result = run_cli("validate", repo=repo)

            self.assertEqual(result.returncode, 1)
            self.assertIn("canonical text must use LF line endings", result.stderr)

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
                newline="\n",
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
                newline="\n",
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
                newline="\n",
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

    def test_contribute_creates_isolated_branch_from_origin(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source_parent = root / "source"
            source_parent.mkdir()
            repo = copy_repository(source_parent)
            origin = root / "origin.git"
            origin_url = origin.as_uri()

            registry_path = repo / "registry.json"
            registry = json.loads(registry_path.read_text(encoding="utf-8"))
            registry["repository"]["canonical_remote"] = origin_url
            registry_path.write_text(
                json.dumps(registry, indent=2) + "\n",
                encoding="utf-8",
                newline="\n",
            )
            refreshed = run_cli("refresh", repo=repo)
            self.assertEqual(refreshed.returncode, 0, refreshed.stderr)

            run_git(repo, "init", "-b", "main")
            run_git(repo, "config", "user.name", "Harness Test")
            run_git(repo, "config", "user.email", "harness@example.invalid")
            run_git(repo, "add", ".")
            run_git(repo, "commit", "-m", "test fixture")
            run_git(root, "init", "--bare", str(origin))
            run_git(repo, "remote", "add", "origin", origin_url)
            run_git(repo, "push", "--set-upstream", "origin", "main")

            worktree = root / "routing-gap"
            result = run_cli(
                "contribute",
                "routing-gap",
                "--worktree",
                str(worktree),
                repo=repo,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue((worktree / "CONTRIBUTING.md").is_file())
            branch = run_git(worktree, "branch", "--show-current").stdout.strip()
            self.assertEqual(branch, "improvement/routing-gap")
            self.assertIn(str(worktree.resolve()), result.stdout)
            self.assertFalse((repo / "routing-gap").exists())

            (repo / "README.md").write_text(
                (repo / "README.md").read_text(encoding="utf-8") + "\n",
                encoding="utf-8",
                newline="\n",
            )
            refused = run_cli(
                "contribute",
                "second-gap",
                "--worktree",
                str(root / "second-gap"),
                repo=repo,
            )
            self.assertEqual(refused.returncode, 2)
            self.assertIn("canonical checkout has local changes", refused.stderr)

    def test_fork_clone_uses_upstream_as_the_canonical_remote(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source_parent = root / "source"
            source_parent.mkdir()
            repo = copy_repository(source_parent)
            upstream = root / "upstream.git"
            fork = root / "fork.git"
            upstream_url = upstream.as_uri()
            fork_url = fork.as_uri()

            registry_path = repo / "registry.json"
            registry = json.loads(registry_path.read_text(encoding="utf-8"))
            registry["repository"]["canonical_remote"] = upstream_url
            registry_path.write_text(
                json.dumps(registry, indent=2) + "\n",
                encoding="utf-8",
                newline="\n",
            )
            refreshed = run_cli("refresh", repo=repo)
            self.assertEqual(refreshed.returncode, 0, refreshed.stderr)

            run_git(repo, "init", "-b", "main")
            run_git(repo, "config", "user.name", "Harness Test")
            run_git(repo, "config", "user.email", "harness@example.invalid")
            run_git(repo, "add", ".")
            run_git(repo, "commit", "-m", "test fixture")
            run_git(root, "init", "--bare", str(upstream))
            run_git(root, "init", "--bare", str(fork))
            run_git(repo, "remote", "add", "upstream", upstream_url)
            run_git(repo, "remote", "add", "origin", fork_url)
            run_git(repo, "push", "upstream", "main")
            run_git(repo, "push", "origin", "main")
            run_git(repo, "config", "core.hooksPath", ".githooks")

            health = run_cli("check", repo=repo)
            self.assertEqual(health.returncode, 0, health.stderr)
            self.assertIn("canonical remote 'upstream'", health.stdout)

            synced = run_cli("sync", repo=repo)
            self.assertEqual(synced.returncode, 0, synced.stderr)

            worktree = root / "fork-gap"
            result = run_cli(
                "contribute",
                "fork-gap",
                "--worktree",
                str(worktree),
                repo=repo,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(
                run_git(worktree, "branch", "--show-current").stdout.strip(),
                "improvement/fork-gap",
            )
            self.assertIn("base:     upstream/main", result.stdout)
            self.assertIn("push:     origin", result.stdout)
            self.assertIn(
                "git push --set-upstream origin improvement/fork-gap",
                result.stdout,
            )

            run_git(repo, "remote", "add", "fork", fork_url)
            explicit_worktree = root / "explicit-fork-gap"
            explicit = run_cli(
                "contribute",
                "explicit-fork-gap",
                "--worktree",
                str(explicit_worktree),
                "--push-remote",
                "fork",
                repo=repo,
            )
            self.assertEqual(explicit.returncode, 0, explicit.stderr)
            self.assertIn("push:     fork", explicit.stdout)
            self.assertIn(
                "git push --set-upstream fork improvement/explicit-fork-gap",
                explicit.stdout,
            )

    def test_posix_wrapper_resolves_symlinked_invocation(self) -> None:
        if sys.platform == "win32":
            self.skipTest("POSIX shell wrapper is not used on Windows")
        with tempfile.TemporaryDirectory() as temp:
            link = Path(temp) / "aikb"
            link.symlink_to(REPO / "bin" / "aikb")

            result = subprocess.run(
                [str(link), "--repo", str(REPO), "list"],
                check=False,
                capture_output=True,
                text=True,
                encoding="utf-8",
                timeout=30,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("AI knowledge namespaces", result.stdout)

    def test_posix_installer_covers_macos_and_linux_editor_roots(self) -> None:
        script = (REPO / "install" / "bootstrap.sh").read_text(encoding="utf-8")
        self.assertIn('"$HOME/.config" "$HOME/Library/Application Support"', script)
        for editor in ("Code - Insiders", "VSCodium", "Cursor", "Windsurf"):
            self.assertIn(f'"{editor}"', script)

    def test_posix_installer_configures_shell_environment(self) -> None:
        script = (REPO / "install" / "bootstrap.sh").read_text(encoding="utf-8")
        self.assertIn("export AI_KB_REPO=", script)
        self.assertIn(".zshrc", script)
        self.assertIn(".bashrc", script)

    def test_shell_sources_use_lf_endings(self) -> None:
        for relative in (
            "bin/aikb",
            "install/bootstrap.sh",
            ".githooks/pre-push",
        ):
            with self.subTest(path=relative):
                self.assertNotIn(b"\r", (REPO / relative).read_bytes())

    def test_windows_installer_uses_bomless_utf8_writes(self) -> None:
        script = (REPO / "install" / "bootstrap.ps1").read_text(encoding="utf-8")
        self.assertIn("System.Text.UTF8Encoding($false)", script)
        self.assertIn("Write-Utf8NoBom $Destination $desired", script)
        self.assertNotIn("Set-Content -LiteralPath $Destination", script)

    def test_windows_installer_places_harness_first_on_path(self) -> None:
        script = (REPO / "install" / "bootstrap.ps1").read_text(encoding="utf-8")
        self.assertIn("$newPath = (@($BinDir) + $withoutHarness) -join ';'", script)
        self.assertNotIn("$newPath = (@($pathEntries) + $BinDir) -join ';'", script)


if __name__ == "__main__":
    unittest.main()
