# MicroSpek CLI reference

## Invocation

Installed command (after `python install.py --mode system --yes`):

```sh
microspek [flags]
```

From source checkout:

```sh
python run_microspek.py [flags]
python -m microspek [flags]      # from src/
```

## Flags

| Flag | Effect |
| --- | --- |
| `--gui` | open Tkinter GUI (default when no other action is given) |
| `--summary` | print short per-section summary to stdout |
| `--snapshot` | print full TXT snapshot to stdout |
| `--output {txt,json,png}` | save report to file |
| `--file PATH` | output path (default: `microspek_<timestamp>.<ext>`) |
| `--redact` | replace sensitive values with `скрыто` |
| `--no-dxdiag` | skip the slow dxdiag report |
| `--dxdiag-timeout SEC` | dxdiag timeout, default 60 |
| `--admin-sensors` | one UAC prompt: CPU temperatures and disk SMART (needs admin) |
| `--version` | print version |

Flags can be combined, e.g. `microspek --summary --output json --file report.json`.

## Sections

`os`, `motherboard`, `cpu`, `memory`, `storage`, `gpu`, `network`, `devices`,
`dxdiag` (only when dxdiag is enabled).

Notable groups:

- `os` → "Загрузка и безопасность": firmware (UEFI/Legacy), Secure Boot, TPM.
- `memory` → per-module SPD/working frequency and inferred `Профиль памяти`.
- `gpu` → video controllers (with nvidia-smi telemetry on the healthy one) and
  "Мониторы (EDID)" with model, manufacturer code and connection type.
  With LibreHardwareMonitorLib: "Горячая точка GPU", fan RPM/percent, voltage,
  VRAM usage (the `Датчики` lines inside each controller group).
- `cpu` → "Датчики (LibreHardwareMonitor)" appears when the PawnIO driver is
  installed: package/core temperatures, fan speed, package power.
- `motherboard` → "Датчики платы (Super I/O)": fans and voltages when available.
- `storage` → physical disks, volumes, partitions; `layouts` holds visual bars.
  Disk `температура` / `остаток ресурса` come from LHM (admin required).
- `devices` → audio, Bluetooth, PnP problems, SATA controller mode.

## JSON shape (excerpt)

```json
{
  "generated_at": "2026-11-18T16:00:00",
  "hostname": "PC-NAME",
  "platform": "Windows-11-10.0.26300-SP0",
  "warnings": [],
  "sections": [
    {
      "key": "cpu",
      "title": "Процессор",
      "summary": [{"label": "Процессор", "value": "...", "note": "", "sensitive": false}],
      "groups": [
        {"title": "Основное", "items": [
          {"label": "Модель", "value": "...", "note": "", "sensitive": false}
        ]}
      ]
    }
  ],
  "layouts": [
    {
      "title": "Диск 0 — SSD (476,9 ГиБ)",
      "total_size": 512105932800,
      "segments": [
        {"label": "C:", "size": 510933336064, "kind": "data", "used": 287600000000}
      ]
    }
  ]
}
```

`kind` values: `data`, `efi`, `recovery`, `service`, `ldm`, `free`.
`used` is `null` when the volume spans multiple disks (LDM) or is unknown.

## Quick jq examples

```sh
microspek --output json --file snap.json
jq -r '.sections[] | select(.key=="gpu") | .summary[] | "\(.label): \(.value)"' snap.json
jq -r '.layouts[] | .title' snap.json
jq '.warnings' snap.json
```
