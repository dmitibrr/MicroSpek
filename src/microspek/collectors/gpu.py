"""GPU collector: WMI video controllers, monitors (EDID) and nvidia-smi."""

from __future__ import annotations

from ..models import Group, Item, Section
from ..util import (
    command_output,
    first,
    format_bytes,
    format_date,
    format_fan,
    format_percent,
    format_temp,
    format_volts,
    format_watts,
    ps_json,
)
from . import sensors as sensor_hub

SCRIPT = r"""
$ErrorActionPreference='SilentlyContinue'
$gpus = @(Get-CimInstance Win32_VideoController | Select-Object Name,VideoProcessor,AdapterCompatibility,DriverVersion,DriverDate,AdapterRAM,CurrentHorizontalResolution,CurrentVerticalResolution,CurrentRefreshRate,Status,VideoModeDescription)
$monitors = @(Get-CimInstance -Namespace root/wmi -ClassName WmiMonitorID | ForEach-Object {
    [pscustomobject]@{
        instance=@($_.InstanceName); manufacturer=@($_.ManufacturerName);
        model=@($_.UserFriendlyName); product=@($_.ProductCodeID);
        serial=@($_.SerialNumberID); week=$_.WeekOfManufacture; year=$_.YearOfManufacture
    } })
$connections = @(Get-CimInstance -Namespace root/wmi -ClassName WmiMonitorConnectionParams | ForEach-Object {
    [pscustomobject]@{ instance=@($_.InstanceName); tech=$_.VideoOutputTechnology } })
[pscustomobject]@{ gpus=$gpus; monitors=$monitors; connections=$connections } |
    ConvertTo-Json -Depth 5 -Compress
"""

NVIDIA_FIELDS = (
    "name", "temperature.gpu", "utilization.gpu", "memory.used",
    "memory.total", "clocks.sm", "power.draw", "fan.speed", "driver_version",
)

# Значения D3DKMDT_VIDEO_OUTPUT_TECHNOLOGY (документация Microsoft):
# 0=HD15/VGA, 1=S-video, 2=composite, 3=component, 4=DVI, 5=HDMI,
# 6=LVDS/DSI, 8=D-JPN, 9=SDI, 10=DisplayPort, 11=eDP, 12/13=UDI,
# 14=SDTV-переходник, 15=Miracast, 16=Indirect wired, 0x80000000=внутренний.
VIDEO_OUTPUT = {
    0: "VGA (HD15)", 1: "S-video", 2: "Composite", 3: "Компонентный",
    4: "DVI", 5: "HDMI", 6: "LVDS / DSI", 8: "D-JPN", 9: "SDI",
    10: "DisplayPort", 11: "DisplayPort (встроенный)",
    12: "UDI", 13: "UDI (встроенный)", 14: "SDTV-переходник",
    15: "Miracast", 16: "Indirect wired", 0x80000000: "Внутренний",
}


def _nvidia_telemetry() -> list[dict[str, str]]:
    output = command_output(
        "nvidia-smi",
        ["--query-gpu=" + ",".join(NVIDIA_FIELDS), "--format=csv,noheader,nounits"],
        timeout=10.0,
    )
    if not output:
        return []
    rows: list[dict[str, str]] = []
    for line in output.splitlines():
        cells = [cell.strip() for cell in line.split(",")]
        if len(cells) >= len(NVIDIA_FIELDS):
            rows.append(dict(zip(NVIDIA_FIELDS, cells)))
    return rows


def _match_telemetry(name: str, rows: list[dict[str, str]]) -> dict[str, str]:
    target = name.lower()
    for row in rows:
        candidate = row.get("name", "").lower()
        if target in candidate or candidate in target:
            return row
    return {}


def _edid_text(values: object) -> str:
    if not isinstance(values, list):
        return "—"
    try:
        raw = bytes(int(v) & 0xFF for v in values if isinstance(v, (int, float)))
    except (TypeError, ValueError):
        return "—"
    text = raw.decode("ascii", errors="ignore").strip("\x00 \t\r\n")
    return text or "—"


def _instance_key(values: object) -> str:
    instance = _edid_text(values)
    if instance == "—":
        return ""
    return "\\".join(instance.split("\\")[:2]).upper()


def _sensor_value(device, kind: str, name: str) -> float | None:
    if device is None:
        return None
    for reading in device.readings(kind):
        if reading.name == name:
            return reading.value
    return None


