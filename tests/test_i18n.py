"""Offline tests: RU/EN translation layer (no PowerShell required)."""

from __future__ import annotations

import sys
import unittest
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from microspek import i18n
from microspek.models import DiskLayout, Group, Item, PartitionSegment, Section, Snapshot


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
        layouts=[
            DiskLayout(
                "Диск 0 — Test SSD (100 ГиБ)",
                total_size=100 * 1024**3,
                segments=[PartitionSegment("C:", 100 * 1024**3, "data", used=40 * 1024**3)],
            )
        ],
        warnings=["тестовое предупреждение"],
    )


class I18nTests(unittest.TestCase):
    def tearDown(self) -> None:
        i18n.set_language("ru")

    def test_russian_is_returned_unchanged(self) -> None:
        i18n.set_language("ru")
        self.assertEqual(i18n.t("Серийный номер"), "Серийный номер")
        self.assertEqual(i18n.t("1,00 ГиБ"), "1,00 ГиБ")

    def test_labels_and_units(self) -> None:
        i18n.set_language("en")
        self.assertEqual(i18n.t("Серийный номер"), "Serial number")
        self.assertEqual(i18n.t("1,00 ГиБ"), "1.00 GiB")
        self.assertEqual(i18n.t("3,50 ГГц"), "3.50 GHz")
        self.assertEqual(i18n.t("1647 об/мин"), "1647 RPM")
        self.assertEqual(i18n.t("64-разрядная"), "64-bit")

    def test_generated_titles(self) -> None:
        i18n.set_language("en")
        self.assertEqual(i18n.t("Диск 0: Test SSD"), "Disk 0: Test SSD")
        self.assertEqual(i18n.t("Модуль 2 — ChannelA-DIMM1"), "Module 2 — ChannelA-DIMM1")
        self.assertEqual(
            i18n.t("Disk 4: ST3320413CS — модель"), "Disk 4: ST3320413CS — model"
        )

    def test_ui_strings(self) -> None:
        i18n.set_language("en")
        self.assertEqual(i18n.s("refresh"), "Refresh")
        i18n.set_language("ru")
        self.assertEqual(i18n.s("refresh"), "Обновить")
        # Unknown keys fall back to the key itself, never raise.
        self.assertEqual(i18n.s("no_such_key"), "no_such_key")

    def test_localize_snapshot_does_not_mutate_source(self) -> None:
        snapshot = make_snapshot()
        view = i18n.localize_snapshot(snapshot, "en")
        self.assertEqual(view.sections[0].title, "Processor")
        self.assertEqual(view.sections[0].groups[0].title, "General")
        self.assertEqual(view.sections[0].groups[0].items[0].label, "Model")
        self.assertIn("Disk 0", view.layouts[0].title)
        self.assertEqual(snapshot.sections[0].title, "Процессор")
        self.assertEqual(snapshot.layouts[0].title, "Диск 0 — Test SSD (100 ГиБ)")

    def test_detect_language_env_override(self) -> None:
        import os

        previous = os.environ.get("MICROSPEK_LANG")
        try:
            os.environ["MICROSPEK_LANG"] = "en"
            self.assertEqual(i18n.detect_language(), "en")
            os.environ["MICROSPEK_LANG"] = "ru"
            self.assertEqual(i18n.detect_language(), "ru")
        finally:
            if previous is None:
                os.environ.pop("MICROSPEK_LANG", None)
            else:
                os.environ["MICROSPEK_LANG"] = previous


if __name__ == "__main__":
    unittest.main()
