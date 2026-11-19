"""Offline tests: lightweight snapshot edition entry point (collector patched)."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from microspek import i18n, snapshot_cli
from microspek.models import Group, Item, Section, Snapshot


def make_snapshot() -> Snapshot:
    return Snapshot(
        generated_at=datetime(2026, 11, 18, 16, 0, 0),
        hostname="TEST-PC",
        platform="Windows-11-10.0.26300-SP0",
        sections=[
            Section(
                "cpu",
                "Процессор",
                groups=[Group("Основное", [Item("Модель", "Test CPU")])],
                summary=[Item("Процессор", "Test CPU")],
            )
        ],
    )


class SnapshotEditionTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self._tmp.name)

    def tearDown(self) -> None:
        self._tmp.cleanup()
        i18n.set_language("ru")

    def test_main_writes_configured_report(self) -> None:
        config = self.dir / "microspek.json"
        config.write_text(
            json.dumps(
                {
                    "output": "md",
                    "file": "reports/pc.md",
                    "sections": ["cpu"],
                    "sensors": False,
                    "lang": "en",
                    "quiet": True,
                }
            ),
            encoding="utf-8",
        )
        with mock.patch.object(snapshot_cli, "collect_snapshot", return_value=make_snapshot()):
            code = snapshot_cli.main(["--config", str(config)])
        self.assertEqual(code, 0)
        report = self.dir / "reports" / "pc.md"
        self.assertTrue(report.is_file())
        text = report.read_text(encoding="utf-8")
        self.assertIn("# MicroSpek — system snapshot", text)
        self.assertIn("## Processor", text)

    def test_cli_overrides_config(self) -> None:
        config = self.dir / "microspek.json"
        config.write_text(json.dumps({"output": "txt", "quiet": True}), encoding="utf-8")
        target = self.dir / "override.json"
        with mock.patch.object(snapshot_cli, "collect_snapshot", return_value=make_snapshot()):
            code = snapshot_cli.main(
                ["--config", str(config), "--output", "json", "--file", str(target), "--quiet"]
            )
        self.assertEqual(code, 0)
        data = json.loads(target.read_text(encoding="utf-8"))
        self.assertEqual(data["hostname"], "TEST-PC")

    def test_broken_config_returns_2(self) -> None:
        config = self.dir / "broken.json"
        config.write_text("{", encoding="utf-8")
        self.assertEqual(snapshot_cli.main(["--config", str(config)]), 2)


if __name__ == "__main__":
    unittest.main()
