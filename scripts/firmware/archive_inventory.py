#!/usr/bin/env python3
"""Create a deterministic SHA-256 inventory for ZIP/TAR firmware archives."""
from __future__ import annotations
import argparse, hashlib, json, pathlib, tarfile, zipfile
from datetime import datetime, timezone

CHUNK = 1024 * 1024

def digest_stream(stream):
    h = hashlib.sha256()
    size = 0
    while True:
        block = stream.read(CHUNK)
        if not block:
            break
        size += len(block)
        h.update(block)
    return size, h.hexdigest()

def inventory(path: pathlib.Path):
    archive_digest = hashlib.sha256()
    with path.open("rb") as archive_stream:
        while True:
            block = archive_stream.read(CHUNK)
            if not block:
                break
            archive_digest.update(block)
    archive_hash = archive_digest.hexdigest()
    members = []
    archive_format = "raw"
    if zipfile.is_zipfile(path):
        archive_format = "zip"
        with zipfile.ZipFile(path) as zf:
            for info in zf.infolist():
                if info.is_dir():
                    continue
                with zf.open(info) as src:
                    size, sha = digest_stream(src)
                members.append({"name": info.filename, "size": size, "sha256": sha})
    elif tarfile.is_tarfile(path):
        archive_format = "tar"
        with tarfile.open(path, "r:*") as tf:
            for info in tf.getmembers():
                if not info.isfile():
                    continue
                src = tf.extractfile(info)
                if src is None:
                    continue
                with src:
                    size, sha = digest_stream(src)
                members.append({"name": info.name, "size": size, "sha256": sha})
    members.sort(key=lambda x: (x["name"], x["size"], x["sha256"]))
    return {
        "schema_version": 1,
        "archive": path.name,
        "format": archive_format,
        "archive_size": path.stat().st_size,
        "archive_sha256": archive_hash,
        "member_count": len(members),
        "members": members,
    }

def main():
    p = argparse.ArgumentParser()
    p.add_argument("archives", nargs="+", type=pathlib.Path)
    p.add_argument("--output", type=pathlib.Path, default=pathlib.Path("archive-inventory.json"))
    a = p.parse_args()
    records = [inventory(x) for x in sorted(a.archives)]
    doc = {"generated_at_utc": datetime.now(timezone.utc).isoformat(),
           "generator": "archive_inventory.py", "archives": records}
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(doc, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"Inventoried {len(records)} archive(s) -> {a.output}")

if __name__ == "__main__":
    main()
