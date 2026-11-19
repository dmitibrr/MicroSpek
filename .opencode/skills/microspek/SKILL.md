---
name: MicroSpek
description: Use when the user asks about PC hardware specifications, diagnostics, system snapshots, or wants a TXT/JSON/Markdown hardware report for an AI agent.
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
- preparing a Notion/Obsidian page or an AI chat attachment from hardware data

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
   | Markdown for a chat/Notion | `microspek --output md --redact --file snapshot.md` |
   | Full text for an AI | `microspek --snapshot --redact --file snapshot.txt` |
   | Machine-readable data | `microspek --output json --file snapshot.json` |
   | Interactive inspection | `microspek --gui` |
   | English output | add `--lang en` |
   | Fast, partial snapshot | add `--sections cpu,memory,storage` and `--no-sensors` |

3. Add `--redact` whenever the result may be shared, pasted into a chat, or
   committed: it hides serial numbers, MAC addresses, volume serials and user
   names. Use it by default for snapshots.

4. Add `--no-dxdiag` unless DirectX details are explicitly needed — dxdiag can
   take up to 60 seconds. GPU temperature/load/VRAM come from nvidia-smi and do
   **not** require dxdiag.

5. For JSON, read the file and summarise; never invent values. The document has
   `schema`, `language`, `generated_at`, `hostname`, `platform`, `sections`,
   `layouts`, `warnings`. Each section has `key`, `title`, `summary`, `groups`;
   each item has `label`, `value`, `note`, `sensitive`. See `references/cli.md`.

6. Treat `"—"` as "not available on this system", not as a zero. Common
   unavailable fields: CPU temperature, disk SMART counters, TPM, fan speeds.

7. If `warnings` is non-empty, mention it and keep going — a failed collector
   does not invalidate the rest of the report.

## Editions

| Edition | Binary | Use |
| --- | --- | --- |
| full | `MicroSpek-GUI.exe` + `microspek.exe` | normal desktop use |
| gui | `MicroSpek.exe` | window only |
| cli | `microspek.exe` | scripts and agents |
| snapshot | `microspek-snapshot.exe` | embedding, `microspek.json` only |

The snapshot edition has no Tkinter/Pillow, accepts the same flags, and reads
defaults from `microspek.json` next to the executable. It is the best choice
when another program needs a report without a GUI.

## Rules

- Never output a raw snapshot with serial numbers unless the user explicitly
  asks for the unredacted version.
- Do not claim temperatures, fan speeds or wear values that are not in the
  output; standard WMI often cannot read them on desktop boards.
- For disk layout, "ИТОГО ... размечено" means allocated space. Free space
  inside NTFS is shown per volume as "занято X (Y%)".
- Prefer `--output json --file ...` when you need to filter/compare fields;
  prefer `--output md` for a human-readable handoff and `--snapshot` for plain
  text.

## Supporting files

- `references/cli.md` — full flag list, config schema and output shape.
