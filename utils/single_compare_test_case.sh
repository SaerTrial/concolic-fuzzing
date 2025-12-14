#!/bin/bash

# Usage: ./compare_bb.sh <log1> <log2>

if [[ $# -ne 2 ]]; then
    echo "Usage: $0 <log1> <log2>"
    exit 1
fi

LOG1="$1"
LOG2="$2"

extract_addrs() {
    local file="$1"
    grep "\[cpu_tb_exec\] executed at" "$file" \
        | awk '{print $4}' \
        | sed 's/\.\.\.$//'   # remove trailing "..."
}

TMP1=$(mktemp)
TMP2=$(mktemp)

extract_addrs "$LOG1" > "$TMP1"
extract_addrs "$LOG2" > "$TMP2"

echo "=== Comparing basic block execution addresses ==="
diff -u "$TMP1" "$TMP2"

# Compare raw content
if cmp -s "$TMP1" "$TMP2"; then
    echo ""
    echo "✅ Both logs have identical BB execution sequences."
    RESULT=0
else
    echo ""
    echo "❌ Logs differ in at least one basic block address."
    RESULT=1
fi

rm -f "$TMP1" "$TMP2"
exit $RESULT

