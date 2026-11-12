#!/usr/bin/env python3
"""Safely extract ZIP/TAR archives without path traversal or silent overwrites."""
from __future__ import annotations
import argparse, hashlib, json, pathlib, tarfile, zipfile

CHUNK = 1024 * 1024

def safe_target(root: pathlib.Path, member: str) -> pathlib.Path:
    name = pathlib.PurePosixPath(member.replace("\\", "/"))
    if name.is_absolute() or any(part in ("..", "") for part in name.parts):
        raise ValueError(f"Unsafe archive path: {member!r}")
    target = (root / pathlib.Path(*name.parts)).resolve()
    base = root.resolve()
    if target != base and base not in target.parents:
        raise ValueError(f"Archive path escapes destination: {member!r}")
    return target

def sha256_file(path: pathlib.Path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while True:
            block = stream.read(CHUNK)
            if not block:
                break
            digest.update(block)
    return digest.hexdigest()

def write_member(src, target):
    target.parent.mkdir(parents=True, exist_ok=True)
    h, size = hashlib.sha256(), 0
    with target.open("xb") as dst:
        while True:
            block = src.read(CHUNK)
            if not block:
                break
            dst.write(block); h.update(block); size += len(block)
    return size, h.hexdigest()

def extract(archive: pathlib.Path, dest: pathlib.Path):
    dest.mkdir(parents=True, exist_ok=True)
    seen, rows = set(), []
    if zipfile.is_zipfile(archive):
        with zipfile.ZipFile(archive) as zf:
            for info in zf.infolist():
                if info.is_dir(): continue
                target = safe_target(dest, info.filename)
                key = str(target)
                if key in seen: raise ValueError(f"Duplicate destination collision: {info.filename}")
                seen.add(key)
                with zf.open(info) as src:
                    size, sha = write_member(src, target)
                rows.append({"name": info.filename, "size": size, "sha256": sha})
    elif tarfile.is_tarfile(archive):
        with tarfile.open(archive, "r:*") as tf:
            for info in tf.getmembers():
                if not info.isfile(): continue
                target = safe_target(dest, info.name)
                key = str(target)
                if key in seen: raise ValueError(f"Duplicate destination collision: {info.name}")
                seen.add(key)
                src = tf.extractfile(info)
                if src is None: continue
                with src: size, sha = write_member(src, target)
                rows.append({"name": info.name, "size": size, "sha256": sha})
    else:
        raise ValueError(f"Unsupported archive format: {archive}")
    rows.sort(key=lambda x: x["name"])
    return rows

def main():
    p=argparse.ArgumentParser()
    p.add_argument("archive", type=pathlib.Path)
    p.add_argument("destination", type=pathlib.Path)
    p.add_argument("--manifest", type=pathlib.Path)
    a=p.parse_args()
    rows=extract(a.archive,a.destination)
    manifest={"schema_version":1,"source_archive":a.archive.name,
              "source_sha256":sha256_file(a.archive),
              "extracted_count":len(rows),"files":rows}
    out=a.manifest or a.destination/"manifest.json"
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(manifest,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print(f"Extracted {len(rows)} file(s) -> {a.destination}")

if __name__=="__main__": main()
