# Hybrid fuzzing for rehosted Cortex-M firmware

This research prototype combines AFL++ with a full-system concolic executor.
AFL++ mutates inputs and measures coverage through the `TriforceQEMU` fork.
A modified SymCC fuzzing helper selects inputs from AFL's queue, runs them
through `concolic-replay`, and tests the solver's candidate inputs with
`afl-showmap` before making interesting candidates available to AFL.

The supplied configurations target Cortex-M7 firmware. They describe a simplified
execution environment: memory regions, an entry point, selected function hooks,
exit addresses, and optional interrupt scheduling. This is not a complete STM32
board model or hardware-accurate peripheral emulation.

See [the code walkthrough](docs/code-walkthrough.md),
[validation results](docs/validation.md), and
[publication status](docs/release-readiness.md).

## Components

| Component | Pinned version | Role |
| --- | --- | --- |
| [TriforceQEMU](https://github.com/SaerTrial/TriforceQEMU) | `29165260d6351cb7f223fe5c17ace142ccd1d7e5` | QEMU 9.1.3 fork with firmware rehosting, AFL forkserver and coverage |
| [concolic-replay](https://github.com/SaerTrial/concolic-replay) | `b793b1601e032652a4afd4cf00c4c6047a4a7c96` | QEMU 9.1.1 / SymQEMU fork with system-mode symbolic execution |
| [SymCC runtime](https://github.com/eurecom-s3/symcc-rt) | `892f817f38f5abfa083dd0c1caa7ced821566bf5` | Symbolic expressions and the Qsym solver backend |
| [AFL++](https://github.com/AFLplusplus/AFLplusplus/tree/v4.34c) | `v4.34c` / `474ff18ba2a7999a518a4d194fcd5a1f87c3625d` | Mutation, queue management and coverage collection |

Both emulator repositories must be accessible to the reader. Making this
superproject public alone does not expose private submodules.

## Build on Linux

Use a Linux x86-64 environment. The release checks use Ubuntu 22.04; macOS is
suitable for reviewing the sources and running the portable utility tests.

Install the build dependencies on Ubuntu:

```sh
sudo apt-get update
sudo apt-get install build-essential git pkg-config python3-dev python3-venv \
  python3-pip ninja-build meson cmake libglib2.0-dev libpixman-1-dev \
  libgcrypt20-dev zlib1g-dev libz3-dev llvm-13-dev
```

Install a Rust toolchain using [rustup](https://rustup.rs/) and ensure that
`cargo` is in your shell's `PATH`. Then:

```sh
git clone https://github.com/SaerTrial/concolic-fuzzing.git
cd concolic-fuzzing
JOBS=4 ./build_fuzzer_and_concolic_executor.sh
```

The script initializes the required submodules, pins AFL++, uses a local Python
virtual environment, builds both ARM system emulators, and installs the helper
under `build/tools/bin/`. It stops on the first failed command. QEMU may download
its pinned build subprojects and Python tools during configuration.

Only `afl-fuzz` and `afl-showmap` are built from AFL++; this workflow obtains
coverage from the emulator and does not need AFL compiler instrumentation.
An existing `AFLplusplus/` directory must be a Git checkout at the pinned commit;
move an older archive-based build aside before running the script.

## Run the NUCLEO-H753ZI example

Run these commands from the repository root. Use a checkout path without spaces:
the current helper splits the command line in `fuzzer_stats` on whitespace.

Prepare a seed and a local configuration:

```sh
mkdir -p runs/input
python3 -c "from pathlib import Path; Path('runs/input/seed').write_bytes(b'A' * 80 + b'\\n')"
python3 utils/prepare_config.py \
  fw-example/nucleo753zi/aflConfiguration.json runs/nucleo753zi.json
```

The checked-in configurations use firmware paths relative to the configuration
file, as supported by both emulators. `prepare_config.py` checks that the image
exists and creates a separate configuration with absolute image paths.

Start AFL++ in the first terminal:

```sh
./AFLplusplus/afl-fuzz \
  -M fuzzer01 -i runs/input -o runs/output -t 2000 \
  -- ./TriforceQEMU/build/qemu-system-arm \
  -M rehost-fuzzing -display none \
  -kernel "$PWD/runs/nucleo753zi.json" -aflFile @@
```

After `runs/output/fuzzer01/fuzzer_stats` appears, start the helper in a second
terminal, from the same repository root:

```sh
./build/tools/bin/symcc_fuzzing_helper \
  -v -o runs/output -a fuzzer01 -n symqemu \
  -- ./concolic-replay/build/qemu-system-arm \
  -M concolic-execution -display none \
  -kernel "$PWD/runs/nucleo753zi.json" -replayFile @@
```

The helper sets `SYMCC_MEMORY_INPUT`, `SYMCC_OUTPUT_DIR`, and its symbolic
coverage-map path. It discovers `afl-showmap` from AFL's recorded command line.
Keep both terminals in the same working directory. Stop both processes with
Ctrl-C when the run is finished.

Queue growth or generated solver files alone do not establish better coverage.
Check that AFL imports the helper's inputs, and use repeated baseline-versus-hybrid
experiments before making effectiveness claims.

## Execution checks

Compare both emulators over a directory of concrete inputs:

```sh
utils/test_same_exec_flows_over_testset.sh runs/input runs/nucleo753zi.json
```

The runner uses a 30-second timeout per engine and input, retains individual logs
under `runs/trace-check.*/`, and returns:

- `0`: every input produced matching, nonempty ordered block-entry traces.
- `1`: at least one trace differed.
- `2`: invalid input, a failed/timed-out emulator, or missing/malformed trace data.

Set `TRACE_TIMEOUT_SECONDS` to adjust the limit. A matching address sequence
does not compare register values, memory values, peripheral semantics, or
agreement with physical hardware.

To compare existing logs, use
`utils/single_compare_test_case.sh fuzzer.log concolic.log`. It accepts the
current `[arm_helper_func] executing at` marker and the older
`[cpu_tb_exec] executed at` marker.

Utility regression checks need no emulator build:

```sh
python3 -m unittest discover -s tests -v
bash -n build_fuzzer_and_concolic_executor.sh utils/*.sh
```

After building both emulators, check EZCOV output and trace agreement for three
inputs. Choose a new output directory for each run:

```sh
python3 tests/check_coverage_export.py --output runs/coverage-regression
```

This checks record formatting and nonempty matching traces. It does not establish
that the exported ranges include every executed block.

## Visualizing coverage in Ghidra Cartographer

Export observed address ranges as EZCOV coverage:

```sh
./TriforceQEMU/build/qemu-system-arm \
  -M rehost-fuzzing -display none \
  -kernel runs/nucleo753zi.json -aflFile runs/input/seed \
  -covFile runs/seed.ezcov
```

Open the matching `fw-example/nucleo753zi/nucleo-h753zi-RnR.elf` in Ghidra,
with [Cartographer](https://github.com/nccgroup/Cartographer) installed. Select
**Tools → Code Coverage → Load Code Coverage File(s)** and load the EZCOV file.
**Window → Code Coverage** opens the function coverage table; the Listing,
Decompiler and Function Graph can show the executed regions.

![Cartographer coverage highlights in the Ghidra Listing and Decompiler for the NUCLEO-H753ZI firmware](imgs/ghidra-coverage.png)

*A view from this project: Cartographer highlights loaded coverage ranges in the
disassembly and decompiled C. This illustration is separate from the runs in
the [validation record](docs/validation.md).*

The overlay describes the ranges in the loaded file. The current exporter does
not include every block-entry PC observed in the execution log; see
[the export checks](docs/validation.md#coverage-export). An uncolored region is
therefore not proof that execution never reached it. The overlay also does not
measure physical-device coverage or prove a hybrid-fuzzing advantage. Use the
same firmware image and address mapping in Ghidra and the emulator.

## Configuration and boundaries

- `ram`, `flash` and `mmio` define the emulated address space.
- `entry_address` and optional `init_state` choose the starting CPU state.
- `patch` selects named C hooks; `exit_at` defines normal stopping addresses.
- `interrupt_firing` currently supports round-robin scheduling. Its frequency
  counts emulated block events, not physical time.
- `symbolize_at_pc` marks selected memory reads symbolic. When configured, the
  concolic executor disables MMIO symbolization; these modes are not combined.
  Validate how the symbolic input bytes correspond to the fuzzer's input stream
  for each target before relying on this mode.
- The STM32H7S78-DK directory contains an ELF but lacks the raw `.bin` referenced
  by its configuration. It is not the quick-start example. Obtain the matching
  raw image or convert the ELF with `arm-none-eabi-objcopy -O binary`, then
  validate that target separately.
- `utils/aggregate_queue_cov.sh` and `utils/search_interesting_bb.sh` are legacy
  exploratory helpers. The former concatenates coverage records without
  deduplicating them. Neither is a validated coverage benchmark.

RH850 support, additional interrupt strategies, more firmware targets and
coordination policies remain future work. Controlled AFL-only versus hybrid
benchmarks with equal resource budgets are also planned.

## Attribution and licensing

The original scripts, tests, configurations and documentation in this
superproject are licensed under **GPL-3.0-only**. See [LICENSE](LICENSE) for the
full text and [LICENSING.md](LICENSING.md) for scope and exclusions.

This work builds on QEMU, AFL/Triforce integration, SymQEMU, SymCC and the Qsym
backend. Their existing licenses and attribution files continue to apply.
The firmware examples were created by this project's author. Their original
application code uses GPL-3.0-only; vendor/runtime components retain their own
terms. The [provenance record](docs/firmware-provenance.md) identifies matching
prebuilt copies, with source/build and component-notice packaging remaining in
[release readiness](docs/release-readiness.md).
