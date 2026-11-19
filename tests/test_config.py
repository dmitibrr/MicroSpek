"""Offline tests: microspek.json configuration (no PowerShell required)."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from microspek.config import ConfigError, Settings, load_config, write_example
from microspek.snapshot import normalize_sections


class ConfigTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self._tmp.name)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def write(self, data: dict, name: str = "microspek.json") -> Path:
        path = self.dir / name
        path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        return path

    def test_explicit_missing_file_raises(self) -> None:
        with self.assertRaises(ConfigError):
            load_config(self.dir / "missing.json")

    def test_values_are_parsed(self) -> None:
        path = self.write(
            {
                "output": "markdown",
                "file": "out/pc.md",
                "redact": "yes",
                "sections": "cpu, storage;bogus",
                "sensors": False,
                "dxdiag": True,
                "admin_sensors": 1,
                "language": "EN",
                "open": True,
                "quiet": True,
                "stdout": True,
                "unknown": "ignored",
            }
        )
        settings = load_config(path)
        self.assertEqual(settings.output, "md")
        self.assertEqual(settings.file, "out/pc.md")
        self.assertTrue(settings.redact)
        self.assertEqual(settings.sections, ["cpu", "storage"])
        self.assertFalse(settings.sensors)
        self.assertTrue(settings.dxdiag)
        self.assertTrue(settings.admin_sensors)
        self.assertEqual(settings.lang, "en")
        self.assertTrue(settings.open_file)
        self.assertTrue(settings.quiet)
        self.assertTrue(settings.stdout)
        self.assertEqual(settings.values["unknown"], "ignored")

    def test_bad_values_keep_defaults(self) -> None:
        path = self.write({"output": "png", "sections": 42, "lang": "de"})
        settings = load_config(path, Settings())
        self.assertEqual(settings.output, "txt")
        self.assertIsNone(settings.sections)
        self.assertIsNone(settings.lang)

    def test_sections_all_and_list(self) -> None:
        path = self.write({"sections": "all"})
        self.assertIsNone(load_config(path).sections)
        path = self.write({"sections": ["os", "cpu", "cpu", "nope"]})
        self.assertEqual(load_config(path).sections, ["os", "cpu"])

    def test_broken_json_and_non_object(self) -> None:
        broken = self.dir / "broken.json"
        broken.write_text("{not json", encoding="utf-8")
        with self.assertRaises(ConfigError):
            load_config(broken)
        array = self.dir / "array.json"
        array.write_text("[1, 2]", encoding="utf-8")
        with self.assertRaises(ConfigError):
            load_config(array)

    def test_write_example_round_trips(self) -> None:
        path = write_example(self.dir / "microspek.json", lang="en")
        settings = load_config(path)
        self.assertEqual(settings.output, "md")
        self.assertEqual(settings.lang, "en")
        self.assertTrue(settings.redact)

    def test_normalize_sections(self) -> None:
        self.assertIsNone(normalize_sections(None))
        self.assertIsNone(normalize_sections("all"))
        self.assertEqual(normalize_sections("cpu, gpu"), ["cpu", "gpu"])
        self.assertEqual(normalize_sections(["GPU", "nope", "gpu"]), ["gpu"])
        self.assertIsNone(normalize_sections(""))


if __name__ == "__main__":
    unittest.main()
