# MicroSpek CLI reference

## Invocation

Installed command (after `python install.py --mode system --yes`):

```sh
microspek [flags]
```

From source checkout:

```sh
python run_microspek.py [flags]
python -m microspek [flags]      # with src/ on PYTHONPATH
```

Standalone editions use their own binary names:

```sh
microspek.exe [flags]            # full and cli editions
microspek-snapshot.exe [flags]   # snapshot edition
```

## Flags

| Flag | Effect |
| --- | --- |
| `--gui` | open the Tkinter GUI (default when no other action is given) |
| `--summary` | print a short per-section summary to stdout |
| `--snapshot` | print the full TXT snapshot to stdout |
| `--output {txt,json,md}` | save the report to a file |
| `--file PATH` | output path (default: `microspek_snapshot_<timestamp>.<ext>`) |
| `--redact` | replace sensitive values with `скрыто` / `hidden` |
| `--lang {ru,en}` | interface and report language |
| `--sections LIST` | collect only the listed sections (comma-separated keys) |
| `--no-sensors` | do not run the sensor helper (faster, no temperatures/SMART) |
| `--no-dxdiag` | skip the slow dxdiag report |
| `--dxdiag-timeout SEC` | dxdiag timeout, default 60 |
| `--admin-sensors` | one UAC prompt: CPU temperatures and disk SMART |
| `--config PATH` | read defaults from `microspek.json` |
| `--version` | print the version |

Flags can be combined, e.g.
`microspek --output md --lang en --redact --file report.md`.

## Configuration file

`microspek.json` is optional for the CLI and the main configuration for the
snapshot edition. It is looked up in the current directory and, for a frozen
executable, next to the `.exe`. Unknown keys are ignored; command-line flags
win over the file.

```json
{
  "output": "md",
  "file": "reports/pc.md",
  "redact": true,
  "sections": ["os", "cpu", "memory", "storage", "gpu"],
  "sensors": true,
  "dxdiag": false,
  "admin_sensors": false,
  "lang": "en",
  "open": false,
  "quiet": false,
  "stdout": false
}
```

- `output` — `txt`, `json` or `md` (`markdown` is accepted).
- `file` — relative paths are resolved next to the config file.
- `sections` — list or comma string; `all`, `*` or an empty value means every
  section.
- `open` — open the finished report in the default application.

## Sections

`os`, `motherboard`, `cpu`, `memory`, `storage`, `gpu`, `network`, `devices`,
`dxdiag` (only when dxdiag is enabled).

Notable groups (Russian titles are translated in EN output):

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
  "schema": "microspek.snapshot/1",
  "language": "en",
  "generated_at": "2026-11-18T16:00:00",
  "hostname": "PC-NAME",
  "platform": "Windows-11-10.0.26300-SP0",
  "warnings": [],
  "sections": [
    {
      "key": "cpu",
      "title": "Processor",
      "summary": [{"label": "Processor", "value": "...", "note": "", "sensitive": false}],
      "groups": [
        {"title": "General", "items": [
          {"label": "Model", "value": "...", "note": "", "sensitive": false}
        ]}
      ]
    }
  ],
  "layouts": [
    {
      "title": "Disk 0 — SSD (476.9 GiB)",
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

## Markdown shape

`--output md` writes one heading per section, a table per group, a table for
each disk layout and a warnings list. Pipes and newlines inside values are
escaped, so the file renders correctly in GitHub, Notion and Obsidian.

## Quick jq examples

```sh
microspek --output json --file snap.json
jq -r '.sections[] | select(.key=="gpu") | .summary[] | "\(.label): \(.value)"' snap.json
jq -r '.layouts[] | .title' snap.json
jq '.warnings' snap.json
```
