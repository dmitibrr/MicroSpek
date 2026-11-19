# Changelog

All notable changes to this project are documented here.

## [0.3.0] — 2026-11-18

Four editions, two languages and a Markdown snapshot. MicroSpek is now public
domain (Unlicense) and no longer produces PNG reports.

Added:

- **Four standalone editions**, all built from one code base by
  `scripts/build_exe.py --edition all`:
  - `full` — GUI + CLI + sensor helper + `SNAPSHOT.cmd`;
  - `gui` — only the redesigned windowed app;
  - `cli` — only the console application for scripts and AI agents;
  - `snapshot` — `microspek-snapshot.exe`, the smallest build: no Tkinter, no
    Pillow, configured entirely through `microspek.json`.
- **English / Russian interface and reports.** The RU/EN switch lives in the GUI
  header; `--lang en` does the same for the CLI. Snapshots are still collected
  in Russian internally and translated at display time, so switching languages
  never re-runs the collectors.
- **Markdown snapshot** (`--output md`, GUI menu «Экспорт ▾»): tables that render
  in Notion, Obsidian, GitHub and AI chats.
- `microspek.json` — a configuration file for defaults: output format, file
  name, redaction, section list, sensors, dxdiag, language, open/quiet.
- `--sections` and `--no-sensors`: collect only what is needed. On the dev PC
  the `snapshot` edition with `os,cpu,memory,storage,gpu` takes about 3 seconds.
- `microspek.snapshot/1` JSON schema marker and a `language` field in JSON.
- 19 new offline tests: Markdown, i18n, configuration and the snapshot edition
  (33 tests total).

Changed:

- **GUI redesign**: quiet light palette, single «Экспорт ▾» button for
  TXT/JSON/Markdown, language switch, zebra tables, status dot, localized tabs,
  disk-layout canvas redrawn when its tab becomes visible.
- The old «Слепок TXT» and «JSON / PNG-отчёт» buttons are merged into one
  export menu; the PNG *report* is gone (the window screenshot button stays).
- CLI help is localized and follows `--lang`; `--config` is available in both
  the CLI and the snapshot edition.
- `README.md` is now English with a Russian twin, `README.ru.md`, both with
  regenerated neumorphic artwork and a real screenshot of the new window.
- `LICENSE` is the Unlicense: use, modify and redistribute without attribution.

Removed:

- PNG report rendering (`render_png`, Pillow layout code, `--output png`).
  Pillow is now needed only for the optional window screenshot.

## [0.2.0] — 2026-11-18

Hardware sensors and a much faster collector.

Added:

- `MicroSpekSensors.exe` — a tiny C# helper (.NET Framework 4.8) that exposes
  LibreHardwareMonitorLib 0.9.6 as JSON: GPU temperature/hot spot/fan RPM/power/
  voltage, disk SMART temperatures and remaining life, CPU package/core
  temperatures, fan speeds and Super I/O voltages when available.
- `--admin-sensors`: one UAC prompt for CPU temperatures and disk SMART data;
  `SNAPSHOT.cmd` enables it. Declining falls back silently.
- GUI button «Датчики (админ)» and a sensor status line in the status bar.
- `scripts/fetch_sensors_vendor.py` (NuGet vendor download) and
  `scripts/build_sensors.py` (csc-based build of the helper).

Changed:

- Collectors run concurrently: a full snapshot on the dev PC dropped from
  14.3 s to ~4.5 s, because nine PowerShell startups no longer add up.
- PnP devices come from a single `Win32_PnPEntity` query instead of three
  `Get-PnpDevice` calls (that module costs ~3.5 s per cold process).
- TPM state comes from `tpmtool` (~0.1 s) instead of `Win32_Tpm` (~5 s when no
  TPM is present).
- Disk SMART temperatures are merged into the disk sections without a second
  WMI pass.

Fixed:

- Zero cache values from WMI are reported as unknown instead of `0 КиБ`.
- `Installable File System` partitions are no longer classified as EFI.
- GPU sensor lookup does not guess between two adapters with the same name.

## [0.1.1] — 2026-11-17

- First public test build: GUI, CLI, TXT/JSON/PNG reports, disk layout canvas.
