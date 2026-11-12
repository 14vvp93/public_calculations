# Firmware tools

- `archive_inventory.py`: streaming SHA-256 inventory for ZIP/TAR archives and raw split-volume files.
- `safe_extract.py`: safe extraction of a single ZIP/TAR archive with path traversal and duplicate-destination checks.
- `process_archive_sets.py`: numeric reassembly of `.zip.001` multipart archives, ZIP CRC verification, symlink/path/duplicate rejection, extraction and JSON/Markdown reports.
- `build_source_manifest.py`: provenance manifest for an existing imported firmware tree.
- `import_public_firmware.py`: copies the approved source paths, enforces per-file size limits, verifies source and destination SHA-256 equality, and writes a provenance manifest.

All tools use the Python standard library and are designed for offline/CI analysis only.
They do not access ADB, install firmware, or write to a target device.
