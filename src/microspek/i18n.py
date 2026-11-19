"""Bilingual RU/EN layer.

Snapshots are always collected with Russian labels, values and notes: that keeps
the collectors fast, independent from the UI language and easy to test.  The
text is translated only when it is shown or written to a report, so switching
the language in the GUI does not require collecting the data again.

Public API::

    set_language("en") / get_language() / detect_language()
    s("refresh")                  # UI string by key
    t("Процессор")                # data string, label or value
    localize_snapshot(snapshot)   # copy with translated titles/labels/values
"""

from __future__ import annotations

import locale
import os
import re
from typing import Iterable

from .models import DiskLayout, Group, Item, PartitionSegment, Section, Snapshot

LANGUAGES = ("ru", "en")
_LANGUAGE = "ru"

_SECTION_EN = {
    "Операционная система": "Operating system",
    "Материнская плата": "Motherboard",
    "Процессор": "Processor",
    "Оперативная память": "Memory",
    "Диски": "Storage",
    "Видеокарта": "Graphics",
    "Сеть": "Network",
    "Устройства": "Devices",
    "DirectX (dxdiag)": "DirectX (dxdiag)",
}

# Words and phrases translated inside labels, values, notes and warnings.
_EN = {
    # --- sections / groups -------------------------------------------------
    "Операционная система": "Operating system",
    "Материнская плата": "Motherboard",
    "Оперативная память": "Memory",
    "Процессор": "Processor",
    "Видеокарта": "GPU",
    "Устройства": "Devices",
    "Материнская плата": "Motherboard",
    "Основное": "General",
    "Кэш": "Cache",
    "Загрузка по ядрам": "Load per core",
    "Датчики (LibreHardwareMonitor)": "Sensors (LibreHardwareMonitor)",
    "Датчики платы (Super I/O)": "Board sensors (Super I/O)",
    "Объём": "Capacity",
    "Виртуальная память": "Virtual memory",
    "Физические диски": "Physical disks",
    "Логические диски": "Logical drives",
    "Разделы": "Partitions",
    "Мониторы (EDID)": "Monitors (EDID)",
    "Контроллер накопителей": "Storage controller",
    "Звук": "Sound",
    "Bluetooth": "Bluetooth",
    "Проблемы PnP": "PnP problems",
    "Питание": "Power",
    "Корпус / система": "Chassis / system",
    "BIOS": "BIOS",
    "Загрузка и безопасность": "Boot and security",
    "Статус": "Status",
    "Система (по dxdiag)": "System (dxdiag)",
    "Сводка": "Summary",
    "Разметка дисков": "Disk layout",
    "Предупреждения": "Warnings",

    # --- report header -----------------------------------------------------
    "MicroSpek — слепок системы": "MicroSpek — system snapshot",
    "Создан": "Generated",
    "Хост": "Host",
    "Платформа": "Platform",
    "Чувствительные данные скрыты": "Sensitive data hidden",
    "ИТОГО": "TOTAL",
    "размечено": "allocated",
    "занято": "used",

    # --- summary / item labels --------------------------------------------
    "Ядра / потоки": "Cores / threads",
    "Частота": "Clock",
    "Загрузка сейчас": "Current load",
    "Температура": "Temperature",
    "Модель": "Model",
    "Производитель": "Vendor",
    "Идентификатор": "Identifier",
    "Физических ядер": "Physical cores",
    "Логических потоков": "Logical threads",
    "Базовая частота": "Base clock",
    "Текущая частота": "Current clock",
    "Сокет": "Socket",
    "Архитектура": "Architecture",
    "Разрядность": "Width",
    "Напряжение": "Voltage",
    "Аппаратная виртуализация": "Hardware virtualization",
    "Температура (термозона ACPI)": "Temperature (ACPI thermal zone)",
    "Кэш L2": "L2 cache",
    "Кэш L3": "L3 cache",
    "Память всего": "Total memory",
    "Занято / свободно": "Used / free",
    "Модули": "Modules",
    "Установлено": "Installed",
    "Доступно ОС": "Available to OS",
    "Свободно": "Free",
    "Слотов всего": "Total slots",
    "Занято слотов": "Slots used",
    "Всего": "Total",
    "Используется сейчас": "Used now",
    "Пик использования": "Peak usage",
    "Размер": "Size",
    "Слот": "Slot",
    "Part Number": "Part number",
    "Серийный номер": "Serial number",
    "Тип": "Type",
    "Частота ( SPD / работает )": "Speed ( SPD / running )",
    "Профиль памяти": "Memory profile",
    "Форм-фактор": "Form factor",
    "Рангов": "Ranks",
    "Версия": "Version",
    "Дата": "Date",
    "Спецификация": "Specification",
    "Тип корпуса": "Chassis type",
    "Серийный номер корпуса": "Chassis serial number",
    "Производитель системы": "System vendor",
    "Модель системы": "System model",
    "Тип системы": "System type",
    "Пользователь": "User",
    "Рабочая группа / домен": "Workgroup / domain",
    "Название": "Name",
    "Установлена": "Installed",
    "Последняя перезагрузка": "Last boot",
    "Время работы": "Uptime",
    "Часовой пояс": "Time zone",
    "Системная папка": "System folder",
    "Локаль": "Locale",
    "Зарегистрированный пользователь": "Registered user",
    "Организация": "Organization",
    "Режим прошивки": "Firmware mode",
    "Secure Boot": "Secure Boot",
    "TPM": "TPM",
    "Сборка": "Build",
    "Имя компьютера": "Computer name",
    "Загрузка": "Boot",
    "Активные адаптеры": "Active adapters",
    "Всего адаптеров": "Total adapters",
    "Описание": "Description",
    "Состояние": "Status",
    "Скорость": "Speed",
    "MAC-адрес": "MAC address",
    "IPv4": "IPv4",
    "IPv6": "IPv6",
    "Маска подсети": "Subnet mask",
    "Шлюз": "Gateway",
    "DNS": "DNS",
    "DHCP": "DHCP",
    "Звуковые устройства": "Audio devices",
    "Bluetooth-адаптер": "Bluetooth adapter",
    "Проблемные устройства": "Problem devices",
    "Режим SATA": "SATA mode",
    "Драйвер": "Driver",
    "Активные драйверы": "Active drivers",
    "Режим": "Mode",
    "Результат": "Result",
    "Видеопроцессор": "GPU",
    "Версия драйвера": "Driver version",
    "Дата драйвера": "Driver date",
    "Видеопамять (WMI)": "Video memory (WMI)",
    "Текущее разрешение": "Current resolution",
    "Температура GPU": "GPU temperature",
    "Загрузка GPU": "GPU load",
    "Память занято": "Memory used",
    "Частота SM": "SM clock",
    "Потребление": "Power draw",
    "Вентилятор": "Fan",
    "Горячая точка GPU": "GPU hot spot",
    "Температура памяти GPU": "GPU memory temperature",
    "Вентилятор GPU (об/мин)": "GPU fan (RPM)",
    "Напряжение ядра GPU": "GPU core voltage",
    "Частота GPU": "GPU clock",
    "Монитор": "Monitor",
    "Видеокарта (dxdiag)": "GPU (dxdiag)",
    "DirectX": "DirectX",
    "Типы": "Types",
    "Логические диски": "Logical drives",
    "Физические диски": "Physical disks",
    "Аккумулятор": "Battery",
    "Процессор": "Processor",

    # --- suffixes of generated "{title} — ..." labels -----------------------
    "— модель": "— model",
    "— объём": "— capacity",
    "— тип": "— type",
    "— шина / интерфейс": "— bus / interface",
    "— интерфейс (WMI)": "— interface (WMI)",
    "— прошивка": "— firmware",
    "— серийный номер тома": "— volume serial",
    "— серийный номер": "— serial number",
    "— состояние": "— health",
    "— температура": "— temperature",
    "— наработка": "— power-on time",
    "— износ": "— wear",
    "— остаток ресурса": "— life remaining",
    "— файловая система": "— file system",
    "— свободно": "— free",
    "— занято": "— used",
    "— производитель (EDID)": "— vendor (EDID)",
    "— производитель": "— vendor",
    "— ID изделия": "— product ID",
    "— подключение": "— connection",
    "— выпущен": "— manufactured",
    "— драйвер": "— driver",

    # --- dxdiag labels -----------------------------------------------------
    "Чип / GPU": "Chip / GPU",
    "DAC": "DAC",
    "Тип устройства": "Device type",
    "Ключ устройства": "Device key",
    "Память (всего)": "Memory (total)",
    "Выделенная память": "Dedicated memory",
    "Общая память": "Shared memory",
    "Текущий режим": "Current mode",
    "Родной режим": "Native mode",
    "Модель монитора": "Monitor model",
    "ID монитора": "Monitor ID",
    "Тип выхода": "Output type",
    "Дата / размер драйвера": "Driver date / size",
    "Модель драйвера": "Driver model",
    "Уровни функций": "Feature levels",
    "Версия DDI": "DDI version",
    "ID устройства": "Device ID",
    "Воспроизведение по умолчанию": "Default playback",
    "Голос по умолчанию": "Default voice",
    "Память": "Memory",
    "Версия DirectX": "DirectX version",
    "Файл подкачки": "Page file",

    # --- LibreHardwareMonitor names ---------------------------------------
    "Пакет CPU": "CPU package",
    "Ядра CPU": "CPU cores",
    "Максимум по ядрам": "Core max",
    "Ядро CPU": "CPU core",
    "Всего CPU": "CPU total",
    "Напряжение ядра CPU": "CPU core voltage",
    "Ядро GPU": "GPU core",
    "Память GPU": "GPU memory",
    "Память GPU (junction)": "GPU memory junction",
    "Вентилятор GPU": "GPU fan",
    "Пакет GPU": "GPU package",
    "Плата GPU": "GPU board",
    "Мощность GPU": "GPU power",
    "Память GPU всего": "GPU memory total",
    "Память GPU занято": "GPU memory used",
    "Память GPU свободно": "GPU memory free",
    "Остаток ресурса": "Life remaining",
    "Записано всего": "Total host writes",
    "Прочитано всего": "Total host reads",
    "Наработка": "Power-on time",
    "Циклов включения": "Power cycles",
    "Занято": "Used",
    "Ресурс": "Life",

    # --- values ------------------------------------------------------------
    "не удалось определить": "unknown",
    "скрыто": "hidden",
    "Майкрософт": "Microsoft",
    "Новый том": "New volume",
    "не найден / недоступен": "not found / unavailable",
    "не активирован": "not activated",
    "неисправен": "failed",
    "исправен": "healthy",
    "предупреждение": "warning",
    "неизвестно": "unknown",
    "не указан": "unspecified",
    "включён": "enabled",
    "выключен": "disabled",
    "активен": "active",
    "Съёмный": "Removable",
    "Локальный": "Local",
    "Сетевой": "Network",
    "RAM-диск": "RAM disk",
    "Неизвестно": "Unknown",
    "Нет корня": "No root",
    "нет корня": "no root",
    "не размечено": "unallocated",
    "данные": "data",
    "восстановление": "recovery",
    "служебный": "service",
    "XMP / разгон активен": "XMP / overclock active",
    "JEDEC (без разгона)": "JEDEC (no overclock)",
    "адаптер не найден": "adapter not found",
    "ошибок не обнаружено": "no errors found",
    "не удалось получить отчёт dxdiag": "could not obtain the dxdiag report",
    "ошибка запуска": "launch failed",
    "не удалось запустить сбор датчиков": "could not start sensor collection",
    "helper не найден": "helper not found",
    "Датчики недоступны": "Sensors unavailable",
    "Датчики собираются…": "Collecting sensors…",
    "Датчики отключены": "Sensors disabled",
    "Датчики: без температур": "Sensors: no temperatures",
    " (нужен запуск от администратора)": " (run as administrator)",
    ", CPU — нужен PawnIO": ", CPU needs PawnIO",
    ", с правами администратора": ", elevated",
    "Запрашиваю права администратора для температур и SMART…":
        "Requesting administrator rights for temperatures and SMART…",
    "заряд": "charge",
    "статус": "status",
    "буквы": "letters",
    "индекс": "index",
    "код": "code",
    "неделя": "week",
    "из": "of",

    # --- chassis types -----------------------------------------------------
    "Другое": "Other",
    "Настольный ПК": "Desktop",
    "Низкопрофильный": "Low profile",
    "Пирамида": "Pizza box",
    "Портативный": "Portable",
    "Ноутбук (Notebook)": "Notebook",
    "Ноутбук": "Laptop",
    "Карманный": "Handheld",
    "All-in-One": "All-in-One",
    "Субноутбук": "Sub-notebook",
    "Компактный": "Compact",
    "Серверный корпус": "Server chassis",
    "Стойка (Rack)": "Rack",

    # --- PnP problem descriptions -----------------------------------------
    "устройство не работает": "device not working",
    "не удаётся запустить": "cannot start",
    "недостаточно ресурсов": "not enough resources",
    "требуется перезагрузка": "restart required",
    "конфликт ресурсов": "resource conflict",
    "несовместимое оборудование": "incompatible hardware",
    "устройство отключено": "device disabled",
    "отключено пользователем": "disabled by the user",
    "нет драйвера": "driver missing",
    "драйвер не загружен": "driver not loaded",
    "драйвер повреждён": "driver corrupted",
    "сбой устройства (Code 43)": "device failure (Code 43)",
    "подпись драйвера не подтверждена": "driver signature not confirmed",
}

