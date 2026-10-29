#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2025-2026 Zhanpeng Huang
# SPDX-License-Identifier: GPL-3.0-only
# See LICENSE and LICENSING.md in the repository root.
"""Check that both emulators write complete EZCOV records on input exhaustion."""

import argparse
import json
import os
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RECORD = re.compile(r"0x[0-9a-fA-F]+,\s*[1-9][0-9]*,\s*\[\s*\]")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True,
                        help="new directory in which to retain inputs, logs and coverage")
    args = parser.parse_args()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    config = output / "config.json"
    subprocess.run(
        ["python3", str(ROOT / "utils/prepare_config.py"),
         str(ROOT / "fw-example/nucleo753zi/aflConfiguration.json"), str(config)],
        check=True,
    )
    cases = {"a81": b"A" * 80 + b"\n", "zero81": bytes(81), "sequence80": bytes(range(80))}
    engines = (
        ("triforce-qemu", "rehost-fuzzing", "-aflFile", "afl_fuzzing_log"),
        ("concolic-executor", "concolic-execution", "-replayFile", "concolic_replay"),
    )
    results = []
    for name, data in cases.items():
        case = output / name
        case.mkdir()
        seed = case / "input"
        seed.write_bytes(data)
        traces = []
        for engine, machine, input_option, log_flag in engines:
            folder = case / engine
            folder.mkdir()
            solver = folder / "solver"
            solver.mkdir()
            coverage = folder / "coverage.ezcov"
            trace = folder / "trace.log"
            traces.append(trace)
            command = [
                str(ROOT / engine / "build/qemu-system-arm"),
                "-M", machine, "-display", "none", "-kernel", str(config),
                input_option, str(seed), "-d", log_flag, "-D", str(trace),
                "-covFile", str(coverage),
            ]
            with (folder / "stdout.log").open("wb") as stdout, (folder / "stderr.log").open("wb") as stderr:
                subprocess.run(
                    command, check=True, timeout=30, cwd=ROOT, stdout=stdout, stderr=stderr,
                    env=dict(os.environ, SYMCC_MEMORY_INPUT="1", SYMCC_OUTPUT_DIR=str(solver)),
                )
            raw = coverage.read_bytes()
            lines = raw.decode().splitlines()
            if not raw.endswith(b"\n") or len(lines) < 2 or lines[0] != "EZCOV VERSION: 1":
                raise RuntimeError(f"Missing or truncated coverage: {coverage}")
            if not all(RECORD.fullmatch(line) for line in lines[1:]):
                raise RuntimeError(f"Malformed EZCOV record: {coverage}")
            results.append({"input": name, "engine": engine, "bytes": len(raw), "records": len(lines) - 1})
        subprocess.run(
            ["bash", str(ROOT / "utils/single_compare_test_case.sh"), *map(str, traces)],
            check=True,
        )
    (output / "summary.json").write_text(json.dumps(results, indent=2) + "\n")
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
