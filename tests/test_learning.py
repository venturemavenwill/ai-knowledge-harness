from __future__ import annotations

import json
import contextlib
import importlib.util
import io
import os
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

REPO = Path(__file__).resolve().parents[1]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


api = load("aikb_learning_tests_api", REPO / "bin" / "aikb.py")
learning = load("aikb_learning_tests", REPO / "scripts" / "learning.py")


def lesson(**changes):
    value = {
        "trigger": "correction", "namespace": "engineering.repair.root-cause",
        "title": "Review complete worker receipts",
        "expression": "A worker receipt must distinguish pending review from published knowledge.",
        "scope": "a background process prepares knowledge for a shared repository",
        "procedure": "Persist each phase before external actions and reconcile the remote result on retry.",
        "verification": "Interrupt between submission and receipt; a retry must discover the existing proposal.",
        "uncertainty": "Unmeasured procedure; a summary alone does not establish reliability.",
        "evidence": "Synthetic public regression scenario; no original conversation retained.",
        "search_terms": "receipt retry",
    }
    return {**value, **changes}


def clean_seed(source, target):
    subprocess.run(
        ["git", "clone", "--quiet", "--no-hardlinks", "--no-checkout",
         str(source), str(target)], check=True, capture_output=True,
    )
    # PR CI checkouts are detached and need not have a local `main` branch.
    subprocess.run(
        ["git", "checkout", "--quiet", "-B", "main", "HEAD"],
        cwd=target, check=True, capture_output=True,
    )
    subprocess.run(
        ["git", "update-ref", "refs/remotes/origin/main", "HEAD"],
        cwd=target, check=True, capture_output=True,
    )


