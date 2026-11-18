# Сторонние компоненты

`MicroSpekSensors.exe` и DLL рядом с ним — отдельная сборка датчиков, которая
лежит в папке `sensors/`. Она использует следующие сторонние библиотеки.
Все они распространяются вместе с программой без изменений.

## LibreHardwareMonitorLib 0.9.6

- Автор: LibreHardwareMonitor
- Лицензия: Mozilla Public License 2.0 (MPL-2.0)
- Исходный код: <https://github.com/LibreHardwareMonitor/LibreHardwareMonitor>
- Файл лицензии: `LICENSE-MPL-2.0.txt`

Читает температуры, обороты вентиляторов, напряжения и SMART-данные
накопителей. Наш код только вызывает публичный API библиотеки и не изменяет
её исходники.

## DiskInfoToolkit 1.1.2

- Автор: DiskInfoToolkit
- Лицензия: Mozilla Public License 2.0 (MPL-2.0)
- Файл лицензии: `LICENSE-MPL-2.0.txt`

Транзитивная зависимость LibreHardwareMonitorLib (работа с накопителями).

## RAMSPDToolkit-NDD 1.4.2

- Автор: RAMSPDToolkit-NDD
- Лицензия: Mozilla Public License 2.0 (MPL-2.0)
- Файл лицензии: `LICENSE-MPL-2.0.txt`

Транзитивная зависимость LibreHardwareMonitorLib (чтение SPD модулей памяти).

## BlackSharp.Core 1.0.7

- Автор: BlackSharp.Core
- Лицензия: Mozilla Public License 2.0 (MPL-2.0)
- Файл лицензии: `LICENSE-MPL-2.0.txt`

Транзитивная зависимость DiskInfoToolkit и RAMSPDToolkit-NDD.

## HidSharp 2.6.4

- Автор: James F. Bellinger
- Лицензия: Apache License 2.0
- Файл лицензии: `LICENSE-HidSharp.txt`

Доступ к HID-устройствам (используется LibreHardwareMonitorLib).

## Пакеты Microsoft .NET (System.*)

- System.Buffers 4.6.1
- System.CodeDom 10.0.2
- System.Management 10.0.2
- System.Memory 4.6.3
- System.Numerics.Vectors 4.6.1
- System.Runtime.CompilerServices.Unsafe 6.1.2
- System.Security.AccessControl 6.0.0
- System.Security.Principal.Windows 5.0.0
- System.Threading.AccessControl 10.0.3

- Лицензия: MIT
- Правообладатель: .NET Foundation и участники проекта
- Текст: <https://licenses.nuget.org/MIT>

---

Полный текст MPL-2.0 лежит в `LICENSE-MPL-2.0.txt`, текст Apache-2.0 —
в `LICENSE-HidSharp.txt`. Обе лицензии разрешают распространять библиотеки
в составе закрытой программы при условии сохранения уведомлений и, для
MPL-2.0, доступности исходников самих библиотек по указанным выше ссылкам.
