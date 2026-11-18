"""Offline tests: rendering and redaction (no PowerShell required)."""

from __future__ import annotations

import json
import sys
import unittest
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from microspek.models import DiskLayout, Group, Item, PartitionSegment, Section, Snapshot, format_bytes
from microspek.render import render_json, render_txt, snapshot_to_dict


def make_snapshot() -> Snapshot:
    return Snapshot(
        generated_at=datetime(2026, 11, 18, 16, 0, 0),
        hostname="TEST-PC",
        platform="Windows-11-10.0.26300-SP0",
        sections=[
            Section(
                "cpu",
                "Процессор",
                groups=[Group("Основное", [
                    Item("Модель", "Test CPU"),
                    Item("Серийный номер", "SERIAL-123", sensitive=True),
                ])],
                summary=[Item("Процессор", "Test CPU")],
            )
        ],
        layouts=[
            DiskLayout(
                "Диск 0 — Test SSD (100 ГиБ)",
                total_size=100 * 1024**3,
                segments=[
                    PartitionSegment("C:", 100 * 1024**3, "data", used=40 * 1024**3),
                ],
            )
        ],
        warnings=["тестовое предупреждение"],
    )


class RenderTests(unittest.TestCase):
    def setUp(self) -> None:
        self.snapshot = make_snapshot()

    def test_format_bytes(self) -> None:
        self.assertEqual(format_bytes(1024), "1,00 КиБ")
        self.assertEqual(format_bytes(1024**3), "1,00 ГиБ")

    def test_txt_contains_sections_and_layout(self) -> None:
        text = render_txt(self.snapshot)
        self.assertIn("MicroSpek — слепок системы", text)
        self.assertIn("## Процессор", text)
        self.assertIn("SERIAL-123", text)
        self.assertIn("размечено", text)
        self.assertIn("занято 40,00 ГиБ", text)
        self.assertIn("тестовое предупреждение", text)

    def test_redaction_hides_sensitive(self) -> None:
        text = render_txt(self.snapshot, redacted=True)
        self.assertNotIn("SERIAL-123", text)
        self.assertIn("скрыто", text)

    def test_json_shape(self) -> None:
        data = json.loads(render_json(self.snapshot))
        self.assertEqual(data["hostname"], "TEST-PC")
        self.assertEqual(data["sections"][0]["key"], "cpu")
        self.assertEqual(data["layouts"][0]["segments"][0]["used"], 40 * 1024**3)
        self.assertEqual(len(data["warnings"]), 1)

    def test_redacted_json_has_no_serial(self) -> None:
        self.assertNotIn("SERIAL-123", render_json(self.snapshot, redacted=True))
        self.assertNotIn("SERIAL-123", json.dumps(snapshot_to_dict(self.snapshot, True)))


if __name__ == "__main__":
    unittest.main()