class LearningCLITests(unittest.TestCase):
    def test_status_is_available_without_enabling_capture(self):
        with tempfile.TemporaryDirectory() as home:
            result = subprocess.run(
                [sys.executable, str(REPO / "bin" / "aikb.py"), "--repo", str(REPO),
                 "learn", "--state-dir", home, "status"],
                capture_output=True, text=True,
                env={**os.environ, "AIKB_AUTO_UPDATE": "off"},
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            status = json.loads(result.stdout)
            self.assertFalse(status["config"]["capture"])
            self.assertFalse(status["config"]["publish"])
            self.assertEqual(status["candidates"], [])

    def test_invalid_capture_has_characterized_error(self):
        with tempfile.TemporaryDirectory() as home:
            prefix = [sys.executable, str(REPO / "bin" / "aikb.py"), "--repo", str(REPO),
                      "learn", "--state-dir", home]
            subprocess.run([*prefix, "configure", "--capture", "on"],
                           capture_output=True, check=True)
            result = subprocess.run([*prefix, "capture", "--file", "-"], input=b"[]",
                                    capture_output=True)
            self.assertEqual(result.returncode, 2)
            self.assertIn(b"candidate must contain exactly", result.stderr)


class LearningWorkflowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.seed_tmp = tempfile.TemporaryDirectory()
        cls.seed = Path(cls.seed_tmp.name) / "seed"
        # A real clean default-branch checkout, never the developer's dirty tree.
        clean_seed(REPO, cls.seed)

    @classmethod
    def tearDownClass(cls):
        cls.seed_tmp.cleanup()

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.repo = self.root / "repo"
        shutil.copytree(self.seed, self.repo)
        self.git("config", "user.name", "Learning Test")
        self.git("config", "user.email", "learning@example.invalid")
        self.git("config", "core.autocrlf", "false")
        self.git("remote", "set-url", "origin",
                 "https://github.com/venturemavenwill/ai-knowledge-harness.git")
        self.workflow = learning.Workflow(self.repo, self.root / "private", api)
        self.canonical = mock.patch.object(
            self.workflow, "canonical_head", side_effect=lambda _: self.git("rev-parse", "HEAD")
        )
        self.canonical.start()
        self.addCleanup(self.canonical.stop)
        self.registry = mock.patch.object(
            learning, "registry_store", return_value=learning.Store(self.root / "scheduler-registry")
        )
        self.registry.start()
        self.addCleanup(self.registry.stop)

    def git(self, *args):
        return learning.checked(["git", *args], self.repo)

    def capture(self):
        self.workflow.configure("on", None, None)
        return self.workflow.capture(lesson())

    def prepare(self):
        identifier = self.capture()
        preview = self.workflow.preview(identifier)
        return identifier, preview

    def approved(self):
        identifier, preview = self.prepare()
        self.workflow.approve(identifier, preview["sha256"])
        self.workflow.configure(None, "on", None)
        return identifier, preview

    def run_quiet(self):
        with contextlib.redirect_stdout(io.StringIO()):
            return self.workflow.run()

    def remote(self, preview):
        """Model gh's remote state, while every local Git commit remains real."""
        prs = []
        calls = []

        def gh(*args):
            calls.append(args)
            if args[:2] == ("pr", "create"):
                item = self.workflow.store.read()["candidates"][preview["package"]["candidate"]]
                prs.append({
                    "url": "https://github.com/example/harness/pull/1", "state": "OPEN",
                    "headRefOid": item["commit"], "title": preview["package"]["title"],
                    "body": preview["package"]["body"],
                    "baseRefName": preview["package"]["destination"]["base"],
                })
                return prs[0]["url"]
            return json.dumps([
                {
                    "html_url": pr["url"], "state": "open" if pr["state"] == "OPEN" else "closed",
                    "merged_at": "2026-01-01T00:00:00Z" if pr["state"] == "MERGED" else None,
                    "head": {
                        "sha": pr["headRefOid"],
                        "repo": {"full_name": preview["package"]["destination"]["push_repository"]},
                    },
                    "title": pr["title"], "body": pr["body"], "base": {"ref": pr["baseRefName"]},
                } for pr in prs
            ])

        original = self.workflow.git
        pushes = []

        def git(*args, **kwargs):
            if args[0] == "push":
                pushes.append(args)
                return ""
            return original(*args, **kwargs)

        return prs, calls, pushes, mock.patch.object(self.workflow, "gh", side_effect=gh), \
            mock.patch.object(self.workflow, "git", side_effect=git)

    def test_capture_requires_opt_in_and_has_no_network(self):
        with self.assertRaisesRegex(learning.LearningError, "disabled"):
            self.workflow.capture(lesson())
        with mock.patch.object(self.workflow, "gh", side_effect=AssertionError("network")):
            identifier = self.capture()
        self.assertEqual(self.workflow.store.read()["candidates"][identifier]["status"], "pending")
        self.assertEqual(self.git("status", "--porcelain"), "")

    def test_clean_seed_supports_detached_ci_checkouts(self):
        self.git("checkout", "--detach")
        for reference in self.git("for-each-ref", "--format=%(refname)",
                                  "refs/heads", "refs/remotes").splitlines():
            self.git("update-ref", "--no-deref", "-d", reference)
        target = self.root / "detached-source-seed"
        clean_seed(self.repo, target)
        self.assertEqual(learning.checked(["git", "branch", "--show-current"], target), "main")
        self.assertEqual(learning.checked(["git", "rev-parse", "HEAD"], target),
                         self.git("rev-parse", "HEAD"))
        self.assertEqual(learning.checked(["git", "rev-parse", "origin/main"], target),
                         self.git("rev-parse", "HEAD"))

    def test_capture_deduplicates_across_process_lifetimes(self):
        identifier = self.capture()
        other = learning.Workflow(self.repo, self.root / "private", api)
        self.assertEqual(other.capture(lesson()), identifier)
        data = other.store.read()
        self.assertEqual(len(data["candidates"]), 1)
        self.assertEqual(data["candidates"][identifier]["seen"], 2)
        self.assertEqual(data["checkpoints"]["correction:candidate"], 2)

    def test_nothing_durable_is_counted_without_a_transcript(self):
        self.workflow.configure("on", None, None)
        self.workflow.capture(nothing="interaction")
        data = self.workflow.store.read()
        self.assertEqual(data["checkpoints"], {"interaction:nothing": 1})
        self.assertEqual(data["candidates"], {})

    def test_schema_and_traversal_rejected(self):
        self.workflow.configure("on", None, None)
        for value in ([], {**lesson(), "transcript": "not allowed"},
                      lesson(namespace="../secrets"), lesson(title="x\ny"),
                      lesson(evidence="x" * 25000), lesson(procedure="")):
            with self.subTest(value=str(value)[:80]), self.assertRaises(learning.LearningError):
                self.workflow.capture(value)
        self.assertEqual(self.workflow.store.read()["candidates"], {})

    def test_hidden_tags_reported_not_silently_removed(self):
        self.workflow.configure("on", None, None)
        with self.assertRaisesRegex(learning.LearningError, "tag-character finding"):
            self.workflow.capture(lesson(procedure="Hidden " + chr(0xE0061)))

    def test_unknown_namespace_rejected(self):
        self.workflow.configure("on", None, None)
        with self.assertRaisesRegex(learning.LearningError, "namespace does not exist"):
            self.workflow.capture(lesson(namespace="nonexistent.namespace"))

    def test_preview_deterministic_and_unmeasured(self):
        identifier, first = self.prepare()
        self.assertEqual(self.workflow.preview(identifier), first)
        package = first["package"]
        self.assertEqual(set(package["files"]).intersection({"bin/aikb.py"}), set())
        claim = next(text for path, text in package["files"].items() if "/claims/" in path)
        self.assertIn('"authority": "hand-authored"', claim)
        self.assertIn('"evidence_class": "reported-summary"', claim)
        self.assertNotIn(str(self.root), claim)
        self.assertEqual(self.git("status", "--porcelain"), "")

    def test_preparation_uses_python39_compatible_text_writes(self):
        shutil.copy2(REPO / "scripts" / "new_claim.py", self.repo / "scripts" / "new_claim.py")
        if self.git("status", "--porcelain"):
            self.git("add", "scripts/new_claim.py")
            self.git("commit", "-m", "Claim writer compatibility fixture")
        identifier = self.capture()
        original = Path.write_text

        def python39_write_text(path, data, encoding=None, errors=None):
            return original(path, data, encoding=encoding, errors=errors)

        with mock.patch.object(Path, "write_text", python39_write_text):
            self.assertIn("package", self.workflow.preview(identifier))

    def test_approval_requires_matching_hash(self):
        identifier, preview = self.prepare()
        with self.assertRaisesRegex(learning.LearningError, "hash mismatch"):
            self.workflow.approve(identifier, "0" * 64)
        self.workflow.approve(identifier, preview["sha256"])

    def test_destination_change_invalidates_approval(self):
        identifier, preview = self.prepare()
        self.git("remote", "add", "fork", "https://github.com/example/ai-knowledge-harness.git")
        self.workflow.configure(None, None, "fork")
        with self.assertRaisesRegex(learning.LearningError, "destination changed"):
            self.workflow.approve(identifier, preview["sha256"])

    def test_changed_file_invalidates_approval(self):
        identifier, preview = self.prepare()
        item = self.workflow.store.read()["candidates"][identifier]
        path = next(p for p in preview["package"]["files"] if "/claims/" in p)
        with (Path(item["worktree"]) / path).open("a", encoding="utf-8") as stream:
            stream.write("Unreviewed\n")
        with self.assertRaisesRegex(learning.LearningError, "content changed"):
            self.workflow.approve(identifier, preview["sha256"])

    def test_extra_executable_file_blocks_submission(self):
        identifier, preview = self.approved()
        item = self.workflow.store.read()["candidates"][identifier]
        (Path(item["worktree"]) / "unreviewed.py").write_text("print('no')\n", encoding="utf-8")
        with mock.patch.object(self.workflow, "gh") as gh:
            self.assertEqual(self.run_quiet(), 1)
            gh.assert_not_called()
        self.assertIn("unreviewed changes", self.workflow.store.read()["candidates"][identifier]["error"])

    def test_fork_destination_is_bound_to_review(self):
        self.git("remote", "rename", "origin", "upstream")
        self.git("remote", "add", "origin", "https://github.com/example/ai-knowledge-harness.git")
        _, preview = self.prepare()
        self.assertEqual(preview["package"]["destination"]["push_repository"], "example/ai-knowledge-harness")
        self.assertEqual(preview["package"]["destination"]["repository"],
                         "venturemavenwill/ai-knowledge-harness")

    def test_unpublished_base_history_never_enters_a_review_package(self):
        identifier = self.capture()
        self.workflow.canonical_head.side_effect = None
        self.workflow.canonical_head.return_value = "0" * 40
        with self.assertRaisesRegex(learning.LearningError, "differs from canonical"):
            self.workflow.preview(identifier)
        self.assertNotIn("worktree", self.workflow.store.read()["candidates"][identifier])

    def test_disabled_worker_never_exports(self):
        _, preview = self.prepare()
        with mock.patch.object(self.workflow, "gh") as gh:
            with self.assertRaisesRegex(learning.LearningError, "publication disabled"):
                self.run_quiet()
            gh.assert_not_called()

    def test_unapproved_candidate_not_committed_or_exported(self):
        identifier, _ = self.prepare()
        self.workflow.configure(None, "on", None)
        with mock.patch.object(self.workflow, "gh") as gh:
            self.assertEqual(self.run_quiet(), 0)
            gh.assert_not_called()
        self.assertNotIn("commit", self.workflow.store.read()["candidates"][identifier])

    def test_real_commit_and_submission_are_idempotent(self):
        identifier, preview = self.approved()
        prs, calls, pushes, gh_patch, git_patch = self.remote(preview)
        with gh_patch, git_patch:
            self.assertEqual(self.run_quiet(), 0)
            self.assertEqual(self.run_quiet(), 0)
            prs[0]["state"] = "MERGED"
            self.assertEqual(self.run_quiet(), 0)
        data = self.workflow.store.read()
        self.assertEqual(data["candidates"][identifier]["status"], "merged")
        self.assertEqual(len(pushes), 1)
        self.assertEqual(sum(args[:2] == ("pr", "create") for args in calls), 1)
        self.assertEqual(self.git("status", "--porcelain"), "")
        item = data["candidates"][identifier]
        self.assertEqual(self.git("rev-list", "--count",
                                 f"{preview['package']['base_commit']}..{item['commit']}"), "1")

    def test_failed_remote_retains_error_and_recovers(self):
        identifier, preview = self.approved()
        with mock.patch.object(self.workflow, "gh", side_effect=learning.LearningError("offline")):
            self.assertEqual(self.run_quiet(), 1)
        item = self.workflow.store.read()["candidates"][identifier]
        self.assertEqual(item["status"], "approved")
        self.assertEqual(item["error"], "offline")
        saved_commit = item["commit"]
        _, _, _, gh_patch, git_patch = self.remote(preview)
        with gh_patch, git_patch:
            self.assertEqual(self.run_quiet(), 0)
        self.assertEqual(self.workflow.store.read()["candidates"][identifier]["commit"], saved_commit)

    def test_crash_after_pr_creation_reconciles_without_republishing(self):
        identifier, preview = self.approved()
        prs, calls, pushes, gh_patch, git_patch = self.remote(preview)
        with gh_patch, git_patch:
            self.assertEqual(self.run_quiet(), 0)
            data = self.workflow.store.read()
            data["candidates"][identifier]["status"] = "approved"
            self.workflow.store.save(data)
            self.assertEqual(self.run_quiet(), 0)
        self.assertEqual(len(pushes), 1)
        self.assertEqual(sum(args[:2] == ("pr", "create") for args in calls), 1)

    def test_push_passes_real_repository_hooks_and_reaches_a_bare_remote(self):
        identifier, preview = self.approved()
        bare = self.root / "receiver.git"
        learning.checked(["git", "init", "--bare", str(bare)], self.repo)
        self.git("config", "core.hooksPath", ".githooks")
        self.git("config", "push.followTags", "true")
        self.git("tag", "-a", "unreviewed-local-note", "-m", "Synthetic unapproved metadata")
        prs, _, _, gh_patch, _ = self.remote(preview)
        original = self.workflow.git

        def local_network(*args, **kwargs):
            if args[0] == "push":
                self.assertIn("--no-follow-tags", args)
                self.assertTrue(args[-1].startswith("refs/aikb-approved/"))
                return original("push", "--no-follow-tags", str(bare), args[-1], **kwargs)
            return original(*args, **kwargs)

        with gh_patch, mock.patch.object(self.workflow, "git", side_effect=local_network):
            self.assertEqual(self.run_quiet(), 0,
                             self.workflow.store.read()["candidates"][identifier].get("error"))
        expected = self.workflow.store.read()["candidates"][identifier]["commit"]
        actual = learning.checked(
            ["git", "--git-dir", str(bare), "rev-parse", preview["package"]["branch"]], self.repo,
        )
        self.assertEqual(actual, expected)
        self.assertEqual(len(prs), 1)
        self.assertEqual(learning.checked(
            ["git", "--git-dir", str(bare), "tag", "--list"], self.repo), "")

    def test_mixed_case_fork_identity_is_discovered(self):
        _, preview = self.prepare()
        destination = preview["package"]["destination"]["push_repository"]
        record = {
            "html_url": "https://github.com/example/harness/pull/1", "state": "open",
            "merged_at": None, "head": {"sha": "a" * 40, "repo": {"full_name": destination.upper()}},
            "title": preview["package"]["title"], "body": preview["package"]["body"],
            "base": {"ref": "main"},
        }
        with mock.patch.object(self.workflow, "gh", return_value=json.dumps([record])):
            self.assertEqual(len(self.workflow.pull_request(preview["package"])), 1)

    def test_approved_source_ref_uses_preparation_clone_when_worker_uses_another_clone(self):
        identifier, preview = self.approved()
        other_repo = self.root / "other-clone"
        shutil.copytree(self.seed, other_repo)
        other = learning.Workflow(other_repo, self.workflow.store.root, api)
        # Both clones have the same public destination but different Git databases.
        subprocess.run(
            ["git", "remote", "set-url", "origin",
             "https://github.com/venturemavenwill/ai-knowledge-harness.git"],
            cwd=other_repo, check=True, capture_output=True,
        )
        self.workflow, original = other, self.workflow
        try:
            _, _, _, other_gh, other_git = self.remote(preview)
            with other_gh, other_git:
                self.assertEqual(self.run_quiet(), 0,
                                 other.store.read()["candidates"][identifier].get("error"))
        finally:
            self.workflow = original

    def test_changed_pr_text_cannot_spend_an_old_approval(self):
        identifier, _ = self.approved()
        data = self.workflow.store.read()
        data["candidates"][identifier]["package"]["body"] += "\nUnreviewed text"
        self.workflow.store.save(data)
        with mock.patch.object(self.workflow, "gh") as gh:
            self.assertEqual(self.run_quiet(), 1)
            gh.assert_not_called()
        self.assertIn("approval", self.workflow.store.read()["candidates"][identifier]["error"])

    def test_crash_after_commit_before_receipt_recovers_exact_commit(self):
        identifier, preview = self.approved()
        with mock.patch.object(self.workflow, "gh", side_effect=learning.LearningError("offline")):
            self.assertEqual(self.run_quiet(), 1)
        data = self.workflow.store.read()
        expected = data["candidates"][identifier].pop("commit")
        self.workflow.store.save(data)
        _, _, _, gh_patch, git_patch = self.remote(preview)
        with gh_patch, git_patch:
            self.assertEqual(self.run_quiet(), 0)
        self.assertEqual(self.workflow.store.read()["candidates"][identifier]["commit"], expected)

    def test_bounded_passes_rotate_instead_of_starving_later_candidates(self):
        self.workflow.configure("on", "on", None)
        identifiers = [
            self.workflow.capture(lesson(title=f"Lesson {number}")) for number in range(6)
        ]
        data = self.workflow.store.read()
        for identifier in identifiers:
            data["candidates"][identifier].update(status="submitted", package={"candidate": identifier})
        self.workflow.store.save(data)
        seen = []

        def reconcile(package):
            seen.append(package["candidate"])
            return []

        with mock.patch.object(self.workflow, "pull_request", side_effect=reconcile):
            self.assertEqual(self.run_quiet(), 0)
            self.assertEqual(len(seen), 5)
            self.assertEqual(self.run_quiet(), 0)
        self.assertEqual(set(seen), set(identifiers))

    def test_refresh_preserves_old_worktree_and_requires_new_approval(self):
        identifier, preview = self.approved()
        old = self.workflow.store.read()["candidates"][identifier]["worktree"]
        refreshed = self.workflow.preview(identifier, refresh=True)
        self.assertNotEqual(preview["sha256"], refreshed["sha256"])
        self.assertTrue(Path(old).is_dir())
        item = self.workflow.store.read()["candidates"][identifier]
        self.assertNotIn("approval", item)
        self.assertEqual(item["status"], "prepared")

    def test_process_lock_refuses_second_worker(self):
        with self.workflow.store.locked():
            with self.assertRaisesRegex(learning.LearningError, "busy"):
                with learning.Store(self.workflow.store.root).locked():
                    self.fail("concurrent writer admitted")
        with self.workflow.store.locked():
            pass

    def test_corrupt_state_not_overwritten(self):
        self.workflow.store.root.mkdir(parents=True)
        self.workflow.store.path.write_text("{broken", encoding="utf-8")
        with self.assertRaises(ValueError):
            self.workflow.configure("on", None, None)
        self.assertEqual(self.workflow.store.path.read_text(encoding="utf-8"), "{broken")

    def test_structurally_invalid_state_is_preserved_with_a_characterized_error(self):
        self.capture()
        data = self.workflow.store.read()
        data["candidates"]["invalid"] = {"status": []}
        self.workflow.store.save(data)
        original = self.workflow.store.path.read_bytes()
        with self.assertRaisesRegex(learning.LearningError, "invalid candidate record"):
            self.workflow.store.read()
        self.assertEqual(self.workflow.store.path.read_bytes(), original)

    def test_schedule_requires_opt_in_before_os_commands(self):
        with mock.patch.object(learning, "checked", side_effect=AssertionError("OS mutation")):
            with self.assertRaisesRegex(learning.LearningError, "enable publication"):
                learning.schedule(self.workflow, "install", 60)

    def test_schedule_removal_stops_worker_before_waiting_for_its_inbox_lock(self):
        self.workflow.configure(None, "on", None)
        data = self.workflow.store.read()
        data["scheduler"] = {"state": "installed"}
        self.workflow.store.save(data)
        events = []

        @contextlib.contextmanager
        def occupied(*args, **kwargs):
            events.append("lock")
            raise learning.LearningError("inbox busy")
            yield

        def stop(*args):
            events.append("stop")
            return {"action": "remove"}

        with mock.patch.object(self.workflow.store, "locked", side_effect=occupied), \
                mock.patch.object(learning, "native_schedule", side_effect=stop):
            with self.assertRaisesRegex(learning.LearningError, "busy"):
                learning.schedule(self.workflow, "remove", 60)
        self.assertEqual(events, ["stop", "lock"])

    def test_uninstall_removes_all_stores_owned_by_the_installation(self):
        self.workflow.configure(None, "on", None)
        custom = learning.Workflow(self.repo, self.root / "custom-private", api)
        custom.configure(None, "on", None)
        calls = []

        def native(workflow, action, minutes):
            calls.append((workflow.store.root, action))
            return {"name": str(workflow.store.root), "action": action, "minutes": minutes}

        with mock.patch.object(learning, "native_schedule", side_effect=native):
            learning.schedule(self.workflow, "install", 60)
            learning.schedule(custom, "install", 60)
            learning.schedule(self.workflow, "uninstall", 60)
        removed = {root for root, action in calls if action == "remove"}
        self.assertEqual(removed, {self.workflow.store.root, custom.store.root})
        self.assertEqual(learning.installation_schedules(self.workflow), [])

    def test_unconfigured_schedule_status_is_read_only(self):
        with mock.patch.object(learning, "checked", side_effect=AssertionError("OS command")):
            self.assertEqual(learning.schedule(self.workflow, "status", 60),
                             {"state": "not-installed"})
        self.assertFalse(self.workflow.store.root.exists())

    def test_all_platform_schedule_adapters_use_absolute_worker_arguments(self):
        import xml.etree.ElementTree as ET
        import plistlib
        self.workflow.configure(None, "on", None)
        for platform in ("windows", "darwin", "linux"):
            calls = []

            def checked(argv, cwd, **kwargs):
                calls.append(argv)
                if argv[0] == "whoami":
                    return '"Test User","S-1-5-21-123"'
                return "native scheduler accepted"

            original = learning.checked

            def routed(argv, cwd, **kwargs):
                return original(argv, cwd, **kwargs) if argv[0] == "git" else checked(argv, cwd, **kwargs)

            with mock.patch.object(learning, "checked", side_effect=routed), \
                    mock.patch.object(Path, "home", return_value=self.root), \
                    mock.patch.object(learning.os, "getuid", return_value=1000, create=True):
                result = learning.native_schedule(self.workflow, "install", 60, platform=platform)
            if platform == "windows":
                document = ET.parse(self.workflow.store.root / "schedule.xml")
                self.assertTrue((self.workflow.store.root / "schedule.xml").read_bytes().startswith(b"\xff\xfe"))
                ns = {"t": "http://schemas.microsoft.com/windows/2004/02/mit/task"}
                self.assertEqual(document.find(".//t:Command", ns).text, sys.executable)
                self.assertIn(str(self.repo), document.find(".//t:Arguments", ns).text)
                self.assertEqual(document.find(".//t:UserId", ns).text, "S-1-5-21-123")
            elif platform == "darwin":
                value = plistlib.loads((self.root / "Library" / "LaunchAgents" /
                                       (result["name"] + ".plist")).read_bytes())
                self.assertEqual(value["ProgramArguments"][0], sys.executable)
                self.assertIn(str(self.repo), value["ProgramArguments"])
                self.assertEqual(value["StartInterval"], 3600)
            else:
                value = (self.root / ".config" / "systemd" / "user" /
                         (result["name"] + ".service")).read_text(encoding="utf-8")
                self.assertIn("learn", value)
                self.assertIn("run", value)
                self.assertTrue(any(call[:4] == ["systemctl", "--user", "enable", "--now"]
                                    for call in calls))
            with mock.patch.object(learning, "checked", side_effect=routed), \
                    mock.patch.object(Path, "home", return_value=self.root), \
                    mock.patch.object(learning.os, "getuid", return_value=1000, create=True):
                learning.native_schedule(self.workflow, "remove", 60, platform=platform)
            if platform == "windows":
                self.assertTrue(any(call[0] == "powershell.exe" and "$t.Stop(0)" in call[-1]
                                    for call in calls))
            elif platform == "linux":
                self.assertTrue(any(call[:3] == ["systemctl", "--user", "stop"] for call in calls))

    @unittest.skipUnless(os.name == "nt" and os.environ.get("AIKB_TEST_NATIVE_SCHEDULER") == "1",
                         "explicit opt-in required for real Task Scheduler integration")
    def test_native_windows_schedule_runs_the_actual_worker(self):
        for relative in ("bin/aikb.py", "scripts/learning.py"):
            shutil.copy2(REPO / relative, self.repo / relative)
        self.git("add", "bin/aikb.py", "scripts/learning.py")
        if self.git("status", "--porcelain"):
            self.git("commit", "-m", "Local worker integration fixture")
        self.workflow.configure(None, "on", None)
        try:
            task = learning.schedule(self.workflow, "install", 60)
            learning.checked(["schtasks", "/Run", "/TN", task["name"]], self.repo)
            deadline = time.monotonic() + 90
            while self.workflow.store.read()["last_run"] is None and time.monotonic() < deadline:
                time.sleep(1)
            receipt = self.workflow.store.read()["last_run"]
            self.assertIsNotNone(receipt)
            self.assertEqual(receipt["failures"], 0)
        finally:
            learning.schedule(self.workflow, "uninstall", 60)

    @unittest.skipUnless(os.name == "nt" and os.environ.get("AIKB_TEST_NATIVE_SCHEDULER") == "1",
                         "explicit opt-in required for real Task Scheduler integration")
    def test_native_windows_uninstall_stops_a_locked_worker_and_all_custom_stores(self):
        import xml.etree.ElementTree as ET
        self.workflow.configure(None, "on", None)
        custom = learning.Workflow(self.repo, self.root / "custom-private", api)
        custom.configure(None, "on", None)
        try:
            learning.schedule(self.workflow, "install", 60)
            task = learning.schedule(custom, "install", 60)
            held = self.root / "lock-acquired.txt"
            code = (
                "import sys,time;from pathlib import Path;"
                f"sys.path.insert(0,{str(REPO / 'scripts')!r});from learning import Store\n"
                f"with Store(Path({str(custom.store.root)!r})).locked():\n"
                f" Path({str(held)!r}).write_text('held');time.sleep(120)"
            )
            path = custom.store.root / "schedule.xml"
            document = ET.parse(path)
            ns = {"t": "http://schemas.microsoft.com/windows/2004/02/mit/task"}
            document.find(".//t:Arguments", ns).text = subprocess.list2cmdline(["-c", code])
            document.write(path, encoding="utf-16", xml_declaration=True)
            learning.checked(["schtasks", "/Create", "/TN", task["name"],
                              "/XML", str(path), "/F"], self.repo)
            learning.checked(["schtasks", "/Run", "/TN", task["name"]], self.repo)
            deadline = time.monotonic() + 60
            while not held.exists() and time.monotonic() < deadline:
                time.sleep(1)
            self.assertTrue(held.exists(), "the scheduled probe did not acquire its lock")
            result = learning.schedule(self.workflow, "uninstall", 60)
            self.assertEqual(len(result["schedules"]), 2)
            self.assertEqual(learning.installation_schedules(self.workflow), [])
            self.assertIsNone(custom.store.read()["scheduler"])
        finally:
            learning.schedule(self.workflow, "uninstall", 60)
