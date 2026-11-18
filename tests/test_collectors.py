"""Regression tests for bugs found in real snapshots (no PowerShell needed)."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from microspek.collectors.cpu import _kb_to_bytes
from microspek.collectors.gpu import VIDEO_OUTPUT
from microspek.collectors.storage import _kind
from microspek.models import format_bytes


class TestRealSnapshotBugs(unittest.TestCase):
    def test_installable_file_system_is_not_efi(self) -> None:
        # Lenovo ThinkCentre M79: тип раздела "Installable File System"
        # содержит подстроку "system", но это обычные данные, не EFI.
        part = {"Type": "Installable File System", "Size": 500 * 1024**3}
        assert _kind(part, "D:") == "data"

    def test_gpt_system_is_efi(self) -> None:
        assert _kind({"Type": "GPT: System", "Size": 100 * 1024**2}, "") == "efi"
        assert _kind({"Type": "EFI System Partition", "Size": 100 * 1024**2}, "") == "efi"

    def test_zero_cache_is_unknown(self) -> None:
        # AMD A10 PRO-7800B сообщает L3 = 0 — это «нет данных», а не 0 байт.
        assert _kb_to_bytes(0) is None
        assert format_bytes(_kb_to_bytes(0)) == "не удалось определить"

    def test_video_output_codes_match_d3dkmdt(self) -> None:
        assert VIDEO_OUTPUT[4] == "DVI"      # было ошибочно HDMI
        assert VIDEO_OUTPUT[5] == "HDMI"
        assert VIDEO_OUTPUT[10] == "DisplayPort"  # было ошибочно Miracast
        assert VIDEO_OUTPUT[15] == "Miracast"
