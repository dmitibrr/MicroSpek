"""PnP devices: audio, Bluetooth, driver problems and SATA controller mode."""

from __future__ import annotations

from ..models import Group, Item, Section
from ..util import first, ps_json

SCRIPT = r"""
$ErrorActionPreference='SilentlyContinue'
# Get-PnpDevice imports a slow module (~3.5 s on every cold process). Win32_PnPEntity
# returns the same device classes from a single fast WMI query.
$pnp = @(Get-CimInstance Win32_PnPEntity |
    Select-Object Name,Manufacturer,DeviceID,PNPClass,Status,ConfigManagerErrorCode,Service)
$btDriver = @(Get-CimInstance Win32_PnPSignedDriver -Filter "DeviceClass='Bluetooth'" |
    Select-Object DeviceName,DriverVersion,Manufacturer,Description)
$storage = @(Get-Service -Name 'storahci','iaStorA','iaStorAC','amdhsasas','nvme' -ErrorAction SilentlyContinue |
    Where-Object {$_.Status -eq 'Running'} | Select-Object Name,DisplayName)
[pscustomobject]@{ pnp=$pnp; bt_driver=$btDriver; storage=$storage } |
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
        name = str(row.get("Name") or row.get("FriendlyName") or row.get("DeviceName") or "").strip()
        if name and name.lower() not in seen:
            seen.add(name.lower())
            result.append(name)
    return result


def _class_rows(entities: list[dict], pnp_class: str) -> list[dict]:
    wanted = pnp_class.lower()
    return [row for row in entities if str(row.get("PNPClass") or "").lower() == wanted]


def _error_code(row: dict) -> int:
    try:
        return int(row.get("ConfigManagerErrorCode") or 0)
    except (TypeError, ValueError):
        return 0


def _is_adapter(row: dict) -> bool:
    """Bluetooth radio vs. a paired headset/phone."""
    device_id = str(row.get("DeviceID") or "").upper()
    if "DEV_" in device_id:  # BTHENUM\DEV_... is a paired peripheral
        return False
    name = str(row.get("Name") or "").lower()
    return "adapter" in name or "bluetooth" in name


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
    entities = data.get("pnp") or []
    bt_driver = data.get("bt_driver") or []
    storage = data.get("storage") or []

    audio = _class_rows(entities, "AudioEndpoint")
    media = [
        row for row in _class_rows(entities, "MEDIA")
        if str(row.get("Status")).lower() == "ok"
    ]
    bluetooth = _class_rows(entities, "Bluetooth")
    problems = [row for row in entities if _error_code(row) != 0]

    audio_names = _unique_names([row for row in audio if str(row.get("Status")).lower() == "ok"])
    mode = _storage_mode(storage)
    driver_rows = [
        row for row in bt_driver
        if "adapter" in str(row.get("DeviceName") or "").lower()
        or "adapter" in str(row.get("Description") or "").lower()
    ]
    if not driver_rows:
        driver_rows = [
            {"DeviceName": device.get("Name")}
            for device in bluetooth
            if _is_adapter(device)
        ]
    summary = [
        Item("Звуковые устройства", ", ".join(audio_names[:3]) or "—"),
        Item("Bluetooth-адаптер", first(driver_rows[0].get("DeviceName")) if driver_rows
             else (first(bluetooth[0].get("Name")) if bluetooth else "—")),
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
    for index, adapter in enumerate(driver_rows or [{}], start=1):
        bt_items.extend([
            Item(f"Адаптер {index}", first(adapter.get("DeviceName"))),
            Item(f"Адаптер {index} — производитель", first(adapter.get("Manufacturer"))),
            Item(f"Адаптер {index} — драйвер", first(adapter.get("DriverVersion"))),
        ])
    for index, device in enumerate(bluetooth, start=1):
        bt_items.append(Item(f"Устройство {index}", f"{first(device.get('Name'))} ({first(device.get('Status'))})"))
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
