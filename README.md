# MicroSpek

Утилита для сбора характеристик ПК: аналог fastfetch + CPU-Z с GUI, CLI,
визуализацией разметки дисков и кнопкой «сделать слепок» в TXT для ИИ.

## Готовый exe (Windows)

Для распространения без Python соберите standalone-сборку:

```powershell
python -m pip install pyinstaller
python scripts/build_exe.py
```

Получится `dist/MicroSpek-<version>-WIN64.zip` с двумя программами:
`MicroSpek-GUI.exe` (оконный интерфейс) и `microspek.exe` (консольная команда),
а также `Слепок.cmd` и инструкция. Python друзьям не нужен.

## Запуск из исходников

Из корня проекта:

```powershell
python run_microspek.py            # открыть GUI (по умолчанию)
python run_microspek.py --summary  # короткая сводка в консоль
python run_microspek.py --snapshot # полный TXT-слепок в консоль
python run_microspek.py --output txt --file report.txt
python run_microspek.py --output json --file report.json
python run_microspek.py --output png --file report.png
python run_microspek.py --redact --output txt --file safe.txt
python run_microspek.py --no-dxdiag --summary   # без медленного dxdiag
python run_microspek.py --gui                    # собрать и сразу открыть GUI
```

Или из папки `src`:

```powershell
python -m microspek --summary
```

## GUI

- **Обновить** (`Ctrl+R`) — повторный сбор данных в фоновом потоке.
- **Слепок TXT** — подробный отчёт, готовый для вставки в ИИ.
- **JSON / PNG-отчёт** — экспорт в соответствующие форматы.
- **Скриншот окна** — снимок текущего окна приложения через Pillow.
- **Скрывать чувствительное** — серийные номера, MAC, пользователь и т.п.
  заменяются на «скрыто» (те же данные помечаются оранжевым в GUI).
- **dxdiag (медленно)** — подключить дополнительный отчёт DirectX
  (по умолчанию выключен, так как занимает до 60 секунд).

Вкладка **Диски** показывает цветные полосы разделов с легендой; цвета:
синий — данные, жёлтый — EFI, фиолетовый — восстановление, серый —
неразмеченное пространство, зелёный — LDM.

## Что собирается

ОС (включая UEFI/Secure Boot/TPM), материнская плата/BIOS, процессор,
память (модули, профиль XMP/JEDEC, файл подкачки), физические диски,
разделы и логические диски с занятым местом, видеокарта (WMI + nvidia-smi),
мониторы (EDID: модель, производитель, тип подключения), сеть,
звуковые и Bluetooth-устройства, проблемные PnP-устройства,
режим SATA-контроллера, опционально DirectX через dxdiag.

## Структура

```
src/microspek/
  __main__.py        CLI
  gui.py             Tkinter GUI
  snapshot.py        сборка слепка из коллекторов
  render.py          экспорт TXT / JSON / PNG
  models.py          модели данных и редокт
  util.py            PowerShell, форматирование, даты
  collectors/        cpu, memory, motherboard, storage, gpu, network,
                     os_info, devices, dxdiag
run_microspek.py     запуск из корня проекта
```

## Требования

Python 3.10+, Windows. Зависимости из стандартной библиотеки; для PNG
и скриншотов используется Pillow (`pip install pillow`). Сбор данных идёт
через PowerShell (CIM/WMI), поэтому утилита рассчитана на Windows.

## Известные нюансы

- `Get-StorageReliabilityCounter` (температура/износ/наработка дисков) на этой
  машине не отдаёт данные вообще — поля остаются «—». Это ограничение системы,
  а не код. Для реальных температур CPU/чипсета/вентиляторов потребуется
  внешняя библиотека (например, LibreHardwareMonitorLib), она не интегрирована.
  Зато доступны температуры и обороты GPU через nvidia-smi.
- `AdapterRAM` в WMI часто ограничен 4 ГБ; для точного объёма видеопамяти
  используется nvidia-smi, если он установлен.
- Занятое место показывается только для томов, целиком лежащих на одном
  разделе; для томов из LDM-массива (например, `L:` на двух дисках) число
  скрыто, чтобы не дублировать его.
- В строке «ИТОГО» разметки диска указано **размечённое** место (сумма разделов),
  а не занятое: свободное место внутри NTFS показано отдельно для каждого тома.
- Первоначальная версия `cpu.py` содержала ошибку PowerShell (дублирующийся
  ключ `cores`) и неверные единицы кэша (WMI отдаёт КБ); исправлено.
