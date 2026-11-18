"""Regression tests for bugs found in real snapshots (no PowerShell needed)."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from microspek.collectors import sensors as sensor_hub
from microspek.collectors.cpu import _kb_to_bytes
from microspek.collectors.gpu import VIDEO_OUTPUT
from microspek.collectors.os_info import _tpm_text
from microspek.collectors.storage import MEDIA_TYPES, _enum_text, _kind
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

    def test_msft_physical_disk_enums(self) -> None:
        # CIM отдаёт числа: 11 = SATA, 4 = SSD, 0 = Healthy.
        assert _enum_text(11, {11: "SATA"}) == "SATA"
        assert _enum_text("11", {11: "SATA"}) == "SATA"
        assert _enum_text(4, MEDIA_TYPES) == "SSD"
        assert _enum_text("4", MEDIA_TYPES) == "SSD"
        assert _enum_text(None, MEDIA_TYPES) == "—"

    def test_tpm_text_prefers_tpmtool(self) -> None:
        assert _tpm_text({"tpm_raw": "TPM Present: True\nTPM Version: 2.0\n", "tpm_code": 0}) == "есть, версия 2.0"
        assert _tpm_text({"tpm_raw": "TPM is not ready", "tpm_code": -2147020577}) == "не найден / недоступен"
        assert _tpm_text({"tpm": {"SpecVersion": "2.0"}}) == "2.0"
        assert _tpm_text({}) == "не найден / недоступен"


def _sensor_payload() -> dict:
    return {
        "ok": True,
        "hardware": [
            {
                "name": "Intel Xeon E3-1270 v3",
                "type": "Cpu",
                "sensors": [
                    {"type": "Temperature", "name": "CPU Package", "value": 45},
                    {"type": "Temperature", "name": "CPU Core #1", "value": 43},
                    {"type": "Fan", "name": "CPU Fan", "value": 1200},
                ],
                "children": [],
            },
            {
                "name": "NVIDIA GeForce RTX 2060 SUPER",
                "type": "GpuNvidia",
                "sensors": [
                    {"type": "Temperature", "name": "GPU Core", "value": 48},
                    {"type": "Temperature", "name": "GPU Hot Spot", "value": 61.5},
                ],
                "children": [
                    {
                        "name": "GPU Fan",
                        "type": "Cooler",
                        "sensors": [{"type": "Fan", "name": "GPU Fan", "value": 1647}],
                        "children": [],
                    },
                ],
            },
        ],
    }


class TestSensors(unittest.TestCase):
    def test_find_reading_walks_children(self) -> None:
        sensors = sensor_hub.Sensors(_sensor_payload())
        gpu = sensors.gpu("NVIDIA GeForce RTX 2060 SUPER")
        assert gpu is not None
        assert gpu.find_reading("GPU Hot Spot").value == 61.5
        # Вентилятор лежит во вложенном устройстве.
        assert gpu.find_reading("GPU Fan").value == 1647

    def test_gpu_lookup_does_not_guess_between_two_adapters(self) -> None:
        payload = _sensor_payload()
        second = dict(payload["hardware"][1])
        second["name"] = "Intel HD Graphics 4600"
        payload["hardware"].append(second)
        sensors = sensor_hub.Sensors(payload)
        assert sensors.gpu("NVIDIA GeForce RTX 2060 SUPER") is not None
        assert sensors.gpu("Microsoft Basic Display Adapter") is None

    def test_ru_names(self) -> None:
        assert sensor_hub.ru_name("CPU Package") == "Пакет CPU"
        assert sensor_hub.ru_name("CPU Core #3") == "Ядро 3"
        assert sensor_hub.ru_name("Fan #2") == "Вентилятор 2"
        assert sensor_hub.ru_name("GPU Hot Spot") == "Горячая точка GPU"