# Regex rules for generated labels and formatted values.  They run before the
# phrase substitution below, so they can rely on the original Russian text.
_RULES: list[tuple[re.Pattern[str], str]] = [
    # decimal comma -> dot (units are translated separately)
    (re.compile(r"(?<=\d),(?=\d)"), "."),
    # units
    (re.compile(r"\bГиБ\b"), "GiB"),
    (re.compile(r"\bТиБ\b"), "TiB"),
    (re.compile(r"\bМиБ\b"), "MiB"),
    (re.compile(r"\bКиБ\b"), "KiB"),
    (re.compile(r"\bПиБ\b"), "PiB"),
    (re.compile(r"\bМБ\b"), "MB"),
    (re.compile(r"\bГБ\b"), "GB"),
    (re.compile(r"\bКБ\b"), "KB"),
    (re.compile(r"\bГГц\b"), "GHz"),
    (re.compile(r"\bМГц\b"), "MHz"),
    (re.compile(r"\bГц\b"), "Hz"),
    (re.compile(r"МТ/с"), "MT/s"),
    (re.compile(r"об/мин"), "RPM"),
    (re.compile(r"(\d)\s*Вт\b"), r"\1 W"),
    (re.compile(r"(\d)\s*В\b"), r"\1 V"),
    (re.compile(r"(\d+)\s*мин\b"), r"\1 min"),
    (re.compile(r"(\d+)\s*д\b"), r"\1 d"),
    (re.compile(r"(\d+)\s*ч\b"), r"\1 h"),
    (re.compile(r"^(\d+)\s*шт\.,\s*(.+)$"), r"\1 drives, \2"),
    (re.compile(r"^(\d+)\s*бит$"), r"\1-bit"),
    (re.compile(r"^(\d+)-разрядная$"), r"\1-bit"),
    (re.compile(r"^(\d+)\s*г\.,\s*неделя\s+(\d+)$"), r"\1, week \2"),
    (re.compile(r"^заряд\s+(.+),\s*статус\s+(.+)$"), r"charge \1, status \2"),
    (re.compile(r"^есть,\s*версия\s+(.+)$"), r"present, version \1"),
    (re.compile(r"^есть$"), "present"),
    (re.compile(r"^да$"), "yes"),
    (re.compile(r"^нет$"), "no"),
    (re.compile(r"^да,\s*"), "yes, "),
    (re.compile(r"^нет,\s*"), "no, "),
    # generated titles
    (re.compile(r"^Диск (\d+|\?):\s*(.*)$"), r"Disk \1: \2"),
    (re.compile(r"^Диск (\d+) / раздел (\d+)$"), r"Disk \1 / partition \2"),
    (re.compile(r"^Диск (\d+) — (.*?) \((.*)\)$"), r"Disk \1 — \2 (\3)"),
    (re.compile(r"^Модуль (\d+) — (.*)$"), r"Module \1 — \2"),
    (re.compile(r"^Файл подкачки (.*)$"), r"Page file \1"),
    (re.compile(r"^Монитор (\d+) — (.*)$"), r"Monitor \1 — \2"),
    (re.compile(r"^Контроллер (\d+)$"), r"Controller \1"),
    (re.compile(r"^Дисплей (\d+) — (.*)$"), r"Display \1 — \2"),
    (re.compile(r"^Звук (\d+) — (.*)$"), r"Sound \1 — \2"),
    (re.compile(r"^Аккумулятор (\d+):\s*(.*)$"), r"Battery \1: \2"),
    (re.compile(r"^Устройство (\d+)$"), r"Device \1"),
    (re.compile(r"^Драйвер (\d+)$"), r"Driver \1"),
    (re.compile(r"^Адаптер (\d+) — (.*)$"), r"Adapter \1 — \2"),
    (re.compile(r"^Адаптер (\d+)$"), r"Adapter \1"),
    (re.compile(r"^Ядро (\d+)$"), r"Core \1"),
    (re.compile(r"^Вентилятор (\d+)$"), r"Fan \1"),
    # value phrases that only make sense as a whole value
    (re.compile(r",\s*занято слотов:\s*(\d+) из (\d+)"), r", slots used: \1 of \2"),
    (re.compile(r",\s*модулей:\s*(\d+)"), r", modules: \1"),
    (re.compile(r"\bиз\b"), "of"),
    (re.compile(r"\bбуквы:\s*"), "letters: "),
]

