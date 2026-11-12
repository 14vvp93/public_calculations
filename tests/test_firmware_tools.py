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
import import_public_firmware
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
            self.assertEqual(result["format"], "split-zip-volume")
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
            backslash_archive = root / "bad-backslash.zip"
            with zipfile.ZipFile(backslash_archive, "w") as zf:
                zf.writestr("..\\escape-backslash.txt", b"no")
            with self.assertRaises(ValueError):
                safe_extract.extract(backslash_archive, dest)
            self.assertFalse((root / "escape-backslash.txt").exists())

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


    def test_importer_verifies_copied_firmware_and_manifest(self):
        with tempfile.TemporaryDirectory() as td:
            root = pathlib.Path(td)
            source = root / "source"
            dumps = source / "reference-materials/firmware-dumps"
            heq = source / "reference-materials/heq"
            kernel_dir = source / "reference-materials/kernel"
            dumps.mkdir(parents=True)
            heq.mkdir(parents=True)
            kernel_dir.mkdir(parents=True)
            samples = {
                dumps / "files2.zip.001": b"archive-volume",
                dumps / "build.prop": b"ro.build.version.release=9",
                heq / "HEQ.zip.001": b"heq-volume",
                kernel_dir / "cd3313.ko": b"kernel-module",
            }
            for path, payload in samples.items():
                path.write_bytes(payload)
            result = import_public_firmware.import_inputs(
                source, root / "destination", "owner/source", "feature/test", "deadbeef", True
            )
            self.assertEqual(result["file_count"], 4)
            self.assertEqual(result["total_bytes"], sum(len(v) for v in samples.values()))
            for item in result["files"]:
                target = root / "destination" / item["path"]
                self.assertEqual(hashlib.sha256(target.read_bytes()).hexdigest(), item["sha256"])
                self.assertTrue(item["verified_copy"])
            manifest = root / "destination/firmware/manifests/mt8163-source-import.json"
            self.assertTrue(manifest.is_file())

    def test_importer_can_exclude_standalone_raw_dumps(self):
        with tempfile.TemporaryDirectory() as td:
            root = pathlib.Path(td)
            source = root / "source"
            dumps = source / "reference-materials/firmware-dumps"
            heq = source / "reference-materials/heq"
            kernel_dir = source / "reference-materials/kernel"
            dumps.mkdir(parents=True)
            heq.mkdir(parents=True)
            kernel_dir.mkdir(parents=True)
            (dumps / "files.zip.001").write_bytes(b"archive")
            (dumps / "build.prop").write_bytes(b"raw")
            (heq / "HEQ.zip.001").write_bytes(b"heq")
            (kernel_dir / "cd3313.ko").write_bytes(b"module")
            result = import_public_firmware.import_inputs(
                source, root / "destination", "owner/source", "main", "deadbeef", False
            )
            self.assertEqual(result["file_count"], 3)
            self.assertFalse((root / "destination/firmware/dumps/mt8163/build.prop").exists())

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


    def test_audio_stack_inventory_reports_policy_and_mixer_anomalies(self):
        with tempfile.TemporaryDirectory() as td:
            root = pathlib.Path(td)
            extracted = root / "extracted"
            vendor = extracted / "files2/files2/vendor"
            system = extracted / "files2/files2/system"
            dumps = root / "dumps"
            vendor.mkdir(parents=True)
            system.mkdir(parents=True)
            dumps.mkdir()
            (vendor / "audio_policy_configuration.xml").write_text(
                '<?xml version="1.0"?><audioPolicyConfiguration xmlns:xi="http://www.w3.org/2001/XInclude">'
                '<modules><module name="primary"><devicePorts><devicePort tagName="BT SCO Headset Mic" role="source">'
                '<profile channelMasks="AUDIO_CHANNEL_OUT_STEREO"/></devicePort></devicePorts></module></modules>'
                '<xi:include href="missing_volume_tables.xml"/></audioPolicyConfiguration>', encoding="utf-8")
            (vendor / "audio_device.xml").write_text(
                '<mixercontrol><path name="mic" value="off">><kctl name="ADC" value="Off"/></path></mixercontrol>',
                encoding="utf-8")
            (dumps / "init.mt8163.rc").write_text(
                'insmod /vendor/lib/modules/cd3313.ko\n'
                'insmod /vendor/lib/modules/ak7604.ko channel_gain=${ro.hw.ak7604.gain:-2,-2,2,0}\n',
                encoding="utf-8")
            (dumps / "build.prop").write_text("", encoding="utf-8")
            (dumps / "default.prop").write_text("", encoding="utf-8")
            output_json = root / "inventory.json"
            output_md = root / "inventory.md"
            subprocess.run([
                sys.executable, str(ROOT / "scripts/firmware/audio_stack_inventory.py"),
                "--extracted-root", str(extracted), "--dump-root", str(dumps),
                "--json", str(output_json), "--markdown", str(output_md)
            ], check=True, capture_output=True, text=True)
            result = json.loads(output_json.read_text(encoding="utf-8"))
            self.assertEqual(result["audio_policy"][0]["missing_includes"], ["missing_volume_tables.xml"])
            self.assertEqual(result["audio_policy"][0]["input_output_mask_mismatches"][0]["port"], "BT SCO Headset Mic")
            self.assertEqual(len(result["audio_device_xml"]["stray_text_paths"]), 1)
            self.assertTrue(output_md.is_file())


if __name__ == "__main__":
    unittest.main()
