#!/usr/bin/env bash
set -euo pipefail

ROOT=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
if [[ $# -ne 2 || ! -d $1 || ! -f $2 ]]; then
    echo "Usage: $0 <test-case-folder> <firmware-config>" >&2
    exit 2
fi
command -v timeout >/dev/null || { echo "Error: GNU timeout is required." >&2; exit 2; }
for emulator in TriforceQEMU concolic-replay; do
    test -x "$ROOT/$emulator/build/qemu-system-arm" || {
        echo "Error: build $emulator first." >&2
        exit 2
    }
done

shopt -s nullglob
inputs=()
for input in "$1"/*; do
    [[ -f $input ]] && inputs+=("$input")
done
if [[ ${#inputs[@]} -eq 0 ]]; then
    echo "Error: no test cases found." >&2
    exit 2
fi

mkdir -p "$ROOT/runs"
OUTPUT=$(mktemp -d "$ROOT/runs/trace-check.XXXXXX")
MATCHES=0
DIFFERENCES=0
ERRORS=0
INDEX=0
for input in "${inputs[@]}"; do
    INDEX=$((INDEX + 1))
    CASE="$OUTPUT/$INDEX"
    mkdir -p "$CASE/solver"
    printf '%s\n' "$input" > "$CASE/input-path.txt"
    if ! timeout -k 5 "${TRACE_TIMEOUT_SECONDS:-30}" \
        "$ROOT/TriforceQEMU/build/qemu-system-arm" \
        -M rehost-fuzzing -display none -kernel "$2" -aflFile "$input" \
        -D "$CASE/fuzzer.log" -d afl_fuzzing_log > "$CASE/fuzzer.stdout" 2> "$CASE/fuzzer.stderr"; then
        echo "Error: fuzzer execution failed or timed out for $input" >&2
        ERRORS=$((ERRORS + 1))
        continue
    fi
    if ! SYMCC_OUTPUT_DIR="$CASE/solver" SYMCC_MEMORY_INPUT=1 \
        timeout -k 5 "${TRACE_TIMEOUT_SECONDS:-30}" \
        "$ROOT/concolic-replay/build/qemu-system-arm" \
        -M concolic-execution -display none -kernel "$2" -replayFile "$input" \
        -D "$CASE/concolic.log" -d concolic_replay > "$CASE/concolic.stdout" 2> "$CASE/concolic.stderr"; then
        echo "Error: concolic execution failed or timed out for $input" >&2
        ERRORS=$((ERRORS + 1))
        continue
    fi
    if "$ROOT/utils/single_compare_test_case.sh" "$CASE/fuzzer.log" "$CASE/concolic.log" > "$CASE/comparison.txt" 2>&1; then
        MATCHES=$((MATCHES + 1))
    else
        status=$?
        if [[ $status -eq 1 ]]; then
            DIFFERENCES=$((DIFFERENCES + 1))
        else
            ERRORS=$((ERRORS + 1))
        fi
    fi
done
echo "Matched: $MATCHES; different: $DIFFERENCES; errors: $ERRORS; total: ${#inputs[@]}"
echo "Per-input logs: $OUTPUT"
[[ $ERRORS -eq 0 ]] || exit 2
[[ $DIFFERENCES -eq 0 ]] || exit 1

