#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2025-2026 Zhanpeng Huang
# SPDX-License-Identifier: GPL-3.0-only
# See LICENSE and LICENSING.md in the repository root.
"""Check the "boot" configuration section in both emulators (STM32H7S78-DK example)."""

import argparse
import json
import os
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "fw-example/stm32h7s78-dk"
ENGINES = (
    ("triforce-qemu", "rehost-fuzzing", "-aflFile", "afl_fuzzing_log"),
    ("concolic-executor", "concolic-execution", "-replayFile", "concolic_replay"),
)
BOOT_BYTES = 1660                       # the 0xfc input reaches boot.target here
TAPE = re.compile(r"(input|boot)\[(\d+)(?:\.\.(\d+))?\]\s+(.*)")


def run(case, engine, config, seed):
    """Run one input; return (exit code, stderr, tape lines, whole log)."""
    name, machine, input_option, log_flag = engine
    folder = case / name
    folder.mkdir(parents=True)
    log = folder / "trace.log"
    result = subprocess.run(
        [str(ROOT / name / "build/qemu-system-arm"), "-M", machine, "-display", "none",
         "-kernel", str(config), input_option, str(seed), "-d", log_flag, "-D", str(log)],
        timeout=120, cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True,
        env=dict(os.environ, SYMCC_MEMORY_INPUT="1", SYMCC_OUTPUT_DIR=str(folder)),
    )
    text = log.read_text(errors="replace") if log.exists() else ""
    tape = [m.groups() for m in map(TAPE.match, text.splitlines()) if m]
    return result.returncode, result.stderr, tape, text


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True,
                        help="new directory in which to keep configurations, inputs and logs")
    out = parser.parse_args().output.resolve()
    out.mkdir(parents=True, exist_ok=False)

    base = json.loads((EXAMPLE / "aflConfigurationBoot.json").read_text())
    base["flash"][0]["file"] = str(EXAMPLE / "stm32h7s78-dk.bin")
    base["symbols"] = str(EXAMPLE / "stm32h7s78-dk.syms")

    def config(name, **boot):
        """The example configuration with `boot` keys replaced (None removes one)."""
        conf = json.loads(json.dumps(base))
        conf["boot"]["input"] = str(EXAMPLE / "boot.bin")
        for key, value in boot.items():
            if value is None:
                del conf["boot"][key]
            else:
                conf["boot"][key] = value
        path = out / f"{name}.json"
        path.write_text(json.dumps(conf, indent=2) + "\n")
        return path

    def data(name, content):
        path = out / name
        path.write_bytes(content)
        return path

    whole = data("whole", b"\xfc" * 4096)               # boot bytes, then loop bytes
    after = data("after", b"\xfc" * (4096 - BOOT_BYTES))    # the loop bytes alone
    passed = failed = 0

    def check(what, ok):
        nonlocal passed, failed
        passed, failed = passed + bool(ok), failed + (not ok)
        print(f"{'ok  ' if ok else 'FAIL'} {what}")

    for engine in ENGINES:
        name = engine[0]
        # Without boot.input: the run is judged, and nothing else changes.
        code, _, plain, log = run(out / "judge", engine, config("judge", input=None), whole)
        check(f"{name}: a good boot is reported at input[{BOOT_BYTES}]",
              code == 0 and f"passed boot at input[{BOOT_BYTES}]: all required" in log)
        _, _, _, log = run(out / "judge-bad", engine, config("judge-bad", input=None),
                           data("ff", b"\xff" * 4096))
        check(f"{name}: a failed boot is reported", "failed boot at input[" in log)

        # With boot.input: boot[...] reads, then the same tape as before, from input[0].
        code, _, tape, _ = run(out / "boot", engine, config("boot"), after)
        shifted = [("input", str(int(a) - BOOT_BYTES), b and str(int(b) - BOOT_BYTES), rest)
                   for _, a, b, rest in plain if int(a) >= BOOT_BYTES]
        check(f"{name}: boot reads come from boot.input",
              code == 0 and [t[0] for t in tape[:415]] == ["boot"] * 415)
        check(f"{name}: after boot, the tape starts at input[0] and is unchanged",
              [t for t in tape if t[0] == "input"] == shifted and len(shifted) > 0)

        # A boot input that does not fit stops the engine and says why.
        for case, boot, message in (
            ("avoid", {"input": str(data("ff.bin", b"\xff" * 4096))}, "reached avoid address"),
            ("required", {"required": ["HAL_UART_Receive"]}, "without required address"),
            ("short", {"input": str(data("short.bin", b"\xfc" * 1200))}, "ran out before"),
            ("missing", {"input": str(out / "no-such-file")}, "cannot read"),
            ("typo", {"requried": []}, "unknown key"),
            ("no-target", {"target": None}, '"target" is missing'),
        ):
            code, stderr, _, _ = run(out / case, engine, config(case, **boot), after)
            check(f"{name}: {case}: exit 1 with \"{message}\"", code == 1 and message in stderr)

    print(f"{passed} passed, {failed} failed; files kept in {out}")
    raise SystemExit(1 if failed else 0)


if __name__ == "__main__":
    main()
