"""PnP devices: audio, Bluetooth, driver problems and SATA controller mode."""

from __future__ import annotations

from ..models import Group, Item, Section
from ..util import first, ps_json

SCRIPT = r"""
$ErrorActionPreference='SilentlyContinue'
$audio = @(Get-PnpDevice -Class AudioEndpoint -ErrorAction SilentlyContinue |
    Select-Object FriendlyName,Status)
$media = @(Get-PnpDevice -Class MEDIA -ErrorAction SilentlyContinue |
    Where-Object {$_.Status -eq 'OK'} | Select-Object FriendlyName,Status)
$bt = @(Get-PnpDevice -Class Bluetooth -ErrorAction SilentlyContinue |
    Where-Object {$_.InstanceId -like 'BTHENUM\DEV_*' -or $_.FriendlyName -like '*Bluetooth Adapter*' -or $_.FriendlyName -like '*Bluetooth USB*'} |
    Select-Object FriendlyName,Status,InstanceId)
$btDriver = @(Get-CimInstance Win32_PnPSignedDriver -ErrorAction SilentlyContinue |
    Where-Object {$_.DeviceClass -eq 'Bluetooth' -and $_.DeviceName -like '*Adapter*'} |
    Select-Object DeviceName,DriverVersion,Manufacturer)
$problems = @(Get-CimInstance Win32_PnPEntity -ErrorAction SilentlyContinue |
    Where-Object {$_.ConfigManagerErrorCode -ne 0} |
    Select-Object Name,ConfigManagerErrorCode,Status)
$storage = @(Get-Service -Name 'storahci','iaStorA','iaStorAC','amdhsasas','nvme' -ErrorAction SilentlyContinue |
    Where-Object {$_.Status -eq 'Running'} | Select-Object Name,DisplayName)
[pscustomobject]@{ audio=$audio; media=$media; bluetooth=$bt;
    bt_driver=$btDriver; problems=$problems; storage=$storage } |
    ConvertTo-Json -Depth 5 -Compress
"""

PROBLEM_CODES = {
    1: "устройство не работает", 10: "не удаётся запустить",
    12: "недостаточно ресурсов", 14: "требуется перезагрузка",
    16: "конфликт ресурсов", 19: "несовместимое оборудование",
    21: "устройство отключено", 22: "отключено пользователем",
    28: "нет драйвера", 31: "драйвер не загружен",
    39: "драйвер повреждён", 43: "сбой устройства (Code 43)",
    52: "подпись драйвера не подтверждена",
}


def _unique_names(rows: list[dict]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for row in rows:
        name = str(row.get("FriendlyName") or row.get("DeviceName") or "").strip()
        if name and name.lower() not in seen:
            seen.add(name.lower())
            result.append(name)
    return result


def _storage_mode(rows: list[dict]) -> str:
    names = [str(row.get("Name") or "").lower() for row in rows]
    if any(name.startswith("iastor") for name in names):
        return "Intel RAID / AHCI (iaStor)"
    if "storahci" in names:
        return "AHCI (storahci)"
    if "amdhsasas" in names:
        return "AMD AHCI / RAID"
    if "nvme" in names:
        return "NVMe"
    return "—"


def collect_devices() -> Section:
    data = ps_json(SCRIPT) or {}
    audio = data.get("audio") or []
    media = data.get("media") or []
    bluetooth = data.get("bluetooth") or []
    bt_driver = data.get("bt_driver") or []
    problems = data.get("problems") or []
    storage = data.get("storage") or []

    audio_names = _unique_names([row for row in audio if str(row.get("Status")).lower() == "ok"])
    mode = _storage_mode(storage)
    summary = [
        Item("Звуковые устройства", ", ".join(audio_names[:3]) or "—"),
        Item("Bluetooth-адаптер", first(bt_driver[0].get("DeviceName")) if bt_driver
             else (first(bluetooth[0].get("FriendlyName")) if bluetooth else "—")),
        Item("Проблемные устройства", str(len(problems))),
        Item("Режим SATA", mode),
    ]

    groups: list[Group] = []
    groups.append(Group(
        "Звук",
        [Item(f"Устройство {index}", name) for index, name in enumerate(audio_names, start=1)]
        + [Item(f"Драйвер {index}", name) for index, name in enumerate(_unique_names(media), start=1)],
    ))
    bt_items: list[Item] = []
    for index, adapter in enumerate(bt_driver or [{}], start=1):
        bt_items.extend([
            Item(f"Адаптер {index}", first(adapter.get("DeviceName"))),
            Item(f"Адаптер {index} — производитель", first(adapter.get("Manufacturer"))),
            Item(f"Адаптер {index} — драйвер", first(adapter.get("DriverVersion"))),
        ])
    for index, device in enumerate(bluetooth, start=1):
        bt_items.append(Item(f"Устройство {index}", f"{first(device.get('FriendlyName'))} ({first(device.get('Status'))})"))
    groups.append(Group("Bluetooth", bt_items or [Item("Результат", "адаптер не найден")]))

    problem_items = []
    for index, problem in enumerate(problems, start=1):
        code = problem.get("ConfigManagerErrorCode")
        try:
            description = PROBLEM_CODES.get(int(code), f"код {code}")
        except (TypeError, ValueError):
            description = f"код {code}"
        problem_items.append(Item(f"Устройство {index}", f"{first(problem.get('Name'))} — {description}"))
    groups.append(Group("Проблемы PnP", problem_items or [Item("Результат", "ошибок не обнаружено")]))

    groups.append(Group(
        "Контроллер накопителей",
        [Item("Активные драйверы", ", ".join(str(row.get("Name")) for row in storage) or "—"),
         Item("Режим", mode)],
    ))
    return Section("devices", "Устройства", groups, summary)
