#!/bin/bash
echo "================================================="
echo "			search interesting BBs		"
echo "================================================="

if [ ! "`uname -s`" = "Linux" ]; then

  echo "[-] Error: only spported on Linux."
  exit 1

fi


if [ "$#" -le 2 ]; then
    echo "Usage: $0 <Queue Path> <Binary Conf> bb1 bb2 ..."
    exit 1
fi


if [ ! -d "${1}" ]; then
	echo "[-] afl queue folder does not exist!"
        exit 1;
fi

if [ ! -f "${2}" ]; then
        echo "[-] Emulation configuration for binary does not exist!"
        exit 1;
fi


if [ ! -f "./TriforceQEMU/build/qemu-system-arm" ]; then
        echo "[-] qemu-system-arm does not exist!. Compile first or check if it stays in the same folder as script"
        exit 1;
fi


logfile="foundBBs.log"
> "$logfile"

files=("$1"/*)        # expand glob into array
total=${#files[@]}    # count files

count=0

bbs=("${@:3}")
for cur_input in "${1}"/*; do
	((count++))
	percent=$(( 100 * count / total ))
        bar_len=$(( percent / 2 ))
	printf "\r[%-50s] %3d%% (%d/%d)" \
        	"$(printf '#%.0s' $(seq 1 $bar_len))" \
        	"$percent" "$count" "$total"

	"./TriforceQEMU/build/qemu-system-arm" -M rehost-fuzzing -display none -kernel "$2" -aflFile "$cur_input" -D qemu.log -d afl_fuzzing_log &>/dev/null

	for bb in "${bbs[@]}"; do
		if grep -q "$bb" "qemu.log"; then
			echo "$bb found in the $cur_input.." >> "$logfile"
		fi
	done
done

echo "Scan finished. Results saved to $logfile"


