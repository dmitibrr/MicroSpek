"""CLI entrypoint: ``python -m microspek``."""

from __future__ import annotations

import argparse
import sys
from datetime import datetime
from pathlib import Path

from . import __version__
from .config import ConfigError, Settings, load_config
from .i18n import detect_language, get_language, localize_snapshot, s, set_language
from .render import default_name, render_txt, save_snapshot
from .snapshot import collect_snapshot, normalize_sections


def _prescan(argv: list[str]) -> tuple[str | None, str | None]:
    """Read --lang/--config before argparse so help is already localized."""
    lang: str | None = None
    config: str | None = None
    for index, value in enumerate(argv):
        for flag, target in (("--lang", "lang"), ("--config", "config")):
            if value.startswith(flag + "="):
                if target == "lang":
                    lang = value.split("=", 1)[1]
                else:
                    config = value.split("=", 1)[1]
            elif value == flag and index + 1 < len(argv):
                if target == "lang":
                    lang = argv[index + 1]
                else:
                    config = argv[index + 1]
    return lang, config


def build_parser(formats: str = "txt, json, md") -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="microspek",
        description=s("cli_description"),
    )
    parser.add_argument("--version", action="version", version=f"microspek {__version__}")
    parser.add_argument("--gui", action="store_true", help=s("help_gui"))
    parser.add_argument("--summary", action="store_true", help=s("help_summary"))
    parser.add_argument("--snapshot", action="store_true", help=s("help_snapshot"))
    parser.add_argument("--output", choices=("txt", "json", "md"), help=s("help_output", formats=formats))
    parser.add_argument("--file", type=Path, help=s("help_file"))
    parser.add_argument("--redact", action="store_true", default=None, help=s("help_redact"))
    parser.add_argument("--no-dxdiag", action="store_true", default=None, help=s("help_no_dxdiag"))
    parser.add_argument("--dxdiag-timeout", type=float, default=None, help=s("help_dxdiag_timeout"))
    parser.add_argument("--admin-sensors", action="store_true", default=None, help=s("help_admin_sensors"))
    parser.add_argument("--sections", help=s("help_sections"))
    parser.add_argument("--no-sensors", action="store_true", default=None, help=s("help_no_sensors"))
    parser.add_argument("--lang", choices=("ru", "en"), help=s("help_lang"))
    parser.add_argument("--config", help=s("help_config"))
    return parser


def _apply(settings: Settings, args: argparse.Namespace) -> Settings:
    if args.redact is not None:
        settings.redact = args.redact
    if args.no_dxdiag is not None:
        settings.dxdiag = not args.no_dxdiag
    if args.admin_sensors is not None:
        settings.admin_sensors = args.admin_sensors
    if args.sections is not None:
        settings.sections = normalize_sections(args.sections)
    if args.no_sensors is not None:
        settings.sensors = not args.no_sensors
    if args.lang:
        settings.lang = args.lang
    if args.output:
        settings.output = args.output
    if args.file:
        settings.file = str(args.file)
    return settings


def _print_summary(snapshot, redacted: bool) -> None:
    from .models import redact_snapshot

    snap = redact_snapshot(snapshot) if redacted else snapshot
    snap = localize_snapshot(snap)
    print(s("summary_title"))
    print(f"{s('host')}: {snap.hostname}")
    print(f"{s('created')}: {snap.generated_at.strftime('%d.%m.%Y %H:%M:%S')}")
    for section in snap.sections:
        print(f"\n[{section.title}]")
        for item in section.summary:
            print(f"  {item.label}: {item.value}")
    if snap.warnings:
        print(f"\n{s('warnings')}:")
        for warning in snap.warnings:
            print(f"  - {warning}")


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")

    pre_lang, pre_config = _prescan(argv)
    set_language(pre_lang or detect_language())
    args = build_parser().parse_args(argv)

    try:
        settings = load_config(pre_config or args.config, Settings(dxdiag=True))
    except ConfigError as exc:
        print(s("config_error", path=args.config or "microspek.json", error=exc), file=sys.stderr)
        return 2
    settings = _apply(settings, args)

    # --file without --output always means "save a text snapshot".
    if settings.file and not args.output:
        settings.output = "txt"

    has_action = args.summary or args.snapshot or args.output or args.gui
    if settings.lang:
        set_language(settings.lang)
    if not has_action:
        # CLI and snapshot builds exclude Tkinter; there a bare launch must
        # print help instead of crashing on the missing GUI module.
        try:
            from .gui import run_gui
        except Exception:
            build_parser().print_help()
            return 0

        run_gui()
        return 0

    if settings.sections == []:
        print(s("no_sections"), file=sys.stderr)
        return 2

    snapshot = collect_snapshot(
        include_dxdiag=settings.dxdiag,
        dxdiag_timeout=args.dxdiag_timeout or 60.0,
        elevate_sensors=settings.admin_sensors,
        sections=settings.sections,
        sensors=settings.sensors,
    )

    if args.summary:
        _print_summary(snapshot, settings.redact)
    if args.snapshot:
        print(render_txt(snapshot, settings.redact, get_language()))
    if args.output:
        if settings.file:
            target = Path(settings.file)
            if not target.is_absolute():
                target = Path.cwd() / target
        else:
            target = Path(default_name(settings.output, datetime.now()))
        save_snapshot(snapshot, target, settings.output, settings.redact, get_language())
        print(s("saved", path=target))

    if args.gui:
        try:
            from .gui import run_gui
        except Exception:
            print(s("gui_missing"), file=sys.stderr)
            return 2
        run_gui(snapshot)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
