#!/usr/bin/env python3
"""Reassemble split ZIP volumes and safely extract every archive set."""
from __future__ import annotations
import argparse
import hashlib
import json
import re
import shutil
import zipfile
from collections import Counter
from pathlib import Path, PurePosixPath
from datetime import datetime, timezone

CHUNK = 1024 * 1024
SPLIT_RE = re.compile(r"^(.*\.zip)\.(\d{3})$", re.IGNORECASE)

def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(CHUNK), b""):
            digest.update(chunk)
    return digest.hexdigest()

def safe_target(root: Path, member: str) -> Path:
    normalized = member.replace("\\", "/")
    relative = PurePosixPath(normalized)
    if relative.is_absolute() or any(part in ("", ".", "..") for part in relative.parts):
        raise ValueError(f"unsafe archive path: {member!r}")
    target = (root / Path(*relative.parts)).resolve()
    base = root.resolve()
    if target != base and base not in target.parents:
        raise ValueError(f"archive path escapes destination: {member!r}")
    return target

def archive_groups(root: Path):
    split, regular = {}, []
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        match = SPLIT_RE.match(path.name)
        if match:
            split.setdefault((path.parent, match.group(1)), []).append((int(match.group(2)), path))
        elif path.suffix.lower() == ".zip":
            regular.append((path.relative_to(root).as_posix(), [path]))
    groups = []
    for (parent, name), parts in split.items():
        relative_parent = parent.relative_to(root)
        label = (relative_parent / name).as_posix() if str(relative_parent) != "." else name
        groups.append((label, [p for _, p in sorted(parts)]))
    groups.extend(regular)
    return sorted(groups, key=lambda item: (item[0].lower(), str(item[1][0])))

def process_group(root: Path, extract_root: Path, label: str, parts: list[Path]):
    key = label[:-4] if label.lower().endswith(".zip") else label
    destination = safe_target(extract_root, key)
    joined = None
    try:
        if len(parts) == 1 and parts[0].suffix.lower() == ".zip":
            archive_path = parts[0]
        else:
            joined = extract_root / (".assembled-" + re.sub(r"[^A-Za-z0-9._-]+", "-", key.replace("/", "-")) + ".zip")
            with joined.open("wb") as output:
                for expected, part in enumerate(parts, start=1):
                    match = re.search(r"\.(\d{3})$", part.name)
                    actual = int(match.group(1)) if match else 0
                    if actual != expected:
                        raise ValueError(f"missing/out-of-order volume: expected {expected:03d}, got {actual:03d}")
                    with part.open("rb") as source:
                        shutil.copyfileobj(source, output, CHUNK)
            archive_path = joined

        destination.mkdir(parents=True, exist_ok=True)
        rows, seen_targets = [], set()
        extension_counts = Counter()
        total_uncompressed = 0
        with zipfile.ZipFile(archive_path) as zf:
            bad_member = zf.testzip()
            if bad_member:
                raise ValueError(f"CRC failure in {bad_member}")
            for info in zf.infolist():
                if info.is_dir():
                    continue
                target = safe_target(destination, info.filename)
                mode = (info.external_attr >> 16) & 0o170000
                if mode == 0o120000:
                    raise ValueError(f"symlink entry rejected: {info.filename}")
                target_key = target.as_posix()
                if target_key in seen_targets:
                    raise ValueError(f"duplicate extraction destination: {info.filename}")
                seen_targets.add(target_key)
                target.parent.mkdir(parents=True, exist_ok=True)
                temporary = target.with_name(target.name + ".extract-tmp")
                digest = hashlib.sha256()
                size = 0
                with zf.open(info) as source, temporary.open("wb") as output:
                    for chunk in iter(lambda: source.read(CHUNK), b""):
                        output.write(chunk)
                        digest.update(chunk)
                        size += len(chunk)
                hexdigest = digest.hexdigest()
                if target.exists() and target.is_file() and sha256_file(target) == hexdigest:
                    temporary.unlink()
                else:
                    temporary.replace(target)
                suffix = Path(info.filename).suffix.lower() or "[no extension]"
                extension_counts[suffix] += 1
                total_uncompressed += size
                rows.append({"path": info.filename, "size": size,
                             "compressed_size": info.compress_size, "sha256": hexdigest,
                             "extracted_path": target.relative_to(extract_root).as_posix()})
        return {
            "archive": label,
            "parts": [p.relative_to(root).as_posix() for p in parts],
            "status": "ok",
            "file_count": len(rows),
            "uncompressed_bytes": total_uncompressed,
            "archive_bytes": sum(p.stat().st_size for p in parts),
            "source_sha256": [sha256_file(p) for p in parts],
            "extensions": dict(sorted(extension_counts.items())),
            "files": rows,
        }
    finally:
        if joined and joined.exists():
            joined.unlink()

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path("firmware/archives/mt8163"))
    parser.add_argument("--extract-root", type=Path, required=True)
    parser.add_argument("--markdown", type=Path, required=True)
    parser.add_argument("--json", type=Path, required=True)
    args = parser.parse_args()
    root = args.root.resolve()
    extract_root = args.extract_root.resolve()
    args.markdown.parent.mkdir(parents=True, exist_ok=True)
    args.json.parent.mkdir(parents=True, exist_ok=True)
    extract_root.mkdir(parents=True, exist_ok=True)

    reports = []
    for label, parts in archive_groups(root):
        try:
            reports.append(process_group(root, extract_root, label, parts))
        except Exception as exc:
            reports.append({"archive": label,
                            "parts": [p.relative_to(root).as_posix() for p in parts],
                            "status": "error", "error": str(exc)})
    document = {"schema_version": 1, "generated_at_utc": datetime.now(timezone.utc).isoformat(),
                "source_root": args.root.as_posix(), "archive_count": len(reports), "archives": reports}
    args.json.write_text(json.dumps(document, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
                         encoding="utf-8")
    lines = ["# Firmware archive extraction inventory", "",
             "Original archives remain unchanged. Extracted outputs are reproducible from the source volumes.",
             "", "| Archive set | Status | Files | Expanded size |", "|---|---:|---:|---:|"]
    for report in reports:
        if report["status"] != "ok":
            lines.append(f"| `{report['archive']}` | ERROR | — | — |")
        else:
            size = report["uncompressed_bytes"] / (1024 ** 2)
            lines.append(f"| `{report['archive']}` | OK | {report['file_count']} | {size:.1f} MiB |")
    args.markdown.write_text("\n".join(lines) + "\n", encoding="utf-8")
    failures = [r for r in reports if r["status"] != "ok"]
    print(f"Archive sets: {len(reports)}; successful: {len(reports)-len(failures)}; failed: {len(failures)}")
    for report in reports:
        print(f"{report['status'].upper()}: {report['archive']} ({report.get('file_count', 0)} files)")
        if report.get("error"):
            print(f"  {report['error']}")
    return 1 if failures else 0

if __name__ == "__main__":
    raise SystemExit(main())
