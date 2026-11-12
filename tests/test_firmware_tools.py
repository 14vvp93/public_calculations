import hashlib
import json
import pathlib
import subprocess
import sys
import tempfile
import unittest
import warnings
import zipfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts" / "firmware"))
import archive_inventory
import process_archive_sets
import safe_extract


class FirmwareToolTests(unittest.TestCase):
    def test_inventory_hashes_archive_and_members(self):
        with tempfile.TemporaryDirectory() as td:
            root = pathlib.Path(td)
            archive = root / "sample.zip"
            payload = b"MT8163 test payload"
            with zipfile.ZipFile(archive, "w") as zf:
                zf.writestr("system/lib/libaudio.so", payload)
            result = archive_inventory.inventory(archive)
            self.assertEqual(result["format"], "zip")
            self.assertEqual(result["archive_sha256"], hashlib.sha256(archive.read_bytes()).hexdigest())
            self.assertEqual(result["member_count"], 1)
            self.assertEqual(result["members"][0]["sha256"], hashlib.sha256(payload).hexdigest())

    def test_inventory_accepts_raw_split_volume(self):
        with tempfile.TemporaryDirectory() as td:
            volume = pathlib.Path(td) / "files.zip.001"
            volume.write_bytes(b"split volume bytes")
            result = archive_inventory.inventory(volume)
            self.assertEqual(result["format"], "raw")
            self.assertEqual(result["archive_sha256"], hashlib.sha256(volume.read_bytes()).hexdigest())

    def test_safe_extract_writes_verified_member(self):
        with tempfile.TemporaryDirectory() as td:
            root = pathlib.Path(td)
            archive, dest = root / "sample.zip", root / "out"
            payload = b"safe"
            with zipfile.ZipFile(archive, "w") as zf:
                zf.writestr("vendor/lib/libaudio.so", payload)
            rows = safe_extract.extract(archive, dest)
            target = dest / "vendor/lib/libaudio.so"
            self.assertEqual(target.read_bytes(), payload)
            self.assertEqual(rows[0]["sha256"], hashlib.sha256(payload).hexdigest())

    def test_rejects_parent_traversal(self):
        with tempfile.TemporaryDirectory() as td:
            root = pathlib.Path(td)
            archive, dest = root / "bad.zip", root / "out"
            with zipfile.ZipFile(archive, "w") as zf:
                zf.writestr("../escape.txt", b"no")
            with self.assertRaises(ValueError):
                safe_extract.extract(archive, dest)
            self.assertFalse((root / "escape.txt").exists())

    def test_rejects_duplicate_destination(self):
        with tempfile.TemporaryDirectory() as td:
            root = pathlib.Path(td)
            archive, dest = root / "duplicate.zip", root / "out"
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                with zipfile.ZipFile(archive, "w") as zf:
                    zf.writestr("same.txt", b"one")
                    zf.writestr("same.txt", b"two")
            with self.assertRaises(ValueError):
                safe_extract.extract(archive, dest)

    def test_reassembles_and_extracts_split_zip(self):
        with tempfile.TemporaryDirectory() as td:
            root = pathlib.Path(td)
            archives, output = root / "archives", root / "output"
            archives.mkdir()
            output.mkdir()
            original = root / "original.zip"
            payload = b"split archive payload"
            with zipfile.ZipFile(original, "w") as zf:
                zf.writestr("vendor/lib/libaudio.so", payload)
            raw = original.read_bytes()
            split = len(raw) // 2
            (archives / "files.zip.001").write_bytes(raw[:split])
            (archives / "files.zip.002").write_bytes(raw[split:])
            groups = process_archive_sets.archive_groups(archives)
            self.assertEqual(len(groups), 1)
            report = process_archive_sets.process_group(archives, output, groups[0][0], groups[0][1])
            self.assertEqual(report["status"], "ok")
            extracted = output / "files/vendor/lib/libaudio.so"
            self.assertEqual(extracted.read_bytes(), payload)
            self.assertEqual(len(report["source_sha256"]), 2)

    def test_rejects_missing_split_volume(self):
        with tempfile.TemporaryDirectory() as td:
            root = pathlib.Path(td)
            archives, output = root / "archives", root / "output"
            archives.mkdir()
            output.mkdir()
            (archives / "files.zip.001").write_bytes(b"one")
            (archives / "files.zip.003").write_bytes(b"three")
            groups = process_archive_sets.archive_groups(archives)
            with self.assertRaises(ValueError):
                process_archive_sets.process_group(archives, output, groups[0][0], groups[0][1])

    def test_source_manifest_records_hashes_and_provenance(self):
        with tempfile.TemporaryDirectory() as td:
            root = pathlib.Path(td)
            source = root / "firmware/archives/mt8163"
            source.mkdir(parents=True)
            payload = b"public firmware sample"
            (source / "sample.bin").write_bytes(payload)
            output = root / "firmware/manifests/source.json"
            subprocess.run([
                sys.executable, str(ROOT / "scripts/firmware/build_source_manifest.py"),
                "--source-repository", "owner/repo", "--source-ref", "main",
                "--source-commit", "abc123", "--output", str(output)
            ], cwd=root, check=True, capture_output=True, text=True)
            manifest = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(manifest["source"]["commit"], "abc123")
            self.assertEqual(manifest["file_count"], 1)
            self.assertEqual(manifest["files"][0]["sha256"], hashlib.sha256(payload).hexdigest())


if __name__ == "__main__":
    unittest.main()
