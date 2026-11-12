#!/usr/bin/env python3
"""Reassemble the public HEQ APK chunks and verify every SHA-256."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path

CHUNK = 1024 * 1024

def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(CHUNK), b""):
            h.update(block)
    return h.hexdigest()

def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--output", type=Path, default=Path("HEQ.apk"))
    p.add_argument("--parts-dir", type=Path, default=Path("firmware/extracted/heq"))
    p.add_argument("--manifest", type=Path, default=Path("firmware/manifests/heq-apk.json"))
    args = p.parse_args()
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.output.with_name(args.output.name + ".tmp")
    try:
        with temporary.open("wb") as output:
            for item in manifest["parts"]:
                source = args.parts_dir / Path(item["path"]).name
                if not source.is_file() or source.stat().st_size != item["size"] or digest(source) != item["sha256"]:
                    raise ValueError(f"HEQ chunk missing or hash mismatch: {source}")
                with source.open("rb") as stream:
                    for block in iter(lambda: stream.read(CHUNK), b""):
                        output.write(block)
        if temporary.stat().st_size != manifest["size"] or digest(temporary) != manifest["sha256"]:
            raise ValueError("Reassembled HEQ APK size or SHA-256 mismatch")
        temporary.replace(args.output)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise
    print(f"Verified HEQ APK: {args.output} ({args.output.stat().st_size} bytes)")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
