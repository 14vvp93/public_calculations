# Phase 1 — infrastructure status

Last updated: 2026-11-12

## Completed

- Initialized the public compute repository on `main`.
- Defined its boundary: public firmware inputs, derived data, analysis tools,
  heavy Actions and public reports live here; canonical product source remains
  in the private `14vvp93/mt8163_audio_engine`.
- Added the repository layout for firmware archives/dumps/extraction/manifests,
  ELF, Audio HAL, CD3313, PCM/DSP, configuration analysis, scripts and reports.
- Documented public firmware approval and secret/privacy exclusions.
- Added streaming SHA-256 archive inventory, safe extraction, split-ZIP volume
  reassembly, CRC checks, duplicate destination checks, symlink rejection and
  source provenance manifests.
- Added automated tests for archive hashing, raw split volumes, safe extraction,
  path traversal, duplicate paths, split-volume reassembly, missing volumes and
  source provenance.
- Added manually dispatched compute workflow for inventory and split-aware extraction.
- Pinned Actions dependencies to immutable full commit SHAs.
- Added a controlled private-source-to-public-worker import workflow. It imports
  only approved firmware paths, preserves original bytes, verifies source-to-destination SHA-256 equality, rejects
  symlinked paths and files above a conservative 95 MiB ceiling, and commits only to
  the public worker's `main`.
- Added a workflow migration map and documented which analysis jobs belong in
  the compute worker versus which product build/test jobs remain product-owned.
- Audited the 16 retained source workflows for branch/repository portability and
  recorded the findings in the source repository's workflow audit.
- Corrected the old migration document so it agrees with the approved public
  firmware-storage policy.

## CI verification

The infrastructure validation workflow completed successfully, including Python
compilation, firmware tool unit tests and CLI checks:

- [Latest full validation — run 43202475478](https://github.com/14vvp93/public_calculations/actions/runs/43202475478)
- [Import workflow and size-guard validation — run 43202143602](https://github.com/14vvp93/public_calculations/actions/runs/43202143602)

These are host-side infrastructure tests, not firmware analysis or MT8163 device tests.

## Firmware import inventory

The source branch currently contains 48 approved firmware files totaling
393,831,964 bytes (about 375.6 MiB):

- 30 files under `reference-materials/firmware-dumps/`;
- 17 split HEQ ZIP volumes;
- the 183,368-byte `cd3313.ko` reference module.

The largest individual volume is 25,165,824 bytes, below GitHub's 100 MiB normal
Git blob limit. The split inputs are imported byte-for-byte; no recompression occurs.

## One remaining external prerequisite

The binary files cannot be transferred by the text-only GitHub file editor. The
repository now contains a dedicated Actions importer that performs the transfer
inside GitHub's runner.

Before it can read the private source repository, add the Actions secret
`SOURCE_REPO_READ_TOKEN` to `14vvp93/public_calculations`. It must be a fine-grained
token from an identity that can read `14march93/mt8163_audio_engine`, restricted
to that repository with **Contents: Read-only** permission. Do not paste the token
into chat or commit it to a file.

Then run **Actions → Import approved public MT8163 firmware → Run workflow** on
`main`, using source ref `feature/cd3313-driver-rewrite` and
`include_raw_dumps=true`. The workflow will create the firmware import commit
and `firmware/manifests/mt8163-source-import.json`.

Until that import succeeds and the hashes are verified, the public compute
repository is infrastructure-ready but does not yet contain the binary firmware
inputs. No archive-analysis job has been run against the imported data.

## Phase 1 exit criteria

- [x] Compute repository initialized and documented.
- [x] Safe, reproducible archive processing tools and CI tests.
- [x] Compute and import workflows prepared.
- [x] Source workflow portability audit recorded.
- [ ] Add the read-only source token secret.
- [ ] Run the firmware import and verify the resulting manifest against the source.
- [ ] Confirm public repository contents and exact imported file count/bytes.
