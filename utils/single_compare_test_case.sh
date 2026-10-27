#!/usr/bin/env bash
# SPDX-FileCopyrightText: 2025-2026 Zhanpeng Huang
# SPDX-License-Identifier: GPL-3.0-only
# See LICENSE and LICENSING.md in the repository root.
set -euo pipefail

if [[ $# -ne 2 ]]; then
    echo "Usage: $0 <fuzzer-log> <concolic-log>" >&2
    exit 2
fi
for log in "$@"; do
    if [[ ! -f "$log" || ! -r "$log" ]]; then
        echo "Error: cannot read log: $log" >&2
        exit 2
    fi
done

TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT
extract_addrs() {
    awk '/\[arm_helper_func\] executing at|\[cpu_tb_exec\] executed at/ {
        address = $4
        sub(/\.\.\.$/, "", address)
        if (address !~ /^0x[0-9a-fA-F]+$/) {
            print "Error: malformed execution address" > "/dev/stderr"
            exit 2
        }
        print tolower(address)
    }' "$1"
}
extract_addrs "$1" > "$TMP/fuzzer"
extract_addrs "$2" > "$TMP/concolic"

for trace in "$TMP/fuzzer" "$TMP/concolic"; do
    if [[ ! -s "$trace" ]]; then
        echo "Error: missing execution trace; empty logs do not establish agreement." >&2
        exit 2
    fi
done

if diff -u "$TMP/fuzzer" "$TMP/concolic"; then
    echo "Both logs contain the same ordered translation-block start addresses."
else
    echo "Translation-block address sequences differ." >&2
    exit 1
fi
