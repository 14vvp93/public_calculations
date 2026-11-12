# MT8163 Public Calculations

Public compute and reference-data workspace for the MT8163 Audio Engine.

This repository hosts public firmware dumps and archives, reproducible extraction,
heavy analysis workflows, reusable analysis tooling, and generated technical reports.
The canonical product implementation remains in
[14vvp93/mt8163_audio_engine](https://github.com/14vvp93/mt8163_audio_engine).

## Repository responsibilities

- **Firmware inputs:** original public archives and firmware dump files, preserved
  byte-for-byte whenever possible.
- **Extraction:** deterministic unpacking, inventories, SHA-256 manifests, and
  derived trees.
- **Analysis:** ELF/dependency, Android audio stack, HAL/JNI, AudioPolicy,
  PCM/DSP, mixer, CD3313, kernel-module, and configuration analysis.
- **Compute:** resource-intensive GitHub Actions workflows and reusable scripts.
- **Results:** machine-readable reports and concise findings suitable for review
  and promotion into the canonical product repository.

## Data policy

Firmware dumps and extracted firmware contents are approved for public storage.
Do not publish actual credentials, access tokens, passwords, private signing keys,
personal data, or unrelated private material. Treat workflow logs and artifacts
as public. Never print secrets in logs.

## Large files

GitHub's ordinary Git file-size limit makes it unsuitable for committing arbitrary
large firmware archives or full extracted trees. Keep original inputs intact and
record SHA-256 hashes. Use Git LFS or GitHub Releases for durable large-file
storage when appropriate; use Actions artifacts for temporary intermediate output.
Document retention and recreate large derived trees from immutable inputs and scripts.

## Reproducibility rules

1. Record the source archive name, byte size, and SHA-256.
2. Record each extracted member's path, size, and SHA-256.
3. Pin tool versions and workflow actions to reviewed versions or full commit SHAs.
4. Make scripts deterministic and safe to rerun.
5. Never silently overwrite source archives or treat a partial extraction as complete.
6. Separate raw inputs, derived files, reports, and temporary artifacts.

## Start here

- [Repository layout](docs/REPOSITORY_LAYOUT.md)
- [Compute worker contract](docs/COMPUTE_WORKER.md)
- [Firmware data policy](docs/FIRMWARE_DATA_POLICY.md)
- [Workflow catalog](docs/WORKFLOWS.md)
- [Workflow migration map](docs/WORKFLOW_MIGRATION_MAP.md)
- [Firmware import from the private source repository](docs/FIRMWARE_IMPORT.md)
- [Phase 1 status and exit criteria](docs/PHASE1_STATUS.md)
- [MT8163 audio control architecture](docs/AUDIO_CONTROL_ARCHITECTURE.md)
- [Framework audio mute path audit](reports/FRAMEWORK_AUDIO_MUTE_PATH_AUDIT.md)
- [AudioPolicy configuration audit](reports/AUDIO_POLICY_CONFIG_AUDIT.md)
- [MT8163 audio stack — first-pass findings](reports/MT8163_AUDIO_STACK_FIRST_PASS.md)
- [DSP driver ownership analysis](reports/DSP_DRIVER_OWNERSHIP_ANALYSIS.md)
- [CD3313 module variant comparison](reports/CD3313_MODULE_VARIANT_DIFF.md)
- [CD3313 ioctl and character-device ABI audit](reports/CD3313_IOCTL_ABI_AUDIT.md)
- [ExtAudioMuxer JNI ↔ CD3313 ioctl ABI audit](reports/EXT_AUDIO_MUXER_JNI_ABI_AUDIT.md)
- [Audio stack inventory script](scripts/firmware/audio_stack_inventory.py)
- [Latest static audio inventory run](https://github.com/14vvp93/public_calculations/actions/runs/43210027838)

## Status

Phase 1 is complete: all 48 approved firmware inputs were imported and hash-verified,
and all four split archive sets were reassembled, CRC-checked and extracted. The first-pass
audio-stack findings are documented in the linked reports. The static inventory now parses both the embedded base DTB and DTBO overlay, and compares the DSP module variants. Analysis is host-side only;
no live MT8163 device has been accessed.
