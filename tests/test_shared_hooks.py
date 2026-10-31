# SPDX-FileCopyrightText: 2025-2026 Zhanpeng Huang
# SPDX-License-Identifier: GPL-3.0-only
# See LICENSE and LICENSING.md in the repository root.
"""Exercise the hook revision guard with real, isolated Git repositories."""

from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


CHECK = Path(__file__).resolve().parents[1] / "utils/check_shared_hooks.py"


class SharedHookRevisionTests(unittest.TestCase):
    def git(self, path, *args):
        return subprocess.run(
            ["git", "-C", str(path), "-c", "user.name=Hook Test",
             "-c", "user.email=hook-test@example.invalid", *args],
            check=True, text=True, capture_output=True,
        ).stdout.strip()

    def commit(self, path):
        self.git(path, "add", ".")
        self.git(path, "commit", "-qm", "Test snapshot")
        return self.git(path, "rev-parse", "HEAD")

    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="shared hook test ")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        source = self.root / "source"
        source.mkdir()
        self.git(source, "init", "-q")
        (source / "hook.c").write_text("/* first implementation */\n")
        (source / ".gitignore").write_text("*.o\n")
        self.first = self.commit(source)
        (source / "hook.c").write_text("/* second implementation */\n")
        self.second = self.commit(source)
        self.engines = []
        for name in ("triforce-qemu", "concolic-executor"):
            engine = self.root / name
            engine.mkdir()
            self.git(engine, "init", "-q")
            self.git(engine, "-c", "protocol.file.allow=always", "submodule",
                     "add", "-q", str(source), "hooks")
            self.git(engine / "hooks", "checkout", "-q", self.first)
            self.commit(engine)
            self.engines.append(engine)

    def check(self):
        return subprocess.run(
            [sys.executable, str(CHECK), "--root", str(self.root)],
            capture_output=True, text=True,
        )

    def assert_rejected(self, reason):
        result = self.check()
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn(reason, result.stderr)

    def test_identical_clean_pins_are_accepted(self):
        result = self.check()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(self.first, result.stdout)

    def test_different_committed_pins_are_rejected(self):
        self.git(self.engines[1] / "hooks", "checkout", "-q", self.second)
        self.commit(self.engines[1])
        self.assert_rejected("shared hook revisions differ")

    def test_checkout_drift_is_rejected(self):
        self.git(self.engines[1] / "hooks", "checkout", "-q", self.second)
        self.assert_rejected("differs from recorded revision")

    def test_staged_pin_change_is_rejected(self):
        self.git(self.engines[1] / "hooks", "checkout", "-q", self.second)
        self.git(self.engines[1], "add", "hooks")
        self.assert_rejected("commit the staged hooks revision")

    def test_uninitialized_submodule_does_not_use_parent_head(self):
        self.git(self.engines[1], "submodule", "deinit", "-f", "--", "hooks")
        self.assert_rejected("submodule is not initialized")

    def test_missing_gitlink_is_rejected(self):
        self.git(self.engines[1], "rm", "-f", "hooks")
        self.commit(self.engines[1])
        self.assert_rejected("HEAD must record hooks as a Git submodule")

    def test_unstaged_hook_edit_is_rejected(self):
        (self.engines[0] / "hooks/hook.c").write_text("/* local change */\n")
        self.assert_rejected("uncommitted or untracked files")

    def test_staged_hook_edit_is_rejected(self):
        (self.engines[0] / "hooks/hook.c").write_text("/* staged change */\n")
        self.git(self.engines[0] / "hooks", "add", "hook.c")
        self.assert_rejected("uncommitted or untracked files")

    def test_untracked_header_is_rejected(self):
        (self.engines[0] / "hooks/shadow.h").write_text("/* untracked header */\n")
        self.assert_rejected("uncommitted or untracked files")

    def test_ignored_build_artifact_is_allowed(self):
        (self.engines[0] / "hooks/hook.o").write_bytes(b"object")
        result = self.check()
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
