# Licensing scope

The original material in this superproject is licensed under the
**GNU General Public License, version 3 only** (`GPL-3.0-only`).
Copyright (C) 2025–2026 Zhanpeng Huang.

This grant covers the project's original orchestration scripts, utilities,
tests, configuration JSON, repository metadata, documentation and screenshots.
The editable source for documentation is its Markdown; image source is provided
in `imgs/`. The complete, unmodified license text is in [LICENSE](LICENSE).
There is no option to use a later GPL version under this grant.

## Independently licensed components

The superproject's license does not replace the terms of third-party components:

| Component | Where to find its terms |
| --- | --- |
| `triforce-qemu/` | Its `LICENSE`, `COPYING`, `COPYING.LIB` and per-file notices. QEMU includes files with different licenses. |
| `concolic-executor/` | Its `LICENSE`, `COPYING`, `COPYING.LIB` and per-file notices. |
| `concolic-executor/symcc_fuzzing_helper/` | Existing SymCC notices and the manifest's `GPL-3.0-or-later` declaration. |
| Downloaded AFL++, SymCC runtime, Qsym and build dependencies | Their own license and copyright notices. |

Preserve those notices when distributing the corresponding components. The root
GPL-3.0-only declaration does not relicense either emulator fork as a whole.

## Bundled firmware

Both firmware examples in `fw-example/` were created by Zhanpeng Huang. The
application code written for them is also licensed under GPL-3.0-only.
Vendor and runtime components inside the compiled images keep their own terms;
this grant does not relicense them.

For each example, the repository includes the compiled firmware (an ELF file
and a raw flash image) but not its source code, build instructions or the
notices of its vendor and runtime components. Those are still to be added.
