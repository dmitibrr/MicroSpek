"""Operating system collector."""

from __future__ import annotations

import re
import socket

from ..models import Group, Item, Section
from ..util import first, format_date, format_duration, parse_wmi_date, ps_json

SCRIPT = r"""
$ErrorActionPreference='SilentlyContinue'
$os = Get-CimInstance Win32_OperatingSystem | Select-Object Caption,Version,BuildNumber,OSArchitecture,InstallDate,LastBootUpTime,LocalDateTime,SystemDirectory,Locale,RegisteredUser,Organization
$tz = Get-CimInstance Win32_TimeZone | Select-Object -First 1 Caption,StandardName
$fw = $env:firmware_type
$secureboot = (Get-ItemProperty 'HKLM:\SYSTEM\CurrentControlSet\Control\SecureBoot\State' -ErrorAction SilentlyContinue).UEFISecureBootEnabled
# Win32_Tpm spends ~5 s looking for a TPM that is not there; tpmtool answers
# in ~0.1 s. Keep the WMI path only as a fallback for systems without tpmtool.
$tpm = $null; $tpmRaw = $null; $tpmCode = $null
if (Get-Command tpmtool.exe -ErrorAction SilentlyContinue) {
    $tpmRaw = (& tpmtool.exe getdeviceinformation 2>&1 | Out-String)
    $tpmCode = $LASTEXITCODE
} else {
    $tpm = Get-CimInstance -Namespace 'root/CIMV2/Security/MicrosoftTpm' -ClassName Win32_Tpm -ErrorAction SilentlyContinue |
        Select-Object -First 1 SpecVersion,IsEnabled_InitialValue,IsActivated_InitialValue
}
[pscustomobject]@{ os=$os; timezone=$tz.Caption; firmware=$fw; secureboot=$secureboot
    tpm=$tpm; tpm_raw=$tpmRaw; tpm_code=$tpmCode } | ConvertTo-Json -Depth 4 -Compress
"""


def _uptime(data: dict) -> str:
    boot = parse_wmi_date(data.get("LastBootUpTime"))
    now = parse_wmi_date(data.get("LocalDateTime"))
    if boot and now and now > boot:
        return format_duration((now - boot).total_seconds())
    return "—"


def _tpm_text(data: dict) -> str:
    raw = data.get("tpm_raw")
    if raw is not None:
        code = data.get("tpm_code")
        if code not in (0, None):
            return "не найден / недоступен"
        match = re.search(r"\b(1\.2|2\.0)\b", str(raw))
        return f"есть, версия {match.group(1)}" if match else "есть"
    tpm = data.get("tpm") or {}
    if not tpm:
        return "не найден / недоступен"
    parts = [first(tpm.get("SpecVersion"))]
    enabled = tpm.get("IsEnabled_InitialValue")
    activated = tpm.get("IsActivated_InitialValue")
    if enabled is not None:
        parts.append("включён" if enabled else "выключен")
    if activated is not None:
        parts.append("активен" if activated else "не активирован")
    return ", ".join(part for part in parts if part and part != "—")


def collect_os() -> Section:
    data = ps_json(SCRIPT) or {}
    os_data = data.get("os") or {}
    uptime = _uptime(os_data)
    firmware = first(data.get("firmware")) or "—"
    secureboot = data.get("secureboot")
    secureboot_text = "—" if secureboot is None else ("включён" if secureboot else "выключен")
    tpm_text = _tpm_text(data)
    summary = [
        Item("Операционная система", first(os_data.get("Caption"))),
        Item("Сборка", f"{first(os_data.get('Version'))} ({first(os_data.get('BuildNumber'))})"),
        Item("Время работы", uptime),
        Item("Имя компьютера", socket.gethostname()),
        Item("Загрузка", f"{firmware}, Secure Boot: {secureboot_text}"),
    ]
    groups = [
        Group(
            "Операционная система",
            [
                Item("Название", first(os_data.get("Caption"))),
                Item("Версия", first(os_data.get("Version"))),
                Item("Сборка", first(os_data.get("BuildNumber"))),
                Item("Разрядность", first(os_data.get("OSArchitecture"))),
                Item("Установлена", format_date(os_data.get("InstallDate"))),
                Item("Последняя перезагрузка", format_date(os_data.get("LastBootUpTime"))),
                Item("Время работы", uptime),
                Item("Часовой пояс", first(data.get("timezone"))),
                Item("Системная папка", first(os_data.get("SystemDirectory"))),
                Item("Локаль", first(os_data.get("Locale"))),
                Item("Зарегистрированный пользователь", first(os_data.get("RegisteredUser")), sensitive=True),
                Item("Организация", first(os_data.get("Organization")), sensitive=True),
            ],
        ),
        Group(
            "Загрузка и безопасность",
            [
                Item("Режим прошивки", firmware),
                Item("Secure Boot", secureboot_text),
                Item("TPM", tpm_text),
            ],
        ),
    ]
    return Section("os", "Операционная система", groups, summary)