# Phrases that survive as substrings (item labels, statuses, units leftovers).
# Sorted longest first at import time so "Модель системы" wins over "Модель".
_PHRASES: list[tuple[str, str]] = sorted(_EN.items(), key=lambda item: -len(item[0]))
_PHRASE_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (
        re.compile(
            r"(?<![\wА-Яа-яЁё])" + re.escape(ru) + r"(?![\wА-Яа-яЁё])",
            re.IGNORECASE,
        ),
        en,
    )
    for ru, en in _PHRASES
]


# --------------------------------------------------------------------------- UI
_UI: dict[str, dict[str, str]] = {
    "ru": {
        "app_title": "MicroSpek — характеристики ПК",
        "app_subtitle": "Характеристики ПК без лишних движений",
        "refresh": "Обновить",
        "refresh_hint": "Собрать данные заново (Ctrl+R)",
        "sensors_admin": "Датчики (админ)",
        "sensors_hint": "Пересобрать с правами администратора: температуры CPU и SMART",
        "export": "Экспорт ▾",
        "export_txt": "Текстовый слепок (.txt)",
        "export_json": "JSON (.json)",
        "export_md": "Markdown (.md)",
        "screenshot": "Скриншот окна",
        "redact": "Скрывать чувствительное",
        "dxdiag": "dxdiag (медленно)",
        "language": "Язык",
        "summary_tab": "Сводка",
        "col_section": "Раздел",
        "col_group": "Группа",
        "col_parameter": "Параметр",
        "col_value": "Значение",
        "col_note": "Примечание",
        "md_segment": "Сегмент",
        "md_size": "Размер",
        "md_used": "Занято",
        "md_kind": "Тип",
        "group_summary": "Сводка",
        "status_ready": "Готово к сбору",
        "status_collecting": "Сбор данных…",
        "status_collected": "Обновлено {time} · разделов: {count}{extra} · {sensors}",
        "status_loaded": "Загружен слепок от {time}",
        "status_warnings": ", предупреждений: {count}",
        "status_saved": "Сохранено: {path}",
        "status_error": "Ошибка сбора: {error}",
        "status_screenshot": "Скриншот сохранён: {path}",
        "save_title": "Сохранить отчёт",
        "save_as_title": "Сохранить скриншот окна",
        "file_txt": "Текстовый слепок (*.txt)",
        "file_json": "JSON (*.json)",
        "file_md": "Markdown (*.md)",
        "file_png": "PNG (*.png)",
        "file_all": "Все файлы",
        "wait_collect": "Сначала дождитесь окончания сбора данных.",
        "no_data": "Нет данных для экспорта.",
        "save_failed": "Не удалось сохранить:\n{error}",
        "screenshot_failed": "Не удалось сделать скриншот:\n{error}",
        "error_title": "MicroSpek",
        "start_error_title": "MicroSpek — ошибка запуска",
        "start_error_body": "Подробности записаны в файл:\n{path}",
        "cli_description": "Сбор характеристик ПК: GUI, CLI, TXT/JSON/Markdown и скриншот.",
        "help_gui": "открыть графический интерфейс",
        "help_summary": "напечатать короткую сводку",
        "help_snapshot": "напечатать полный TXT-слепок",
        "help_output": "сохранить отчёт в файл ({formats})",
        "help_file": "путь к файлу (по умолчанию имя с датой)",
        "help_redact": "скрыть чувствительные поля",
        "help_no_dxdiag": "не запускать dxdiag (быстрее)",
        "help_dxdiag_timeout": "таймаут dxdiag в секундах",
        "help_admin_sensors": "запросить права администратора для температур CPU и SMART дисков",
        "help_lang": "язык интерфейса и отчёта: ru или en",
        "help_sections": "какие разделы собирать (ключи через запятую: os, motherboard, cpu, memory, storage, gpu, network, devices, dxdiag)",
        "help_no_sensors": "не запускать сборщик датчиков (быстрее, без температур и SMART)",
        "help_config": "прочитать настройки из JSON-файла (microspek.json)",
        "summary_title": "MicroSpek — сводка",
        "host": "Хост",
        "created": "Создан",
        "warnings": "Предупреждения",
        "saved": "Сохранено: {path}",
        "snapshot_saved": "Готово: {path}",
        "config_error": "Не удалось прочитать конфигурацию {path}: {error}",
        "unknown_section": "Неизвестный раздел: {name}",
        "no_sections": "Не выбрано ни одного раздела.",
        "started": "Собираю данные…",
        "sensors_note": "Датчики: {note}",
        "opening": "Открываю {path}",
        "gui_missing": "Графический интерфейс не входит в это издание. Используйте издание full или gui.",
    },
    "en": {
        "app_title": "MicroSpek — PC specifications",
        "app_subtitle": "PC specs without the usual fuss",
        "refresh": "Refresh",
        "refresh_hint": "Collect the data again (Ctrl+R)",
        "sensors_admin": "Sensors (admin)",
        "sensors_hint": "Re-collect as administrator: CPU temperatures and SMART",
        "export": "Export ▾",
        "export_txt": "Text snapshot (.txt)",
        "export_json": "JSON (.json)",
        "export_md": "Markdown (.md)",
        "screenshot": "Window screenshot",
        "redact": "Hide sensitive data",
        "dxdiag": "dxdiag (slow)",
        "language": "Language",
        "summary_tab": "Summary",
        "col_section": "Section",
        "col_group": "Group",
        "col_parameter": "Parameter",
        "col_value": "Value",
        "col_note": "Note",
        "md_segment": "Segment",
        "md_size": "Size",
        "md_used": "Used",
        "md_kind": "Kind",
        "group_summary": "Summary",
        "status_ready": "Ready to collect",
        "status_collecting": "Collecting data…",
        "status_collected": "Updated {time} · sections: {count}{extra} · {sensors}",
        "status_loaded": "Snapshot loaded at {time}",
        "status_warnings": ", warnings: {count}",
        "status_saved": "Saved: {path}",
        "status_error": "Collection failed: {error}",
        "status_screenshot": "Screenshot saved: {path}",
        "save_title": "Save report",
        "save_as_title": "Save window screenshot",
        "file_txt": "Text snapshot (*.txt)",
        "file_json": "JSON (*.json)",
        "file_md": "Markdown (*.md)",
        "file_png": "PNG (*.png)",
        "file_all": "All files",
        "wait_collect": "Wait until the collection finishes.",
        "no_data": "There is no data to export yet.",
        "save_failed": "Could not save:\n{error}",
        "screenshot_failed": "Could not take the screenshot:\n{error}",
        "error_title": "MicroSpek",
        "start_error_title": "MicroSpek — startup error",
        "start_error_body": "Details were written to:\n{path}",
        "cli_description": "PC hardware snapshot: GUI, CLI, TXT/JSON/Markdown and screenshots.",
        "help_gui": "open the graphical interface",
        "help_summary": "print a short summary",
        "help_snapshot": "print the full TXT snapshot",
        "help_output": "save the report to a file ({formats})",
        "help_file": "target file (a dated name is used by default)",
        "help_redact": "hide sensitive fields",
        "help_no_dxdiag": "do not run dxdiag (faster)",
        "help_dxdiag_timeout": "dxdiag timeout in seconds",
        "help_admin_sensors": "ask for administrator rights for CPU temperatures and disk SMART",
        "help_lang": "interface and report language: ru or en",
        "help_sections": "sections to collect (comma-separated keys: os, motherboard, cpu, memory, storage, gpu, network, devices, dxdiag)",
        "help_no_sensors": "skip the sensor helper (faster, no temperatures or SMART)",
        "help_config": "read settings from a JSON file (microspek.json)",
        "summary_title": "MicroSpek — summary",
        "host": "Host",
        "created": "Generated",
        "warnings": "Warnings",
        "saved": "Saved: {path}",
        "snapshot_saved": "Done: {path}",
        "config_error": "Could not read the configuration {path}: {error}",
        "unknown_section": "Unknown section: {name}",
        "no_sections": "No sections selected.",
        "started": "Collecting data…",
        "sensors_note": "Sensors: {note}",
        "opening": "Opening {path}",
        "gui_missing": "This edition does not include the GUI. Use the full or gui edition.",
    },
}


