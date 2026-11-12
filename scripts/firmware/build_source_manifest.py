#!/usr/bin/env python3
"""Build a provenance and SHA-256 manifest for imported public firmware inputs."""
from __future__ import annotations
import argparse
import hashlib
import json
import pathlib
from datetime import datetime, timezone

CHUNK = 1024 * 1024

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

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-repository", required=True)
    parser.add_argument("--source-ref", required=True)
    parser.add_argument("--source-commit", required=True)
    parser.add_argument("--output", type=pathlib.Path, required=True)
    parser.add_argument("roots", nargs="*", type=pathlib.Path,
                        default=[pathlib.Path("firmware/archives/mt8163"),
                                 pathlib.Path("firmware/dumps/mt8163")])
    args = parser.parse_args()
    files = []
    for root in sorted(args.roots):
        if not root.exists():
            continue
        for path in sorted(p for p in root.rglob("*") if p.is_file()):
            size, sha = hash_file(path)
            files.append({"path": path.as_posix(), "size": size, "sha256": sha})
    doc = {
        "schema_version": 1,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "source": {"repository": args.source_repository, "ref": args.source_ref,
                   "commit": args.source_commit},
        "file_count": len(files),
        "total_bytes": sum(item["size"] for item in files),
        "files": files,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(doc, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"Manifest covers {len(files)} file(s), {doc['total_bytes']} bytes.")

if __name__ == "__main__":
    main()
