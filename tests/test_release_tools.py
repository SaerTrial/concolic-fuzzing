# SPDX-FileCopyrightText: 2025-2026 Zhanpeng Huang
# SPDX-License-Identifier: GPL-3.0-only
# See LICENSE and LICENSING.md in the repository root.
"""Regression checks for release tooling; these do not emulate firmware."""
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class TraceComparisonTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.directory = Path(self.tmp.name)

    def compare(self, left, right):
        a, b = self.directory / "left.log", self.directory / "right.log"
        a.write_text(left)
        b.write_text(right)
        return subprocess.run(
            ["bash", str(ROOT / "utils/single_compare_test_case.sh"), str(a), str(b)],
            capture_output=True, text=True,
        )

    def test_current_marker_matches_legacy_marker(self):
        result = self.compare(
            "[arm_helper_func] executing at 0x8001234 ...\n",
            "[cpu_tb_exec] executed at 0x8001234...\n",
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_empty_logs_are_errors(self):
        self.assertEqual(self.compare("", "").returncode, 2)

    def test_unrelated_logs_are_errors(self):
        self.assertEqual(self.compare("initialized\n", "initialized\n").returncode, 2)

    def test_one_empty_trace_is_error(self):
        self.assertEqual(self.compare("[arm_helper_func] executing at 0x8001234 ...\n", "").returncode, 2)

    def test_malformed_addresses_are_errors(self):
        line = "[arm_helper_func] executing at invalid ...\n"
        self.assertEqual(self.compare(line, line).returncode, 2)

    def test_order_and_repetition_are_preserved(self):
        a = "[arm_helper_func] executing at 0x8001234 ...\n"
        b = "[arm_helper_func] executing at 0x8005678 ...\n"
        self.assertEqual(self.compare(a + b, b + a).returncode, 1)
        self.assertEqual(self.compare(a + a, a).returncode, 1)

    def test_missing_files_are_errors(self):
        result = subprocess.run(
            ["bash", str(ROOT / "utils/single_compare_test_case.sh"),
             str(self.directory / "missing"), str(self.directory / "also-missing")],
            capture_output=True,
        )
        self.assertEqual(result.returncode, 2)


class ConfigTests(unittest.TestCase):
    def test_paths_are_relative_to_config_not_working_directory(self):
        with tempfile.TemporaryDirectory(prefix="firmware config ") as directory:
            folder = Path(directory)
            (folder / "firmware.bin").write_bytes(b"test")
            source = folder / "config.json"
            source.write_text(json.dumps({"flash": [{"file": "firmware.bin"}]}))
            output = folder / "generated/config.json"
            result = subprocess.run(
                [sys.executable, str(ROOT / "utils/prepare_config.py"), str(source), str(output)],
                cwd="/", capture_output=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(output.read_text())["flash"][0]["file"],
                             str((folder / "firmware.bin").resolve()))
            self.assertEqual(json.loads(source.read_text())["flash"][0]["file"], "firmware.bin")

    def test_missing_firmware_does_not_write_output(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            source, output = folder / "config.json", folder / "out.json"
            source.write_text(json.dumps({"flash": [{"file": "missing.bin"}]}))
            result = subprocess.run(
                [sys.executable, str(ROOT / "utils/prepare_config.py"), str(source), str(output)],
                capture_output=True,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertFalse(output.exists())


@unittest.skipUnless(shutil.which("timeout"), "GNU timeout is required for the batch runner")
class BatchRunnerTests(unittest.TestCase):
    def run_batch(self, left="0x8001234", right="0x8001234", status=0, seed=True):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "utils").mkdir()
            for name in ("single_compare_test_case.sh", "test_same_exec_flows_over_testset.sh"):
                shutil.copy2(ROOT / "utils" / name, root / "utils" / name)
            (root / "inputs").mkdir()
            if seed:
                (root / "inputs/seed").write_bytes(b"A")
            (root / "config.json").write_text("{}")
            for emulator, address in (("triforce-qemu", left), ("concolic-executor", right)):
                binary = root / emulator / "build/qemu-system-arm"
                binary.parent.mkdir(parents=True)
                binary.write_text(
                    "#!/usr/bin/env python3\nimport sys\nfrom pathlib import Path\n"
                    + f"address = {address!r}\n"
                    + "if address:\n"
                    + " Path(sys.argv[sys.argv.index('-D') + 1]).write_text("
                    + "'[arm_helper_func] executing at ' + address + ' ...\\n')\n"
                    + f"sys.exit({status})\n"
                )
                binary.chmod(0o755)
            return subprocess.run(
                ["bash", str(root / "utils/test_same_exec_flows_over_testset.sh"),
                 str(root / "inputs"), str(root / "config.json")],
                capture_output=True, text=True,
            )

    def test_matching_nonempty_traces(self):
        result = self.run_batch()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Matched: 1; different: 0; errors: 0; total: 1", result.stdout)

    def test_mismatches_fail(self):
        self.assertEqual(self.run_batch(right="0x8005678").returncode, 1)

    def test_failed_emulator_is_error(self):
        self.assertEqual(self.run_batch(status=42).returncode, 2)

    def test_missing_traces_are_errors(self):
        self.assertEqual(self.run_batch(left="", right="").returncode, 2)

    def test_empty_corpus_is_error(self):
        self.assertEqual(self.run_batch(seed=False).returncode, 2)


if __name__ == "__main__":
    unittest.main()
