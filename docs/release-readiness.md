# Publication status

On 2026-10-27, the owner made all three repositories public. The prepared code
was pushed to the default branches below, with matching review branches:

| Repository | Default branch | Review branch |
| --- | --- | --- |
| [concolic-fuzzing](https://github.com/SaerTrial/concolic-fuzzing) | `main` | `public-release-prep` |
| [TriforceQEMU](https://github.com/SaerTrial/TriforceQEMU) | `main` | `flush-coverage-export` |
| [concolic-replay](https://github.com/SaerTrial/concolic-replay) | `master` | `flush-coverage-export` |

The blog is pushed only to `hybrid-fuzzing-draft` in the site repository, under
`_drafts/`. The site's `main` branch and published posts were not changed.

## Prepared

- [x] Trace the pinned emulator implementations and helper queue protocol.
- [x] Replace SSH submodule URLs with HTTPS URLs for eventual public cloning.
- [x] Remove workstation-specific paths from the root firmware examples.
- [x] Make the build script stop on errors and build only required AFL tools.
- [x] Build both emulators and the helper in a separate Linux checkout.
- [x] Reject empty-trace false positives and test utility error handling.
- [x] Fix buffered coverage loss on input exhaustion in both forks and check six exports.
- [x] Observe AFL imports from the helper in a bounded integration run.
- [x] Document variable coverage and avoid performance claims.
- [x] Remove the editor swap file from the proposed tree; preserve a local backup.
- [x] Add a code walkthrough and an unpublished blog draft in the site repository.
- [x] Add the author's Ghidra/Cartographer screenshot to the README and blog draft.
- [x] License the project's original material under GPL-3.0-only, preserving third-party terms.
- [x] Confirm the author's ownership of both firmware examples and record their original application code under GPL-3.0-only.
- [x] Push both emulator fixes before publishing the superproject's matching gitlinks.
- [x] Verify public visibility of the superproject and both emulator repositories without authentication.
- [x] Push the blog draft branch while leaving the site's main branch unchanged.

## Remaining work

1. **Firmware provenance.** The root repository ships H753ZI and H7S78-DK firmware
   binaries. Exact matching prebuilt copies and candidate sources were found in
   the existing `record-and-replay` project; see
   [firmware provenance](firmware-provenance.md). The author confirmed that he
   created both examples. The corresponding source revision, reproducible build
   and component notices remain to be packaged for publication.
2. **History contents.** The removed Vim swap remains in the original root
   history. It contains workstation metadata and recovered script text.
   Publication preserves that history; no history rewriting has been performed.

## Review scope and remaining verification

A limited scan checked the 17 root-repository blob objects reachable from the
original baseline refs for private-key headers, GitHub-token formats and AWS
access-key formats; it found no matches. This is not a comprehensive secret review, and
does not cover the histories of the two emulator forks.

The forks retain QEMU license files and upstream source notices. The
`symcc_fuzzing_helper` manifest identifies GPL-3.0-or-later. The superproject's
original material now uses GPL-3.0-only, as selected for this release;
[LICENSING.md](../LICENSING.md) describes its scope. This does not replace
upstream notices. The author's original firmware application contributions also
use GPL-3.0-only; embedded vendor/runtime code retains its existing terms.

Anonymous repository checks confirm public visibility for all three repositories.
The build and runtime checks are recorded in [validation.md](validation.md).
Firmware source packaging and a broader contributed-history review remain
separate follow-up work; the checks above do not establish a complete audit.

The current runtime limitations are documented in [validation.md](validation.md):
AFL reports variable coverage for some inputs, and the EZCOV exporter omits some
logged block entries. It can be released as a clearly described research
prototype, but the current measurements do not support a claim that it improves
coverage or finds more bugs.

## Blog discussion

The draft is in the site's `_drafts/hybrid-fuzzing-for-cortex-m-firmware.md`,
on branch `hybrid-fuzzing-draft`. It is excluded from a normal Jekyll build.

The proposed angle is the contract between the concrete and symbolic executions:
input-byte meaning, environment modeling, queue feedback and the trace-check bug.
For the next discussion, decide whether to emphasize that engineering story or
give more space to the original research motivation and project history.
