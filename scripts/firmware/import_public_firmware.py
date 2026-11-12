#!/usr/bin/env python3
"""Import approved firmware files, verify byte identity, and write provenance."""
from __future__ import annotations
import argparse
import hashlib
import json
import pathlib
import re
import shutil
from datetime import datetime, timezone

CHUNK = 1024 * 1024
MAX_GIT_BLOB = 95 * 1024 * 1024
ZIP_INPUT = re.compile(r".*\.zip(?:\.\d{3})?$", re.IGNORECASE)

def hash_file(path: pathlib.Path):
    digest = hashlib.sha256()
    size = 0
    with path.open("rb") as stream:
        while True:
            block = stream.read(CHUNK)
            if not block:
                break
            size += len(block)
            digest.update(block)
    return size, digest.hexdigest()

def safe_source_files(folder: pathlib.Path):
    if folder.is_symlink() or not folder.is_dir():
        raise ValueError(f"Required source directory missing or symlinked: {folder}")
    result = []
    for path in sorted(folder.iterdir()):
        if path.is_symlink():
            raise ValueError(f"Symlinked source input rejected: {path}")
        if path.is_file():
            result.append(path)
    return result

def collect_inputs(source_root: pathlib.Path, include_raw: bool):
    refs = source_root / "reference-materials"
    dumps = refs / "firmware-dumps"
    heq = refs / "heq"
    kernel = refs / "kernel" / "cd3313.ko"
    inputs = []
    for source in safe_source_files(dumps):
        if ZIP_INPUT.fullmatch(source.name):
            target = pathlib.Path("firmware/archives/mt8163") / source.name
        elif include_raw:
            target = pathlib.Path("firmware/dumps/mt8163") / source.name
        else:
            continue
        inputs.append((source, target))
    for source in safe_source_files(heq):
        if source.name.lower().startswith("heq.zip."):
            inputs.append((source, pathlib.Path("firmware/archives/mt8163/HEQ") / source.name))
    if kernel.is_symlink() or not kernel.is_file():
        raise ValueError(f"Required CD3313 reference module missing or symlinked: {kernel}")
    inputs.append((kernel, pathlib.Path("firmware/dumps/mt8163/kernel/cd3313.ko")))
    if not inputs:
        raise ValueError("No approved firmware inputs found")
    targets = [target.as_posix() for _, target in inputs]
    if len(targets) != len(set(targets)):
        raise ValueError("Two source files map to the same destination")
    return inputs

def import_inputs(source_root: pathlib.Path, destination_root: pathlib.Path,
                  source_repository: str, source_ref: str, source_commit: str,
                  include_raw: bool):
    destination_root = destination_root.resolve()
    entries = []
    for source, relative_target in collect_inputs(source_root.resolve(), include_raw):
        size, source_sha = hash_file(source)
        if size > MAX_GIT_BLOB:
            raise ValueError(f"Input exceeds conservative 95 MiB Git blob limit: {source}")
        target = (destination_root / relative_target).resolve()
        if destination_root not in target.parents:
            raise ValueError(f"Destination escapes repository: {relative_target}")
        if target.is_symlink():
            raise ValueError(f"Destination symlink rejected: {target}")
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.is_file():
            old_size, old_sha = hash_file(target)
            if old_size == size and old_sha == source_sha:
                pass
            else:
                temporary = target.with_name(target.name + ".import-tmp")
                shutil.copyfile(source, temporary)
                copied_size, copied_sha = hash_file(temporary)
                if copied_size != size or copied_sha != source_sha:
                    temporary.unlink(missing_ok=True)
                    raise IOError(f"Copy verification failed: {source}")
                temporary.replace(target)
        else:
            temporary = target.with_name(target.name + ".import-tmp")
            shutil.copyfile(source, temporary)
            copied_size, copied_sha = hash_file(temporary)
            if copied_size != size or copied_sha != source_sha:
                temporary.unlink(missing_ok=True)
                raise IOError(f"Copy verification failed: {source}")
            temporary.replace(target)
        entries.append({
            "source_path": source.relative_to(source_root.resolve()).as_posix(),
            "path": relative_target.as_posix(),
            "size": size,
            "sha256": source_sha,
            "verified_copy": True,
        })
    entries.sort(key=lambda item: item["path"])
    manifest = {
        "schema_version": 1,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "source": {"repository": source_repository, "ref": source_ref, "commit": source_commit},
        "include_raw_dumps": include_raw,
        "file_count": len(entries),
        "total_bytes": sum(item["size"] for item in entries),
        "files": entries,
    }
    manifest_path = destination_root / "firmware/manifests/mt8163-source-import.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=pathlib.Path, required=True)
    parser.add_argument("--destination-root", type=pathlib.Path, default=pathlib.Path("."))
    parser.add_argument("--source-repository", required=True)
    parser.add_argument("--source-ref", required=True)
    parser.add_argument("--source-commit", required=True)
    parser.add_argument("--include-raw-dumps", action="store_true")
    args = parser.parse_args()
    result = import_inputs(args.source_root, args.destination_root, args.source_repository,
                           args.source_ref, args.source_commit, args.include_raw_dumps)
    print(f"Imported and verified {result['file_count']} file(s), {result['total_bytes']} bytes.")

if __name__ == "__main__":
    main()
