#!/bin/bash


if [[ $# -ne 2 ]]; then
    echo "Usage: $0 <test_case_folder> <binary_conf>"
    exit 1
fi

if [ ! -f "./TriforceQEMU/build/qemu-system-arm" ]; then

  echo "[-] Error: ../TriforceQEMU not found - compile first! or run the script in the same folder where TriforceQEMU lies at"
  exit 1
fi


if [ ! -f "./concolic-replay/build/qemu-system-arm" ]; then

  echo "[-] Error: ../concolic-replay not found - compile first! or run the script in the same folder where concolic-replay lies at"
  exit 1
fi

if [ ! -d "$1" ]; then
  echo "[-] Error: queue folder not found"
  exit 1
fi


if [ ! -f "$2" ]; then
  echo "[-] Error: binary configuration file not found"
  exit 1
fi



logfile="compare.log"
> "$logfile"

TEST_DIR="$1"
DIFF_COUNT=0

extract_addrs() {
    local file="$1"
    grep "\[cpu_tb_exec\] executed at" "$file" \
        | awk '{print $4}' \
        | sed 's/\.\.\.$//'
}

echo "=== Running comparison over test cases in: $TEST_DIR ==="
echo ""

files=("$TEST_DIR"/*)        # expand glob into array
total=${#files[@]}    # count files

count=0

for cur_input in "$TEST_DIR"/*; do
    # echo "[*] Processing: $cur_input"

    ((count++))
    percent=$(( 100 * count / total ))
    bar_len=$(( percent / 2 ))
    printf "\r[%-50s] %3d%% (%d/%d)" \
                "$(printf '#%.0s' $(seq 1 $bar_len))" \
                "$percent" "$count" "$total"

    # Run TriforceQEMU
    ./TriforceQEMU/build/qemu-system-arm \
        -M rehost-fuzzing \
        -display none \
        -kernel "$2" \
        -aflFile "$cur_input" \
        -D qemu.log \
        -d afl_fuzzing_log \
        &>/dev/null

    # Run concolic executor
    SYMCC_OUTPUT_DIR="/tmp/output/" SYMCC_MEMORY_INPUT="1" ./concolic-replay/build/qemu-system-arm \
        -M concolic-execution \
        -display none \
        -kernel "$2" \
        -replayFile "$cur_input" \
        -D qemu1.log \
        -d concolic_replay \
        &>/dev/null

    # Extract BB sequences to temp files
    TMP1=$(mktemp)
    TMP2=$(mktemp)

    extract_addrs qemu.log  > "$TMP1"
    extract_addrs qemu1.log > "$TMP2"

    # Compare
    if ! cmp -s "$TMP1" "$TMP2"; then
        echo "❌ BB difference detected for test: $cur_input" >> "$logfile"
        DIFF_COUNT=$((DIFF_COUNT + 1))
    fi

    rm -f "$TMP1" "$TMP2"
done

echo "=== Summary ==="
if [[ $DIFF_COUNT -eq 0 ]]; then
    echo "All test cases match."
else
    echo "$DIFF_COUNT test case(s) have differences."
fi

