# Validation record — 2026-10-27

These checks validate build and integration behavior. They are not an effectiveness
benchmark or evidence of hardware-accurate STM32 emulation.

## Environment and source revisions

- Host: `alexis`, Linux x86-64, Ubuntu 22.04.5 LTS.
- GCC 11.4.0; Python 3.10.12; CMake 3.22.1; Ninja 1.10.1; Cargo 1.92.0; Z3 4.8.12.
- Root baseline: `2d93c85c2e03a3c34ba6fe0b47f5bb9e06ef9d28`, plus the
  changes on `codex/public-release-prep`.
- TriforceQEMU full-build baseline: `0618b8d84c66c3a2436cb2da43e42a2be781af95`;
  coverage fix: `29165260d6351cb7f223fe5c17ace142ccd1d7e5`.
- concolic-replay full-build baseline: `6d2c699e3dd82bc1f70d94e33293d51b7677537b`;
  coverage fix: `b793b1601e032652a4afd4cf00c4c6047a4a7c96`.
- SymCC runtime: `892f817f38f5abfa083dd0c1caa7ced821566bf5`.
- Qsym backend: `ccd2f41f2efb1b0517b83458c181e060497fa589`.
- AFL++ v4.34c: `474ff18ba2a7999a518a4d194fcd5a1f87c3625d`.

An independent checkout was created from the existing repositories on the host.
The original working directories were not edited. Both emulators, AFL tools
and the helper were built in the new checkout. Existing Rust tooling/cache and
system development packages were reused; this was not a clean operating-system
or container installation.

The full build and hybrid feedback test used the baseline emulator revisions.
After the coverage-buffering fix, both emulators were rebuilt incrementally and
the three-input trace and coverage-export checks were repeated. The hybrid test
was not repeated: the change only affects runs that supply `-covFile`.

## Results

| Check | Observed result | Boundary |
| --- | --- | --- |
| Updated build script | Completed; both emulators, AFL tools and helper built | Fresh build directories on an already provisioned Linux host |
| Utility regression tests | 14 passed on Linux | Harness/path handling, including failure cases; not emulator semantic tests |
| Utility regression tests on macOS | 9 passed, 5 skipped | Batch tests require GNU `timeout` |
| Shell parsing and Git whitespace checks | Passed | Static checks |
| Three concrete input comparisons | 3 matched; 0 differences; 0 execution errors | Ordered block-entry PCs only |
| ELF/raw firmware correspondence | `llvm-objcopy-13 -O binary` output matched the bundled raw image byte for byte | Applies to the H753ZI example |
| EZCOV regression after buffering fix | Six well-formed, newline-terminated exports; three matching trace pairs | Exported ranges still omit some logged PCs; see below |
| Concurrent hybrid smoke test | Helper queue populated; AFL imported 4 helper inputs | 45 seconds, special smoke settings; not a baseline comparison |
| Full Jekyll site build | Not run: the Mac lacks the gems in the existing lockfile | Draft front matter and Markdown structure checked |

## Concrete inputs

All runs used `fw-example/nucleo753zi/aflConfiguration.json`, resolved to the
current raw image. Both processes exited successfully. The fresh-build batch
runner retained separate logs and solver outputs per input.

| Input | Contents | Fuzzer / concolic block entries | Solver candidate files |
| --- | --- | --- | --- |
| `a81` | 80 `A` bytes followed by a newline | 103 / 103, sequences identical | 1 |
| `zero81` | 81 zero bytes | 103 / 103, sequences identical | 1 |
| `sequence80` | Bytes 0 through 79 | 208 / 208, sequences identical | 12 |

Candidate-file counts do not mean new coverage or unique bugs. Matching traces
do not establish equality of machine state or behavior on hardware.

## Coverage export

The original `sequence80` export contained 151 complete records and a truncated
final line (`0x`), at exactly 4,096 bytes. Input exhaustion calls `_exit()`, which
does not flush buffered stdio. Both emulators now enable line buffering when
opening the coverage file. The regression command was:

```sh
python3 tests/check_coverage_export.py --output runs/coverage-regression
```

| Input | Records per emulator | Bytes per export | Block entries per emulator |
| --- | --- | --- | --- |
| `a81` | 80 | 2,177 | 103 |
| `zero81` | 80 | 2,177 | 103 |
| `sequence80` | 161 | 4,364 | 208 |

