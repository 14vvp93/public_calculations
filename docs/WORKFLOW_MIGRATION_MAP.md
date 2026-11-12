# Workflow migration map

Source inventory: `14march93/mt8163_audio_engine`,
branch `feature/cd3313-driver-rewrite`. Canonical product destination:
`14vvp93/mt8163_audio_engine`. Compute destination:
`14vvp93/public_calculations`.

## Move/adapt to the public compute worker

These jobs analyze public firmware evidence and are natural worker workloads:

| Source workflow | Worker responsibility | Required adaptation |
|---|---|---|
| `analyze-audio-hal.yml` | HAL ELF, symbols, relocations, disassembly, XML | Read imported firmware tree; publish report/artifact only |
| `analyze-cd3313-ioctl.yml` | CD3313 ioctl ABI analysis | Read `cd3313.ko`; keep static evidence separate from hardware claims |
| `analyze-cd3313.yml` | CD3313 module static analysis | Same immutable input/hash contract |
| `analyze-firmware-images.yml` | boot/recovery/DTBO inspection | Pin mkbootimg tool revision |
| `analyze-firmware-libraries.yml` | ELF/library/dependency and vendor analysis | Pin vdexExtractor and all external tools |
| `audit-reference-archives.yml` | Archive integrity and full extraction | Use split-aware processor and SHA-256 manifests; never auto-commit expanded trees |
| `decompile-heq.yml` | HEQ archive/APK decompilation | Reassemble verified HEQ parts; record APK and tool hashes |
| `firmware-audio-config-audit.yml` | Audio configuration and manifest audit | Read imported extracted tree and report evidence |
| `scan-audiomux-clients.yml` | Find userspace CD3313 clients | Search extracted firmware and emit machine-readable findings |

## Keep product-owned by default

| Source workflow | Reason |
|---|---|
| `android-armv7.yml` | Builds product binaries; release artifacts belong to the canonical product repo |
| `android-effect-library.yml` | Product Android 9 ABI build |
| `build-android-test-apk.yml` | Product-facing diagnostic APK |
| `test-cd3313-emulator.yml` | Tests canonical emulator implementation |
| `test-pcm-dsp.yml` | Tests canonical PCM/DSP implementation |
| `pcm-dsp-performance.yml` | Product performance regression baseline |
| `pcm-dsp-stability-lab.yml` | Product stability and stress gate |

Product tests may later be executed on the compute runner through a protected read-only
checkout of the private product repository. Do not copy product source code into this
public repository. If such a bridge is added, logs/artifacts must contain only approved
test output and no credentials or private source bundles.

## Migration requirements for every workflow

1. Preserve the original task's behavior and evidence scope.
2. Replace assumptions about `reference-materials/` with the imported worker paths.
3. Pin third-party tools and actions to reviewed immutable revisions.
4. Declare minimum permissions and explicit runtime limits.
5. Use immutable source commit IDs and SHA-256 inputs.
6. Upload results as artifacts with documented retention; commit only reviewed,
   compact public reports.
7. Record the worker run URL, source hashes, tool versions and output schema in the
   canonical product repository.
8. Never install firmware or write to a physical MT8163 device from these workflows.

## Current status

This file is a migration map, not a claim that the listed workflows have already been
ported. The worker currently has infrastructure for public firmware import, archive
inventory, split-ZIP extraction, and validation tests. Individual analysis workflows
will be ported after the source archives have been imported and their output contracts
are defined.