def collect_gpu() -> Section:
    data = ps_json(SCRIPT) or {}
    controllers = data.get("gpus") or []
    if isinstance(controllers, dict):
        controllers = [controllers]
    monitors = data.get("monitors") or []
    connections = data.get("connections") or []
    if isinstance(connections, dict):
        connections = [connections]

    hub = sensor_hub.data()
    telemetry = _nvidia_telemetry()
    tele_used = False
    summary: list[Item] = []
    groups: list[Group] = []

    for index, gpu in enumerate(controllers, start=1):
        name = first(gpu.get("Name"))
        if index == 1:
            summary.append(Item("Видеокарта", name))
            summary.append(Item("Драйвер", first(gpu.get("DriverVersion"))))
        tele: dict[str, str] = {}
        if not tele_used and str(gpu.get("Status") or "").lower() != "error":
            tele = _match_telemetry(name, telemetry)
            if tele:
                tele_used = True
        resolution = "—"
        width = gpu.get("CurrentHorizontalResolution")
        height = gpu.get("CurrentVerticalResolution")
        if width and height:
            resolution = f"{width}x{height} @ {first(gpu.get('CurrentRefreshRate'))} Гц"
        items = [
            Item("Модель", name),
            Item("Производитель", first(gpu.get("AdapterCompatibility"))),
            Item("Видеопроцессор", first(gpu.get("VideoProcessor"))),
            Item("Версия драйвера", tele.get("driver_version") or first(gpu.get("DriverVersion"))),
            Item("Дата драйвера", format_date(gpu.get("DriverDate"))),
            Item("Видеопамять (WMI)", format_bytes(gpu.get("AdapterRAM"))),
            Item("Текущее разрешение", resolution),
            Item("Состояние", first(gpu.get("Status"))),
        ]
        if tele:
            items.extend([
                Item("Температура GPU", format_temp(tele.get("temperature.gpu"))),
                Item("Загрузка GPU", format_percent(tele.get("utilization.gpu"))),
                Item("Память занято", f"{tele.get('memory.used')} / {tele.get('memory.total')} МБ"
                     if tele.get("memory.used") and tele.get("memory.total") else "—"),
                Item("Частота SM", f"{tele.get('clocks.sm')} МГц" if tele.get("clocks.sm") else "—"),
                Item("Потребление", f"{tele.get('power.draw')} Вт" if tele.get("power.draw") else "—"),
                Item("Вентилятор", format_percent(tele.get("fan.speed"))),
            ])
        sensor_gpu = None
        if hub and str(gpu.get("Status") or "").lower() != "error":
            sensor_gpu = hub.gpu(name)
        if sensor_gpu:
            extra: list[Item] = []
            if not tele:
                core = _sensor_value(sensor_gpu, "Temperature", "GPU Core")
                if core is not None:
                    extra.append(Item("Температура GPU", format_temp(core)))
            hotspot = _sensor_value(sensor_gpu, "Temperature", "GPU Hot Spot")
            if hotspot is not None:
                extra.append(Item("Горячая точка GPU", format_temp(hotspot)))
            memory_junction = _sensor_value(sensor_gpu, "Temperature", "GPU Memory Junction")
            if memory_junction is not None:
                extra.append(Item("Температура памяти GPU", format_temp(memory_junction)))
            fan_rpm = _sensor_value(sensor_gpu, "Fan", "GPU Fan")
            if fan_rpm:
                control = _sensor_value(sensor_gpu, "Control", "GPU Fan")
                fan_text = format_fan(fan_rpm)
                if control is not None:
                    fan_text += f" ({control:.0f}%)"
                extra.append(Item("Вентилятор GPU (об/мин)", fan_text))
            voltage = _sensor_value(sensor_gpu, "Voltage", "GPU Core Voltage")
            if voltage:
                extra.append(Item("Напряжение ядра GPU", format_volts(voltage)))
            if not tele:
                power = (
                    _sensor_value(sensor_gpu, "Power", "GPU Package")
                    or _sensor_value(sensor_gpu, "Power", "GPU Board Power")
                    or _sensor_value(sensor_gpu, "Power", "GPU Power")
                )
                if power:
                    extra.append(Item("Потребление", format_watts(power)))
                used = _sensor_value(sensor_gpu, "SmallData", "GPU Memory Used")
                total_memory = _sensor_value(sensor_gpu, "SmallData", "GPU Memory Total")
                if used is not None and total_memory:
                    extra.append(Item("Память занято", f"{used:.0f} / {total_memory:.0f} МБ"))
                clock = _sensor_value(sensor_gpu, "Clock", "GPU Core")
                if clock:
                    extra.append(Item("Частота GPU", f"{clock:.0f} МГц"))
            items.extend(extra)
        groups.append(Group(f"Контроллер {index}", items))

    monitor_items: list[Item] = []
    for index, monitor in enumerate(monitors, start=1):
        key = _instance_key(monitor.get("instance"))
        tech = next(
            (c.get("tech") for c in connections if _instance_key(c.get("instance")) == key),
            None,
        )
        output_type = VIDEO_OUTPUT.get(int(tech), f"код {tech}") if tech is not None else "—"
        model = _edid_text(monitor.get("model"))
        monitor_items.extend([
            Item(f"Монитор {index} — модель", model),
            Item(f"Монитор {index} — производитель (EDID)", _edid_text(monitor.get("manufacturer"))),
            Item(f"Монитор {index} — ID изделия", _edid_text(monitor.get("product"))),
            Item(f"Монитор {index} — подключение", output_type),
            Item(f"Монитор {index} — выпущен",
                 f"{monitor.get('year')} г., неделя {monitor.get('week')}"
                 if monitor.get("year") else "—"),
            Item(f"Монитор {index} — серийный номер",
                 _edid_text(monitor.get("serial")), sensitive=True),
        ])
    if monitor_items:
        groups.append(Group("Мониторы (EDID)", monitor_items))
        summary.append(Item("Монитор", _edid_text(monitors[0].get("model")) if monitors else "—"))

    return Section("gpu", "Видеокарта", groups, summary)