def detect_language() -> str:
    """Best-effort language from MICROSPEK_LANG or the system locale."""
    override = os.environ.get("MICROSPEK_LANG", "").strip().lower()
    if override in LANGUAGES:
        return override
    try:
        name = (locale.getlocale()[0] or "").lower()
    except (TypeError, ValueError):
        name = ""
    if not name:
        name = os.environ.get("LANG", "").lower()
    if name.startswith("ru") or "russian" in name:
        return "ru"
    return "en"


def set_language(lang: str | None) -> str:
    """Set the active language, ignoring unknown values."""
    global _LANGUAGE
    value = (lang or "").strip().lower()
    if value in LANGUAGES:
        _LANGUAGE = value
    return _LANGUAGE


def get_language() -> str:
    return _LANGUAGE


def s(key: str, **kwargs: object) -> str:
    """Return a UI string and apply ``str.format`` placeholders."""
    table = _UI.get(_LANGUAGE, _UI["ru"])
    text = table.get(key) or _UI["ru"].get(key) or key
    if kwargs:
        try:
            return text.format(**kwargs)
        except (KeyError, IndexError):
            return text
    return text


def section_title(title: str) -> str:
    """Translate a section title (context differs from item labels)."""
    if _LANGUAGE == "ru":
        return title
    return _SECTION_EN.get(title, _translate_en(title))


