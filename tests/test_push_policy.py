from __future__ import annotations

import subprocess
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
POLICY = REPO / "scripts" / "check_push_policy.py"
OID = "1" * 40
ZERO = "0" * 40


def run_policy(updates: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(POLICY), "--repo", str(REPO)],
        input=updates,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=15,
    )


class PushPolicyTests(unittest.TestCase):
    def test_feature_branch_push_is_allowed(self) -> None:
        result = run_policy(
            f"refs/heads/improvement/routing-gap {OID} "
            f"refs/heads/improvement/routing-gap {ZERO}\n"
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_default_branch_update_is_blocked(self) -> None:
        result = run_policy(f"refs/heads/main {OID} refs/heads/main {OID}\n")
        self.assertEqual(result.returncode, 1)
        self.assertIn("direct update of refs/heads/main", result.stderr)
        self.assertIn("pull request", result.stderr)

    def test_default_branch_deletion_is_blocked(self) -> None:
        result = run_policy(f"(delete) {ZERO} refs/heads/main {OID}\n")
        self.assertEqual(result.returncode, 1)
        self.assertIn("direct delete of refs/heads/main", result.stderr)

    def test_malformed_hook_input_fails_closed(self) -> None:
        result = run_policy("not a valid update\n")
        self.assertEqual(result.returncode, 1)
        self.assertIn("malformed pre-push input", result.stderr)


if __name__ == "__main__":
    unittest.main()
