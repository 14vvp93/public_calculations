# MT8163 Public Firmware & Compute

This repository is the public firmware-data store and heavy-compute worker for the private MT8163 Audio Engine project.

## Ownership

- **Firmware data:** approved MT8163 firmware dumps, extracted filesystem contents, and SHA-256 manifests under `firmware/`.
- **Compute infrastructure:** reusable GitHub Actions workflows, analysis scripts, and tests.
- **Private repository:** all product source code, build definitions, engineering documentation, and reviewed project decisions live in [`14vvp93/mt8163_audio_engine`](https://github.com/14vvp93/mt8163_audio_engine).

This repository must not contain product implementation code or project documentation. Do not add credentials, tokens, private keys, personal data, or private signing material.

## Firmware layout

```text
firmware/
├── dumps/       # Original standalone firmware images and extracted raw dumps
├── extracted/   # Verified extracted filesystem tree and HEQ reference payload
└── manifests/   # SHA-256 provenance and extracted-file inventories
```

Original ZIP archives are not retained once their complete extracted contents have been verified and committed. The extracted tree is the canonical public firmware dataset.

## Compute

GitHub Actions in this repository perform bounded firmware inventory, ELF/DSP analysis, configuration audits, and other resource-intensive tasks. Results are uploaded as workflow artifacts. The worker checks out the private project read-only only when it needs project code or analysis helpers; firmware inputs are read from this repository.

See the private project's `docs/public-compute/` directory for the workflow contract and operating procedures.
