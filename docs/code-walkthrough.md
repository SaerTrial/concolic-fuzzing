# Code walkthrough

This map refers to the pinned emulator commits listed in the root README.
The release-preparation changes cover setup, examples, validation tools and
documentation, plus a coverage-output buffering fix in both emulators.

## 1. Configure an execution environment

Both forks add a configurable machine:

- `TriforceQEMU/hw/rehosting/configurable_machine.c`: `rehost-fuzzing`.
- `concolic-replay/hw/concolic/configurable_machine.c`: `concolic-execution`.

The JSON file supplied through `-kernel` is a configuration, not the firmware
image itself. Its `flash[].file` points to the raw image. Both loaders resolve
relative image paths against the JSON file's directory.

The configuration establishes RAM and flash ranges, the CPU model and entry
state, patches and exit addresses. ARM hook implementations live in each
machine's `arm/function_hooks.c`. These hooks change the modeled execution;
they must be considered when interpreting coverage or crashes.

## 2. Turn the input file into firmware-visible values

The fuzzer consumes the file passed with `-aflFile`. The concolic executor
consumes `-replayFile`, using its `getFuzz()` cursor to read successive bytes.

Compare:

- `TriforceQEMU/patches/afl-qemu-cpu-inl.h`: AFL setup, forkserver and map updates.
- `TriforceQEMU/system/memory.c`: input-backed memory reads.
- `concolic-replay/system/memory.c`: `symbolize_mem_read()` obtains concrete
  bytes and calls `symcc_make_symbolic()` for the MMIO strategy.
- `concolic-replay/accel/tcg/tcg-runtime-sym.c`: symbolic guest loads and stores,
  including the alternative `symbolize_at_pc` strategy.

The symbolic load helper transfers the expression associated with the MMIO
read into the symbolic computation. Ordinary guest-memory loads use the
host-side shadow-memory representation.

In the current configuration loader, specifying `symbolize_at_pc` disables
MMIO symbolization. A model satisfying constraints on selected memory reads
does not by itself establish that those bytes map back to the same external
events in the AFL execution. Validate that correspondence for each target.

## 3. Observe blocks and schedule interrupts

Both ARM translators register `arm_helper_func`. The translator emits a
block helper, which calls the architecture hook during execution.
The hook records the block-entry PC, checks exits and applies configured
function hooks.

Relevant files include `accel/tcg/translator.c`, `tcg/tcg-op.c`,
`accel/tcg/cpu-exec.c`, `target/arm/tcg/translate.c`, and
`hw/{rehosting,concolic}/arm/interrupt_firing.c`.

The interrupt scheduler cycles through enabled NVIC entries at a configured
block-event interval. That schedule is a modeling choice. It does not
reproduce peripheral timing on a physical STM32.

The two forks also use different upstream QEMU versions. Sharing a JSON
configuration is therefore useful but insufficient evidence of identical
execution.

## 4. Close the AFL / solver loop

The modified Rust helper is in `concolic-replay/symcc_fuzzing_helper/src/`:

1. `AflConfig::load()` in `symcc.rs` reads `fuzzer_stats` and discovers the
   AFL command, its queue and `afl-showmap`.
2. `best_new_testcase()` ranks unseen files. `TestcaseScore` favors names
   marked `+cov`, then original seeds, then smaller files, with filename as
   a final ordering criterion.
3. `SymCC::run()` copies the chosen input to a work file, launches the system
   emulator with a timeout and configures the runtime through environment variables.
4. `main.rs` evaluates generated candidates with `run_showmap()`.
5. Interesting candidates enter the helper's AFL-compatible queue, which the
   main AFL instance can synchronize.

This is an asynchronous shared-queue design. The code does not wait for a
measured coverage plateau before launching concolic execution.

## 5. Review the release-preparation changes

| File | Change and reason |
| --- | --- |
| `.gitmodules` | HTTPS URLs allow public readers to initialize submodules without an SSH identity once the forks are public. |
| `build_fuzzer_and_concolic_executor.sh` | Root-relative paths, fail-fast errors, pinned AFL revision, local Python environment and helper install, required submodules only, bounded parallelism. |
| `fw-example/*/*.json` | Image filenames resolve relative to the configuration, removing workstation-specific paths. |
| `utils/prepare_config.py` | Validates image existence and creates a separate absolute-path configuration for a run. |
| `utils/single_compare_test_case.sh` | Reads the current log marker, preserves order and repetition, rejects missing/empty/malformed traces. |
| `utils/test_same_exec_flows_over_testset.sh` | Bounds execution, retains per-input evidence and returns failure on mismatches or runtime errors. |
| `tests/test_release_tools.py` | Covers the previous empty-trace false positive and batch-runner failure behavior, plus path resolution. |
| `tests/check_coverage_export.py` | Runs three inputs through both built emulators, checks EZCOV record integrity and compares their nonempty traces. |
| Both `hw/{rehosting,concolic}/configurable_machine.c` files | Enable line buffering when opening `-covFile`, so input exhaustion through `_exit()` does not discard pending records. |
| `.gitignore` | Keeps builds, logs and editor state out of future commits. |
| `LICENSE`, `LICENSING.md` and script headers | Declare GPL-3.0-only for the project's original material and distinguish third-party components in the emulators and firmware. |

The coverage fix is committed on `flush-coverage-export` in each fork;
the superproject pins those commits. It changes only coverage-file buffering.
The exporter and block-entry logger observe execution at different points, and
some logged PCs remain absent from the exported ranges. This fix addresses file
truncation, not that coverage-completeness limitation.

The tracked Vim swap file is removed from the proposed working tree. It still
exists in the original Git history; removing a file in a new commit does not
remove its historical contents.
