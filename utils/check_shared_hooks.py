#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2025-2026 Zhanpeng Huang
# SPDX-License-Identifier: GPL-3.0-only
# See LICENSE and LICENSING.md in the repository root.
"""Require both emulators to build the same committed, clean hook sources."""

import argparse
from pathlib import Path
import subprocess
import sys


EMULATORS = ("triforce-qemu", "concolic-executor")


class HookCheckError(Exception):
    """The hook checkouts do not match the recorded build inputs."""


def git(directory, *arguments):
    result = subprocess.run(
        ["git", "-C", str(directory), *arguments],
        capture_output=True, text=True,
    )
    if result.returncode:
        raise HookCheckError(
            f"{directory}: git {' '.join(arguments)} failed: {result.stderr.strip()}"
        )
    return result.stdout.strip()


def require_checkout(directory):
    # Git walks upwards from an empty/uninitialized submodule directory. Do not
    # accidentally accept its parent repository's HEAD as the hook revision.
    if not directory.is_dir():
        raise HookCheckError(f"{directory}: checkout is missing; initialize its submodule")
    top = git(directory, "rev-parse", "--show-toplevel")
    if Path(top).resolve() != directory.resolve():
        raise HookCheckError(f"{directory}: submodule is not initialized")


def check_shared_hooks(root):
    pins = {}
    for emulator in EMULATORS:
        engine = root / emulator
        require_checkout(engine)
        entry = git(engine, "ls-tree", "HEAD", "--", "hooks")
        fields = entry.split()
        if len(fields) != 4 or fields[0:2] != ["160000", "commit"] or fields[3] != "hooks":
            raise HookCheckError(f"{emulator}: HEAD must record hooks as a Git submodule")
        pin = fields[2]
        index = git(engine, "ls-files", "--stage", "--", "hooks").split()
        if index != ["160000", pin, "0", "hooks"]:
            raise HookCheckError(f"{emulator}: commit the staged hooks revision before building")
        hooks = engine / "hooks"
        require_checkout(hooks)
        actual = git(hooks, "rev-parse", "HEAD")
        if actual != pin:
            raise HookCheckError(
                f"{emulator}/hooks: checkout {actual} differs from recorded revision {pin}; "
                f"run git -C {emulator} submodule update --init hooks"
            )
        if git(hooks, "status", "--porcelain=v1", "--untracked-files=normal",
               "--ignore-submodules=none"):
            raise HookCheckError(
                f"{emulator}/hooks: uncommitted or untracked files; commit the intended "
                "hook changes and update both emulator pins before building"
            )
        pins[emulator] = pin
    if len(set(pins.values())) != 1:
        revisions = ", ".join(f"{name}={pin}" for name, pin in pins.items())
        raise HookCheckError(f"shared hook revisions differ: {revisions}")
    return next(iter(pins.values()))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root", type=Path, default=Path(__file__).resolve().parents[1],
        help="superproject checkout (defaults to this script's repository)",
    )
    args = parser.parse_args()
    try:
        revision = check_shared_hooks(args.root.resolve())
    except (HookCheckError, OSError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1
    print(f"Shared hooks verified: {revision}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
