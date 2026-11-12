import hashlib
import pathlib
import sys
import tempfile
import unittest
import warnings
import zipfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts" / "firmware"))
import archive_inventory
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
            self.assertEqual(result["archive_sha256"], hashlib.sha256(archive.read_bytes()).hexdigest())
            self.assertEqual(result["member_count"], 1)
            self.assertEqual(result["members"][0]["sha256"], hashlib.sha256(payload).hexdigest())

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


if __name__ == "__main__":
    unittest.main()
