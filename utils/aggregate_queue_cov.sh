#!/bin/bash

if [[ $# -ne 2 ]]; then
    echo "Usage: $0 <queue_folder> <binary_conf>"
    exit 1
fi

if [ ! -f "./TriforceQEMU/build/qemu-system-arm" ]; then

  echo "[-] Error: ../TriforceQEMU not found - compile first! or run the script in the same folder where TriforceQEMU lies at"
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

count=0

TMP=$(mktemp -d)

files=("$1"/*)        # expand glob into array
total=${#files[@]}    # count files

echo "[-] queue folder: $1, binary configuration file: $2"

for cur_input in "$1"/*; do
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
        -covFile "$TMP//$count.ezcov" \
        &>/dev/null
done
echo ""
echo "[+] Save all cov in $TMP"

OUT="./merged_cov.ezcov"  # final merged file

# Write header once
echo "EZCOV VERSION: 1" > "$OUT"

append_body() {
    local f="$1"
    while IFS= read -r line; do
        [[ "$line" =~ EZCOV ]] && continue
        [[ -z "$line" ]] && continue
        echo "$line" >> "$OUT"
    done < "$f"
}


files=("$TMP"/*)        # expand glob into array
total=${#files[@]}    # count files
count=0

# Loop through all cov files in folder
for f in "$TMP"/*; do
    ((count++))
    percent=$(( 100 * count / total ))
    bar_len=$(( percent / 2 ))
    printf "\r[%-50s] %3d%% (%d/%d)" \
                "$(printf '#%.0s' $(seq 1 $bar_len))" \
                "$percent" "$count" "$total"

    # skip non-files
    [ ! -f "$f" ] && continue

    # append body only
    append_body "$f"
done
echo ""
echo "[+] Merged coverage written to $OUT"

