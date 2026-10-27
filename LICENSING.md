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
| `TriforceQEMU/` | Its `LICENSE`, `COPYING`, `COPYING.LIB` and per-file notices. QEMU includes files with different licenses. |
| `concolic-replay/` | Its `LICENSE`, `COPYING`, `COPYING.LIB` and per-file notices. |
| `concolic-replay/symcc_fuzzing_helper/` | Existing SymCC notices and the manifest's `GPL-3.0-or-later` declaration. |
| Downloaded AFL++, SymCC runtime, Qsym and build dependencies | Their own license and copyright notices. |

Preserve those notices when distributing the corresponding components. The root
GPL-3.0-only declaration does not relicense either emulator fork as a whole.

## Bundled firmware

The `.bin` and `.elf` files in `fw-example/` are excluded from the license grant
above. Matching prebuilt copies and candidate sources are recorded in
[firmware provenance](docs/firmware-provenance.md); the corresponding source
revision and complete redistribution terms remain to be established. The
project's license choice does not establish permission to redistribute those
binaries. This remains an item in [release readiness](docs/release-readiness.md).
