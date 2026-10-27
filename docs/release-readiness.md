# Publication preparation

The proposed changes are local on branch `codex/public-release-prep`. No
repository visibility, remote branch or published website has been changed.

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
- [x] License the superproject's original material under GPL-3.0-only, with explicit third-party and firmware exclusions.

## Publication decisions still needed

1. **Repository set.** The superproject references `SaerTrial/TriforceQEMU`
   and `SaerTrial/concolic-replay`. Both returned HTTP 404 to anonymous requests
   during preparation. Public cloning requires access to those exact revisions,
   so the release needs to cover the forks as well. Push each fork's local
   `codex/flush-coverage-export` commit before publishing the superproject's new
   gitlinks; those commits are not yet available on GitHub.
2. **Firmware provenance.** The root repository ships H753ZI and H7S78-DK firmware
   binaries but does not include their source, build recipe or explicit
   redistribution information. Record where they came from and the intended
   release terms, or choose a separate reproducible example.
3. **History contents.** The removed Vim swap remains in the original root
   history. It contains workstation metadata and recovered script text.
   Decide whether to retain that history or prepare a separate cleaned release
   history. No history rewriting has been performed.

## Review scope and remaining verification

A limited scan checked the 17 root-repository blob objects reachable from the
original baseline refs for private-key headers, GitHub-token formats and AWS
access-key formats; it found no matches. This is not a comprehensive secret review, and
does not cover the histories of the two emulator forks.

The forks retain QEMU license files and upstream source notices. The
`symcc_fuzzing_helper` manifest identifies GPL-3.0-or-later. The superproject's
original material now uses GPL-3.0-only, as selected for this release;
[LICENSING.md](../LICENSING.md) describes its scope. This does not replace
upstream notices or assign a license to the firmware.

Before publication, review the forks' contributed files/history and all bundled
artifacts, settle the decisions above, and then verify an anonymous clone and
the documented build from the chosen public revisions.

The current runtime limitations are documented in [validation.md](validation.md):
AFL reports variable coverage for some inputs, and the EZCOV exporter omits some
logged block entries. It can be released as a clearly described research
prototype, but the current measurements do not support a claim that it improves
coverage or finds more bugs.

## Blog discussion

The draft is in the site's `_drafts/hybrid-fuzzing-for-cortex-m-firmware.md`,
on branch `codex/hybrid-fuzzing-draft`. It is excluded from a normal Jekyll build.

The proposed angle is the contract between the concrete and symbolic executions:
input-byte meaning, environment modeling, queue feedback and the trace-check bug.
For the next discussion, decide whether to emphasize that engineering story or
give more space to the original research motivation and project history.