def t(text: object) -> str:
    """Translate a label/value/note.  Russian is returned unchanged."""
    value = "" if text is None else str(text)
    if _LANGUAGE == "ru" or not value:
        return value
    return _translate_en(value)


def _translate_en(text: str) -> str:
    if not text:
        return text
    # Fast path: the whole string is a known phrase.
    exact = _EN.get(text)
    if exact is not None:
        return exact
    for pattern, replacement in _RULES:
        text = pattern.sub(replacement, text)
    for pattern, replacement in _PHRASE_PATTERNS:
        text = pattern.sub(replacement, text)
    return text


def _localize_items(items: Iterable[Item]) -> list[Item]:
    return [
        Item(t(item.label), t(item.value), t(item.note), item.sensitive)
        for item in items
    ]


def _localize_layout(layout: DiskLayout) -> DiskLayout:
    return DiskLayout(
        title=t(layout.title),
        total_size=layout.total_size,
        segments=[
            PartitionSegment(
                label=t(segment.label),
                size=segment.size,
                kind=segment.kind,
                used=segment.used,
            )
            for segment in layout.segments
        ],
    )


def localize_snapshot(snapshot: Snapshot, lang: str | None = None) -> Snapshot:
    """Return a translated copy of ``snapshot`` without touching the original."""
    if lang is not None:
        set_language(lang)
    if _LANGUAGE == "ru":
        return snapshot
    sections = [
        Section(
            key=section.key,
            title=section_title(section.title),
            groups=[
                Group(t(group.title), _localize_items(group.items))
                for group in section.groups
            ],
            summary=_localize_items(section.summary),
        )
        for section in snapshot.sections
    ]
    return Snapshot(
        generated_at=snapshot.generated_at,
        hostname=snapshot.hostname,
        platform=snapshot.platform,
        sections=sections,
        warnings=[t(warning) for warning in snapshot.warnings],
        layouts=[_localize_layout(layout) for layout in snapshot.layouts],
    )
