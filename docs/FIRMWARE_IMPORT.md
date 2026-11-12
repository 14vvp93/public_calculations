# Importing approved firmware from the source repository

The public compute repository is approved to host public MT8163 firmware archives,
dumps, extracted data and reports. The original source repository remains private.

## One-time credential setup

Create a fine-grained GitHub personal access token restricted to
`14march93/mt8163_audio_engine` with **Contents: Read-only** permission. Add it to
`14vvp93/public_calculations` as an Actions repository secret named
`SOURCE_REPO_READ_TOKEN`. Do not paste the token into chat, workflow inputs, files,
or logs. The import workflow runs only by manual dispatch on `main`.

## Run the import

Open **Actions → Import approved public MT8163 firmware → Run workflow**.
Select the source branch (default `feature/cd3313-driver-rewrite`) and whether to
include standalone raw dumps. The workflow imports:

- split ZIP volumes from `reference-materials/firmware-dumps/`;
- standalone raw images and configuration dumps when enabled;
- split HEQ archive volumes from `reference-materials/heq/`;
- the original `cd3313.ko` reference module.

The current source tree contains 48 approved firmware files totaling 393,831,964 bytes (about 375.6 MiB): 30 files under `firmware-dumps`, 17 HEQ split volumes, and the 183,368-byte CD3313 module. The largest individual volume is 25,165,824 bytes, below GitHub's 100 MiB normal-blob limit. The import preserves these files byte-for-byte.

The workflow records the exact source commit, file sizes and SHA-256 hashes in
`firmware/manifests/mt8163-source-import.json`, then commits the public inputs to
`main`. It does not modify or delete anything in the private source repository.

## Size and integrity

The imported archive volumes are preserved byte-for-byte. Before dispatch, confirm
that each source volume is below GitHub's 100 MiB ordinary Git blob limit. The
workflow uses ordinary Git for the split volumes; it does not recompress them or
silently switch to Git LFS. If a future input exceeds that limit, stop and select an
appropriate large-file backend first.

Because the destination repository is public, the imported files and their history
are public. The workflow does not import credentials or unrelated private files.
