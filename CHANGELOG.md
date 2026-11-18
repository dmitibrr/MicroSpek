# Changelog

All notable changes to this project are documented here.

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
