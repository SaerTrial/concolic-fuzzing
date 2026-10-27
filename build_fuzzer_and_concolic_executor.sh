#!/usr/bin/env bash
# SPDX-FileCopyrightText: 2025-2026 Zhanpeng Huang
# SPDX-License-Identifier: GPL-3.0-only
# See LICENSE and LICENSING.md in the repository root.
set -euo pipefail

ROOT=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
cd "$ROOT"

if [[ $(uname -s) != Linux ]]; then
    echo "Error: the emulator build requires Linux." >&2
    exit 1
fi

for tool in git make ninja cmake python3 cargo pkg-config cc c++; do
    command -v "$tool" >/dev/null 2>&1 || {
        echo "Error: $tool is required; see README.md." >&2
        exit 1
    }
done

# Keep the emulators at the revisions recorded by the superproject.
git submodule update --init TriforceQEMU concolic-replay
git -C concolic-replay submodule update --init subprojects/symcc-rt
# The Qsym backend links system Z3; its third_party/z3 checkout is not needed.
git -C concolic-replay/subprojects/symcc-rt submodule update --init src/backends/qsym/qsym

# Pin both the release name and its commit.
AFL_REV=474ff18ba2a7999a518a4d194fcd5a1f87c3625d
if [[ ! -e AFLplusplus ]]; then
    git clone --depth 1 --branch v4.34c https://github.com/AFLplusplus/AFLplusplus.git AFLplusplus
fi
if [[ $(git -C AFLplusplus rev-parse HEAD) != "$AFL_REV" ]]; then
    echo "Error: AFLplusplus must be at v4.34c ($AFL_REV). Preserve or move your existing checkout first." >&2
    exit 1
fi

# Avoid installing build dependencies into the system Python environment.
python3 -m venv .venv-build
source .venv-build/bin/activate
python -m pip install 'tomli==2.2.1'

# System emulation supplies coverage; AFL compiler instrumentation is not needed.
make -C AFLplusplus -j "${JOBS:-4}" afl-fuzz afl-showmap
test -x AFLplusplus/afl-fuzz
test -x AFLplusplus/afl-showmap

for emulator in TriforceQEMU concolic-replay; do
    echo "Building $emulator..."
    (
        mkdir -p "$emulator/build"
        cd "$emulator/build"
        ../configure \
            --audio-drv-list= \
            --disable-sdl \
            --disable-gtk \
            --disable-vte \
            --disable-opengl \
            --disable-virglrenderer \
            --disable-werror \
            --target-list=arm-softmmu
        ninja -j "${JOBS:-4}"
        test -x qemu-system-arm
    )
done

# Install locally so the README does not depend on a particular shell PATH.
cargo install --locked --path concolic-replay/symcc_fuzzing_helper --root "$ROOT/build/tools"
test -x build/tools/bin/symcc_fuzzing_helper
echo "Build complete. Follow README.md to prepare a configuration and start both processes."
