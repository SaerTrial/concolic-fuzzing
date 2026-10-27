# Firmware provenance investigation

Checked on 2026-10-27. The firmware binaries are excluded from the
superproject's GPL-3.0-only license grant; see [LICENSING.md](../LICENSING.md).

## Matching prebuilt copies

All three bundled firmware files match copies under the existing project at
`alexis:/home/alexis/Research/record-and-replay/record/firmware/`:

| Bundled file | Matching path relative to that directory | SHA-256 |
| --- | --- | --- |
| `nucleo753zi/nucleo-h753zi-RnR.bin` | `nucleo-h753zi/pre-build/nucleo-h753zi-RnR.bin` | `92550d8bb095b8380143cdba777a1e148f23ccd0e434a18074dcbe80813b8b10` |
| `nucleo753zi/nucleo-h753zi-RnR.elf` | `nucleo-h753zi/pre-build/nucleo-h753zi-RnR.elf` | `f2b9f3d13fe27dc1f869e8b859d59f199c404b70e5b36ecb29b957c9e06cb724` |
| `stm32h7s78-dk/stm32h7s78-dk.elf` | `stm32h7s78-dk/pre-build/stm32h7s78-dk.elf` | `dd45212cd603611723dfac3c2e1077d47507d6a0d08653af6af66e33dc20b6b5` |

That checkout was at `4ce6563ddd2a82cc16ab767c83bcfeca5bdc4e8c` when inspected.
Its H753ZI `Core/Src/main.c` had local modifications, and its current `build/`
outputs differed from the matching `pre-build/` copies. This identifies an
existing copy of each binary, not the exact source revision or a reproducible
build of the bundled images.

## Source and license evidence

Both firmware directories contain source and build files. Their `main.c` files
carry STMicroelectronics 2025 notices referring to a component `LICENSE` file.
The H753ZI HAL driver has a package-license notice with a BSD-3-Clause fallback;
CMSIS includes an Apache-2.0 license. These are component notices, not evidence
that the entire firmware can be assigned GPL-3.0-only.

Before including the firmware in a public release:

- Identify the source revision and build recipe for the bundled images, or
  rebuild a documented example from known source.
- Confirm the project's original contributions and applicable release terms.
- Preserve the vendor/component license notices required by that source set.

No files in the existing source project were changed during this investigation.
