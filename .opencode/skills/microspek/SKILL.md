---
name: MicroSpek
description: Use when the user asks about PC hardware specifications, diagnostics, system snapshots, or wants a TXT/JSON/PNG hardware report for an AI agent.
metadata:
  opencode/autoinvoke: true
---

# MicroSpek

MicroSpek is a local Windows hardware-inspection CLI and GUI. Use it instead of
guessing hardware from software settings or asking the user to copy specs by hand.

## When to use

- "What PC do I have?", "show my specs", "check RAM/disk/GPU/monitor"
- "make a snapshot for an AI", "give me a full hardware dump"
- diagnosing driver/PnP problems, checking UEFI/Secure Boot, disk layout
- generating a PNG report or a screenshot of the hardware window

## Workflow

1. Check the command exists:

   ```sh
   microspek --version
   ```

   If it is missing, install it from the project root:

   ```sh
   python install.py --mode system --yes
   ```

   Open a **new terminal** afterwards so the user PATH entry is picked up.

2. Pick the smallest useful command:

   | Need | Command |
   | --- | --- |
   | Short human answer | `microspek --summary` |
   | Full text for an AI | `microspek --snapshot --redact --file snapshot.txt` |
   | Machine-readable data | `microspek --output json --file snapshot.json` |
   | Visual report | `microspek --output png --file report.png` |
   | Interactive inspection | `microspek --gui` |

3. Add `--redact` whenever the result may be shared, pasted into a chat, or
   committed: it hides serial numbers, MAC addresses, volume serials and user
   names. Use it by default for snapshots.

4. Add `--no-dxdiag` unless DirectX details are explicitly needed — dxdiag can
   take up to 60 seconds. GPU temperature/load/VRAM come from nvidia-smi and do
   **not** require dxdiag.

5. For JSON, read the file and summarise; never invent values. Available keys:
   `generated_at`, `hostname`, `platform`, `sections`, `layouts`, `warnings`.
   Each section has `key`, `title`, `summary`, `groups`; each item has
   `label`, `value`, `note`, `sensitive`. See `references/cli.md`.

6. Treat `"—"` as "not available on this system", not as a zero. Common
   unavailable fields: CPU temperature, disk SMART counters, TPM, fan speeds.

7. If `warnings` is non-empty, mention it and keep going — a failed collector
   does not invalidate the rest of the report.

## Rules

- Never output a raw snapshot with serial numbers unless the user explicitly
  asks for the unredacted version.
- Do not claim temperatures, fan speeds or wear values that are not in the
  output; standard WMI often cannot read them on desktop boards.
- For disk layout, "ИТОГО ... размечено" means allocated space. Free space
  inside NTFS is shown per volume as "занято X (Y%)".
- Prefer `--output json --file ...` when you need to filter/compare fields;
  prefer `--snapshot` for a human-readable handoff.

## Supporting files

- `references/cli.md` — full flag list and output schema.
