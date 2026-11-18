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
папкой `sensors` (сборщик температур/SMART), `SNAPSHOT.cmd` и инструкцией.
Python друзьям не нужен.

Сборщик датчиков компилируется из `tools/sensors/MicroSpekSensors.cs`
компилятором .NET Framework, который уже есть в Windows. Если его нужно
пересобрать отдельно:

```powershell
python scripts/fetch_sensors_vendor.py   # один раз, тянет LibreHardwareMonitorLib + зависимости
python scripts/build_sensors.py
```

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
- **Датчики (админ)** — пересобрать с правами администратора: температуры CPU,
  обороты вентиляторов и SMART-данные дисков (один запрос UAC).
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

Отдельно собираются аппаратные датчики через LibreHardwareMonitorLib:
температура GPU, hot spot, обороты и мощность, температуры и SMART-ресурс
дисков, температуры CPU и датчики Super I/O (когда доступны).

Коллекторы работают параллельно: на машине разработки полный слепок занимает
около 4–5 секунд вместо 14 (запуск PowerShell на каждую секцию больше не
складывается последовательно).

## Датчики и права администратора

`MicroSpekSensors.exe` запускается без прав и сразу отдаёт то, что доступно
обычному пользователю (датчики GPU через NVAPI, часть данных LHM).
SMART-данные дисков и температуры CPU требуют администратора: `--admin-sensors`
(и `SNAPSHOT.cmd`) запрашивает UAC один раз, при отказе программа продолжает
без этих полей. В GUI для этого есть кнопка «Датчики (админ)».

Температуры CPU и обороты вентиляторов на многих платах требуют драйвера
**PawnIO** (LHM 0.9.6 использует его вместо WinRing0). Без PawnIO SMART дисков,
GPU-датчики и остальная информация всё равно собираются; поля CPU/вентиляторов
остаются «—».

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
                     os_info, devices, dxdiag, sensors
tools/sensors/       MicroSpekSensors.cs — C#-helper для LibreHardwareMonitorLib
scripts/             сборка exe, датчиков, релиза
run_microspek.py     запуск из корня проекта
```

## Требования

Python 3.10+, Windows. Зависимости из стандартной библиотеки; для PNG
и скриншотов используется Pillow (`pip install pillow`). Сбор данных идёт
через PowerShell (CIM/WMI), поэтому утилита рассчитана на Windows.

Для сборки exe нужен PyInstaller; для сборки `MicroSpekSensors.exe` —
компилятор C# из состава .NET Framework 4.8 (есть в Windows 10/11 по умолчанию)
и пакеты NuGet, которые скачивает `scripts/fetch_sensors_vendor.py`.

## Лицензии сторонних компонентов

`MicroSpekSensors.exe` использует LibreHardwareMonitorLib 0.9.6 и её зависимости
(DiskInfoToolkit, RAMSPDToolkit-NDD, BlackSharp.Core — MPL-2.0; HidSharp —
Apache-2.0; пакеты `System.*` — MIT). Уведомления и полные тексты лицензий
лежат в папке `sensors/` рядом с программой: `THIRD_PARTY.md`,
`LICENSE-MPL-2.0.txt`, `LICENSE-HidSharp.txt`.

## Известные нюансы

- `Get-StorageReliabilityCounter` на многих потребительских дисках не отдаёт
  данные; вместо него SMART-температуры и остаток ресурса читает
  LibreHardwareMonitorLib (нужны права администратора). Температуры CPU и
  обороты вентиляторов дополнительно требуют драйвера PawnIO.
- `AdapterRAM` в WMI часто ограничен 4 ГБ; для точного объёма видеопамяти
  используется nvidia-smi, если он установлен.
- Занятое место показывается только для томов, целиком лежащих на одном
  разделе; для томов из LDM-массива (например, `L:` на двух дисках) число
  скрыто, чтобы не дублировать его.
- В строке «ИТОГО» разметки диска указано **размечённое** место (сумма разделов),
  а не занятое: свободное место внутри NTFS показано отдельно для каждого тома.
- Первоначальная версия `cpu.py` содержала ошибку PowerShell (дублирующийся
  ключ `cores`) и неверные единицы кэша (WMI отдаёт КБ); исправлено.
