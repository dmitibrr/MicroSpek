"""Motherboard, BIOS, chassis and system collector."""

from __future__ import annotations

from ..models import Group, Item, Section
from ..util import first, format_date, format_fan, format_temp, format_volts, ps_json
from . import sensors as sensor_hub

SCRIPT = r"""
$ErrorActionPreference='SilentlyContinue'
$board = Get-CimInstance Win32_BaseBoard | Select-Object -First 1
$bios = Get-CimInstance Win32_BIOS | Select-Object -First 1
$cs = Get-CimInstance Win32_ComputerSystem | Select-Object -First 1
$enc = Get-CimInstance Win32_SystemEnclosure | Select-Object -First 1
$bat = Get-CimInstance Win32_Battery | Select-Object -First 1
[pscustomobject]@{
    board_vendor=$board.Manufacturer; board_product=$board.Product;
    board_version=$board.Version; board_serial=$board.SerialNumber;
    bios_vendor=$bios.Manufacturer; bios_version=$bios.SMBIOSBIOSVersion;
    bios_date=$bios.ReleaseDate; bios_smbios=$bios.Version;
    sys_vendor=$cs.Manufacturer; sys_model=$cs.Model; sys_type=$cs.SystemType;
    sys_user=$cs.UserName; sys_domain=$cs.Domain;
    enc_vendor=$enc.Manufacturer; enc_model=$enc.Model;
    enc_serial=$enc.SerialNumber; chassis=@($enc.ChassisTypes);
    battery=@($bat | ForEach-Object { [pscustomobject]@{
        name=$_.Name; status=$_.BatteryStatus; level=$_.EstimatedChargeRemaining } })
} | ConvertTo-Json -Depth 4 -Compress
"""

CHASSIS = {
    1: "Другое", 2: "Unknown", 3: "Настольный ПК", 4: "Низкопрофильный",
    5: "Пирамида", 6: "Mini Tower", 7: "Tower", 8: "Портативный",
    9: "Ноутбук", 10: "Ноутбук (Notebook)", 11: "Карманный",
    12: "Docking Station", 13: "All-in-One", 14: "Субноутбук",
    15: "Компактный", 16: "Lunch Box", 17: "Серверный корпус",
    18: "Expansion Chassis", 19: "SubChassis", 20: "Bus Expansion",
    21: "Peripheral Chassis", 22: "RAID Chassis", 23: "Стойка (Rack)",
}


def _chassis(types: object) -> str:
    if not isinstance(types, list):
        return "—"
    names = [CHASSIS.get(int(t), str(t)) for t in types if str(t).isdigit()]
    return ", ".join(names) if names else "—"


def collect_motherboard() -> Section:
    data = ps_json(SCRIPT) or {}
    board = f"{first(data.get('board_vendor'))} {first(data.get('board_product'))}".strip()
    summary = [
        Item("Материнская плата", board),
        Item("BIOS", first(data.get("bios_version"))),
    ]
    groups = [
        Group(
            "Материнская плата",
            [
                Item("Производитель", first(data.get("board_vendor"))),
                Item("Модель", first(data.get("board_product"))),
                Item("Версия", first(data.get("board_version"))),
                Item("Серийный номер", first(data.get("board_serial")), sensitive=True),
            ],
        ),
        Group(
            "BIOS",
            [
                Item("Производитель", first(data.get("bios_vendor"))),
                Item("Версия", first(data.get("bios_version"))),
                Item("Дата", format_date(data.get("bios_date"))),
                Item("Спецификация", first(data.get("bios_smbios"))),
            ],
        ),
        Group(
            "Корпус / система",
            [
                Item("Тип корпуса", _chassis(data.get("chassis"))),
                Item("Производитель", first(data.get("enc_vendor"))),
                Item("Серийный номер корпуса", first(data.get("enc_serial")), sensitive=True),
                Item("Производитель системы", first(data.get("sys_vendor"))),
                Item("Модель системы", first(data.get("sys_model"))),
                Item("Тип системы", first(data.get("sys_type"))),
                Item("Пользователь", first(data.get("sys_user")), sensitive=True),
                Item("Рабочая группа / домен", first(data.get("sys_domain")), sensitive=True),
            ],
        ),
    ]
    batteries = data.get("battery") or []
    if batteries:
        items = []
        for index, battery in enumerate(batteries, start=1):
            items.append(
                Item(
                    f"Аккумулятор {index}: {battery.get('name', '?')}",
                    f"заряд {first(battery.get('level'))}%, статус {first(battery.get('status'))}",
                )
            )
        groups.append(Group("Питание", items))

    hub = sensor_hub.data()
    board = hub.motherboard() if hub else None
    if board:
        sensor_items: list[Item] = []
        for reading in board.readings("Temperature"):
            sensor_items.append(Item(sensor_hub.ru_name(reading.name), format_temp(reading.value)))
        for reading in board.readings("Fan"):
            sensor_items.append(Item(sensor_hub.ru_name(reading.name), format_fan(reading.value)))
        for reading in board.readings("Voltage"):
            sensor_items.append(Item(sensor_hub.ru_name(reading.name), format_volts(reading.value)))
        if sensor_items:
            groups.append(Group("Датчики платы (Super I/O)", sensor_items))
    return Section("motherboard", "Материнская плата", groups, summary)
