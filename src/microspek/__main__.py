"""CLI entrypoint: ``python -m microspek``."""

from __future__ import annotations

import argparse
import sys
from datetime import datetime
from pathlib import Path

from . import __version__
from .render import render_txt, save_snapshot
from .snapshot import collect_snapshot


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="microspek",
        description="Сбор характеристик ПК: GUI, CLI, TXT/JSON/PNG и скриншот.",
    )
    parser.add_argument("--version", action="version", version=f"microspek {__version__}")
    parser.add_argument("--gui", action="store_true", help="открыть графический интерфейс")
    parser.add_argument("--summary", action="store_true", help="печать короткой сводки")
    parser.add_argument("--snapshot", action="store_true", help="печать полного TXT-слепка")
    parser.add_argument("--output", choices=("txt", "json", "png"), help="сохранить отчёт в файл")
    parser.add_argument("--file", type=Path, help="путь к файлу (по умолчанию имя с датой)")
    parser.add_argument("--redact", action="store_true", help="скрыть чувствительные поля")
    parser.add_argument("--no-dxdiag", action="store_true", help="не запускать dxdiag (быстрее)")
    parser.add_argument("--dxdiag-timeout", type=float, default=60.0, help="таймаут dxdiag в секундах")
    return parser


def _print_summary(snapshot, redacted: bool) -> None:
    if redacted:
        from .models import redact_snapshot

        snapshot = redact_snapshot(snapshot)
    print("MicroSpek — сводка")
    print(f"Хост: {snapshot.hostname}")
    print(f"Создан: {snapshot.generated_at.strftime('%d.%m.%Y %H:%M:%S')}")
    for section in snapshot.sections:
        print(f"\n[{section.title}]")
        for item in section.summary:
            print(f"  {item.label}: {item.value}")
    if snapshot.warnings:
        print("\nПредупреждения:")
        for warning in snapshot.warnings:
            print(f"  - {warning}")


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    args = build_parser().parse_args(argv)
    # --file без --output всегда означает «сохранить текстовый слепок».
    if args.file and not args.output:
        args.output = "txt"
    has_action = args.summary or args.snapshot or args.output or args.gui
    if not has_action:
        from .gui import run_gui

        run_gui()
        return 0

    snapshot = collect_snapshot(
        include_dxdiag=not args.no_dxdiag,
        dxdiag_timeout=args.dxdiag_timeout,
    )

    if args.summary:
        _print_summary(snapshot, args.redact)
    if args.snapshot:
        print(render_txt(snapshot, args.redact))
    if args.output:
        if args.file:
            target = args.file
        else:
            stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            target = Path(f"microspek_{stamp}.{args.output}")
        save_snapshot(snapshot, target, args.output, args.redact)
        print(f"Сохранено: {target}")

    if args.gui:
        from .gui import run_gui

        run_gui(snapshot)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
