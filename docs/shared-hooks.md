# Shared firmware hooks

Both QEMU forks compile hook implementations from the
[firmware-hooks repository](https://github.com/SaerTrial/firmware-hooks), checked
out as their nested `hooks` submodule. Both forks must record the same hook
commit. There are two working copies, with one maintained source repository.

```text
concolic-fuzzing/
├── triforce-qemu/
│   ├── hooks/arm/function_hooks.c
│   └── hw/rehosting/arm/hook_backend.c
└── concolic-executor/
    ├── hooks/arm/function_hooks.c
    └── hw/concolic/arm/hook_backend.c
```

The shared sources contain `HAL_Delay`, `uart_printf`, their name registry, and
case-insensitive ARM register-name parsing. The existing callback signature
remains `void (*)(CPUARMState *)`. The implementation is ARM-specific; another
architecture should get its own directory and argument/return handling.

Each fork implements the small interface in `hooks/arm/hook_backend.h`:

| Operation | Responsibility |
| --- | --- |
| `hook_read_register(CPUARMState *, unsigned)` | Read a concrete ARM register. |
| `hook_read_memory8(CPUARMState *, uint32_t)` | Read a guest byte through QEMU, preserving MMIO side effects. |
| `hook_log_call(const char *, uint32_t, const char *)` | Log the hook name, counter, and suffix through the engine's existing logging category. |

The extraction preserves hook names, stdout, input read patterns, and the
translator's handling of patched-function returns. It does not introduce a new
input-consuming hook. In particular, `cpu_ldub_data()` reads guest memory; it is
not an API for copying symbolic input into a new guest destination. A future
receive hook will need an engine operation that consumes the shared input stream
and writes guest memory, including symbolic memory in the concolic engine.

## Initialize and build

The top-level build script initializes both nested hook submodules at their
recorded commits and checks them before compiling. It initializes SymCC's
required dependencies separately, avoiding downloads of unrelated optional QEMU
submodules.

```sh
./build_fuzzer_and_concolic_executor.sh
```

To initialize only the emulator and hook source checkouts:

```sh
git submodule update --init triforce-qemu concolic-executor
git -C triforce-qemu submodule update --init hooks
git -C concolic-executor submodule update --init hooks
python3 utils/check_shared_hooks.py
```

Each fork can also be built independently: initialize its `hooks` submodule
before running its normal configure/build commands. The concolic fork still
needs its SymCC runtime dependencies.

## Change a hook

1. Edit, validate, commit, and push the shared hook repository.
2. Fetch and check out that exact commit in **both** `hooks` working copies.
3. Commit and push each QEMU fork's updated `hooks` gitlink.
4. Record those two QEMU commits in `concolic-fuzzing`, then commit and push the
   superproject update.

Publish dependencies in that order so a fresh checkout can obtain every recorded
commit. Normal `git submodule update --init` checks out recorded commits; it does
not automatically follow the hook repository's latest branch.

Run `python3 utils/check_shared_hooks.py` after recording both engine commits.
The guard requires equal committed hook revisions, initialized checkouts at those
revisions, and no staged or unstaged hook changes. It also rejects non-ignored
untracked files, which could otherwise introduce local headers into a build.
Ignored build artifacts are allowed. The guard reports a mismatch without
resetting files or deleting local work.

The top-level build deliberately restores the emulator commits recorded in the
superproject. While developing uncommitted engine changes, build each engine
directly instead of invoking the top-level release build.

## Validate changes

Run the Git-workflow regression tests with:

```sh
python3 -m unittest discover -s tests -p 'test_shared_hooks.py'
```

For hook behavior, compare the same firmware and input before and after the
change in each engine: exit status, hook output, ordered execution trace,
coverage, and generated concolic test cases. Exercise the actual registered hook
names. The Nucleo example's `printf` patch name is not the `uart_printf` callback;
normal replay of that configuration alone does not exercise the printing hook.
Use a separate test configuration rather than changing a running campaign's
configuration. Check AFL bitmap feedback with `afl-showmap` for the native
engine. Do not require the two different engines to have identical traces when
their execution policies already differ.
