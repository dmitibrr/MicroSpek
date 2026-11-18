"""Network adapters and TCP/IP configuration collector."""

from __future__ import annotations

from ..models import Group, Item, Section
from ..util import first, ps_json

SCRIPT = r"""
$ErrorActionPreference='SilentlyContinue'
$adapters = @(Get-NetAdapter | Select-Object Name,InterfaceDescription,Status,LinkSpeed,MacAddress,ifIndex)
$configs = @(Get-CimInstance Win32_NetworkAdapterConfiguration | Where-Object {$_.IPEnabled} |
    Select-Object Description,IPAddress,IPSubnet,DefaultIPGateway,DNSServerSearchOrder,MACAddress,DHCPEnabled)
[pscustomobject]@{ adapters=$adapters; configs=$configs } | ConvertTo-Json -Depth 5 -Compress
"""


def _join(values: object) -> str:
    if isinstance(values, list):
        parts = [str(item) for item in values if item not in (None, "")]
        return ", ".join(parts) if parts else "—"
    return first(values)


def collect_network() -> Section:
    data = ps_json(SCRIPT) or {}
    adapters = data.get("adapters") or []
    configs = data.get("configs") or []
    active = [a for a in adapters if str(a.get("Status") or "").lower() == "up"]
    summary = [
        Item("Активные адаптеры", ", ".join(str(a.get("Name")) for a in active) or "—"),
        Item("Всего адаптеров", str(len(adapters))),
    ]
    groups: list[Group] = []
    for adapter in adapters:
        description = str(adapter.get("InterfaceDescription") or "")
        config = next(
            (c for c in configs if str(c.get("Description") or "").lower() == description.lower()),
            {},
        )
        ipv4 = [ip for ip in (config.get("IPAddress") or []) if "." in str(ip)]
        ipv6 = [ip for ip in (config.get("IPAddress") or []) if ":" in str(ip)]
        groups.append(
            Group(
                f"{adapter.get('Name')} — {first(adapter.get('Status'))}",
                [
                    Item("Описание", first(adapter.get("InterfaceDescription"))),
                    Item("Состояние", first(adapter.get("Status"))),
                    Item("Скорость", first(adapter.get("LinkSpeed"))),
                    Item("MAC-адрес", first(adapter.get("MacAddress")) or first(config.get("MACAddress")), sensitive=True),
                    Item("IPv4", _join(ipv4)),
                    Item("IPv6", _join(ipv6)),
                    Item("Маска подсети", _join(config.get("IPSubnet"))),
                    Item("Шлюз", _join(config.get("DefaultIPGateway"))),
                    Item("DNS", _join(config.get("DNSServerSearchOrder"))),
                    Item("DHCP", "да" if config.get("DHCPEnabled") else "нет" if config else "—"),
                ],
            )
        )
    return Section("network", "Сеть", groups, summary)
