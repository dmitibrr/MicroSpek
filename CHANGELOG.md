# Changelog

All notable changes to this project are documented here.

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
- TPM is detected with `tpmtool` (0.1 s) instead of `Win32_Tpm` (5.6 s),
  with the WMI path kept as a fallback.
- Physical disks use `MSFT_PhysicalDisk` from the Storage CIM namespace;
  the slow `Get-PhysicalDisk`/`Get-StorageReliabilityCounter` pair is gone.

Fixed:

- GPU sensors were attached twice when Windows reported a phantom display
  adapter with `Status = Error`.

## [0.1.1] — 2026-11-18

Fixes found in real snapshots (own PC + Lenovo ThinkCentre M79 / 10JA):

- Monitor connection codes now follow D3DKMDT_VIDEO_OUTPUT_TECHNOLOGY:
  4 = DVI, 5 = HDMI, 10 = DisplayPort, 15 = Miracast (previous mapping was
  off by one; DVI was shown as HDMI and DisplayPort as Miracast).
- Disk segment kind: partition type "Installable File System" is no longer
  mistaken for EFI (it contains the substring "system").
- CPU cache: L3 = 0 from WMI (AMD A10 PRO-7800B) is shown as "—", not "0 Б".
- Disk interface: prefer MSFT_PhysicalDisk.BusType (SATA/NVMe/USB) instead of
  the useless "IDE" stub from Win32_DiskDrive.
- Bluetooth adapter: driver lookup no longer requires "Adapter" in the PnP
  driver name; falls back to the adapter device from Get-PnpDevice.
- dxdiag: duplicate sound device names are no longer repeated.
- CLI: `--file` without `--output` now saves a TXT snapshot.
- Added regression tests for all of the above.

## [0.1.0] — 2026-11-18

First public release.

### Added

- GUI on Tkinter: summary tab, per-section tabs, coloured disk-layout canvas,
  snapshot/JSON/PNG export, window screenshot, redaction toggle.
- CLI: `--summary`, `--snapshot`, `--output {txt,json,png}`, `--file`,
  `--redact`, `--no-dxdiag`, `--dxdiag-timeout`, `--gui`.
- Collectors: OS (UEFI/Secure Boot/TPM), motherboard/BIOS, CPU, RAM
  (XMP/JEDEC inference), storage (partitions, volumes, allocated/used space),
  GPU (WMI + nvidia-smi), monitors (EDID), network, PnP devices
  (audio/Bluetooth/problems/SATA mode), optional DirectX via dxdiag.
- Installer with portable and fixed-location modes, PATH command registration,
  shortcuts, uninstaller and global AI skill installation.
- OpenCode skill `.opencode/skills/microspek` for native agent use.

### Fixed

- PowerShell OEM/Cyrillic output decoding (forced UTF-8).
- Duplicate `cores` key in the CPU collector PowerShell script.
- Cache units: WMI reports L2/L3 in kilobytes.
- Missing `import tempfile` in the dxdiag collector.
- "ИТОГО ... занято" label in the disk layout (now "размечено"; used space
  shown per volume, hidden for LDM spans).
- GPU telemetry duplicated on a phantom secondary controller.
