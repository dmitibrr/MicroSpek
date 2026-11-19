"""Console entry point of the lightweight snapshot edition.

It is intentionally small: read ``microspek.json`` (or flags), collect the
selected sections, write the report, optionally open it.  No Tkinter, no
Pillow, no extra output — suitable for embedding into other applications.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from . import __version__
from .config import ConfigError, Settings, config_dir, find_config, load_config
from .i18n import detect_language, s, set_language
from .render import default_name, render, save_snapshot
from .snapshot import collect_snapshot, normalize_sections


def _prescan(argv: list[str]) -> str | None:
    for index, value in enumerate(argv):
        if value == "--lang" and index + 1 < len(argv):
            return argv[index + 1]
        if value.startswith("--lang="):
            return value.split("=", 1)[1]
    return None


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="microspek-snapshot",
        description=s("cli_description"),
    )
    parser.add_argument("--version", action="version", version=f"microspek-snapshot {__version__}")
    parser.add_argument("--config", help=s("help_config"))
    parser.add_argument("--output", choices=("txt", "json", "md"), help=s("help_output", formats="txt, json, md"))
    parser.add_argument("--file", type=Path, help=s("help_file"))
    parser.add_argument("--redact", action="store_true", default=None, help=s("help_redact"))
    parser.add_argument("--sections", help=s("help_sections"))
    parser.add_argument("--no-sensors", action="store_true", default=None, help=s("help_no_sensors"))
    parser.add_argument("--dxdiag", action="store_true", default=None, help="run dxdiag too")
    parser.add_argument("--admin-sensors", action="store_true", default=None, help=s("help_admin_sensors"))
    parser.add_argument("--lang", choices=("ru", "en"), help=s("help_lang"))
    parser.add_argument("--stdout", action="store_true", default=None, help="print the report to stdout")
    parser.add_argument("--open", action="store_true", default=None, help="open the report after saving")
    parser.add_argument("--quiet", action="store_true", default=None, help="no progress output")
    return parser


def _merge(settings: Settings, args: argparse.Namespace) -> Settings:
    if args.output:
        settings.output = args.output
    if args.file:
        settings.file = str(args.file)
    if args.redact is not None:
        settings.redact = args.redact
    if args.sections is not None:
        settings.sections = normalize_sections(args.sections)
    if args.no_sensors is not None:
        settings.sensors = not args.no_sensors
    if args.dxdiag is not None:
        settings.dxdiag = args.dxdiag
    if args.admin_sensors is not None:
        settings.admin_sensors = args.admin_sensors
    if args.lang:
        settings.lang = args.lang
    if args.stdout is not None:
        settings.stdout = args.stdout
    if args.open is not None:
        settings.open_file = args.open
    if args.quiet is not None:
        settings.quiet = args.quiet
    return settings


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")

    pre_lang = _prescan(argv)
    set_language(pre_lang or detect_language())
    args = build_parser().parse_args(argv)

    try:
        settings = load_config(args.config, Settings(dxdiag=False))
    except ConfigError as exc:
        print(s("config_error", path=args.config or "microspek.json", error=exc), file=sys.stderr)
        return 2
    settings = _merge(settings, args)
    if settings.lang:
        set_language(settings.lang)

    if not settings.quiet:
        print(s("started"), file=sys.stderr)

    snapshot = collect_snapshot(
        include_dxdiag=settings.dxdiag,
        elevate_sensors=settings.admin_sensors,
        sections=settings.sections,
        sensors=settings.sensors,
    )

    if settings.stdout:
        print(render(snapshot, settings.output, settings.redact, settings.lang))

    if settings.file:
        base = config_dir(args.config) if find_config(args.config) else Path.cwd()
        target = Path(settings.file)
        if not target.is_absolute():
            target = base / target
    else:
        target = Path.cwd() / default_name(settings.output)

    save_snapshot(snapshot, target, settings.output, settings.redact, settings.lang)
    if not settings.quiet:
        print(s("snapshot_saved", path=target), file=sys.stderr)

    if settings.open_file:
        try:
            os.startfile(str(target))  # type: ignore[attr-defined]
        except OSError:
            pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