All six files had the EZCOV header, valid nonempty records and a final newline.
All three pairs of ordered block-entry traces matched after rebuilding.

**Remaining limitation:** records are not a complete block-entry trace. The
exporter writes ranges in `cpu_tb_exec`, while the logger runs in the generated
block helper. Comparing logged PCs with the union of exported ranges found 38
distinct PCs missing for `sequence80`, and three missing for each other input.
Consequently, neither record counts nor uncolored regions in Ghidra establish
complete execution coverage. The buffering fix does not resolve this difference.

The README screenshot was supplied separately from the author's existing Ghidra
project. It illustrates the Listing and Decompiler overlays; its input/corpus
was not identified, so it is not attributed to these validation runs.

## Hybrid feedback test

The successful bounded run used the README's two commands with these additions:

- AFL option `-z`, disabling deterministic mutation stages for the short smoke run.
  In v4.34c, `-d` is deprecated and does not disable those stages.
- `AFL_SYNC_TIME=1`, reducing the synchronization interval to one minute.
- `AFL_NO_UI=1` and `AFL_SKIP_CPUFREQ=1` for unattended execution.
- `AFL_I_DONT_CARE_ABOUT_MISSING_CRASHES=1` to run with the host's existing
  core-dump handler. Crash-versus-timeout classification was not validated.

The processes ran concurrently for 45 seconds and were then stopped. Observations:

- AFL executed 18,259 test cases.
- AFL's queue contained 73 files; the helper's queue contained 84.
- `corpus_imported` was 4.
- Four AFL queue filenames recorded `sync:symqemu` with source IDs
  `000050`, `000053`, `000055`, and `000057`.
- AFL reported 18 variable corpus entries and 66.95% stability.

An earlier 75-second run with the default mutation stages produced solver
candidates but did not reach peer synchronization. Those observations motivated
testing the synchronization path separately; they are not comparable benchmark
trials.

**Open issue:** variable coverage needs investigation before evaluating the
benefit of hybrid fuzzing. The observed imports demonstrate the integration path,
but unstable coverage can affect which inputs are retained as interesting.

## Artifacts

The test checkout is at
`/home/alexis/Research/concolic-release-check-QOjn4e`.

- `runs/build.log`: build output.
- `runs/trace-check.bWRJYM/`: fresh-build per-input traces, comparisons and solver outputs.
- `runs/hybrid-smoke-fast/`: exact commands/environment, logs, queues, stats and summary.
- `runs/coverage-fix-build.log`: incremental rebuild of both coverage fixes.
- `runs/coverage-regression/`: six coverage files, per-input traces and summary.
- `runs/coverage-fixed/`: initial verification of the buffering fix.

The older `runs/initial/sequence80.ezcov` is truncated and should not be used as
the Ghidra example. Use a new export from the fixed revisions.

Copies are retained locally in the ignored `runs/validation-evidence/` directory.
Logs and generated corpora are excluded from the proposed source release.

SHA-256 of the firmware and initial fresh-build artifacts (before the buffering
fix):

```text
92550d8bb095b8380143cdba777a1e148f23ccd0e434a18074dcbe80813b8b10  nucleo-h753zi-RnR.bin
f2b9f3d13fe27dc1f869e8b859d59f199c404b70e5b36ecb29b957c9e06cb724  nucleo-h753zi-RnR.elf
b5bfd2e7934c5fe4e14bc0bdd2f1c4bc2fe05a7a8eb9af6b335dd2f71a07e209  TriforceQEMU/build/qemu-system-arm
259c14753eaf35eb9bea0420ae2cc2c0673827d7a297316851273b1b4633a646  concolic-replay/build/qemu-system-arm
9f826be18b00dcfb13dccb7f5c88f9563c4f41f9c8132aa8b18a986fff602eea  AFLplusplus/afl-fuzz
34e7cad41a0c83bba79cf1843d5d5af65338b472325afca5ebee619198618abd  AFLplusplus/afl-showmap
2e181ac048691f0caf3a71935944857148d7743c0db048625804a6f434c5465e  build/tools/bin/symcc_fuzzing_helper
```

SHA-256 of the incrementally rebuilt emulators with the buffering fix:

```text
eabf12589c70cb77d787c6e8f87d09bb12da226696539dd610ae792530465273  TriforceQEMU/build/qemu-system-arm
fc12d0805fd2d52d3a9de31ea2359461d234197d92185c751558cd58a32561bc  concolic-replay/build/qemu-system-arm
```
