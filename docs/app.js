/* MicroSpek landing page — bilingual RU/EN, no dependencies. */
(function () {
  "use strict";

  var I18N = {
    ru: {
      nav_features: "Возможности",
      nav_editions: "Издания",
      nav_preview: "Вид окна",
      nav_cli: "CLI",
      nav_faq: "Вопросы",
      download: "Скачать",
      eyebrow: "WINDOWS 10 / 11 · PORTABLE · OFFLINE",
      hero_lead: "Характеристики ПК без лишних движений",
      hero_desc: "Процессор, память с профилем XMP, диски с разметкой и SMART, видеокарта, мониторы, сеть, датчики — одним окном или одним файлом для ИИ.",
      btn_download: "Скачать для Windows",
      btn_explore: "Посмотреть окно",
      stat_seconds: "полный слепок",
      stat_editions: "издания под разные задачи",
      stat_offline: "телеметрии и сети",
      chip_b: "RU / EN",
      trust_1: "Готовый .exe — Python не нужен",
      trust_2: "Лицензии третьих лиц внутри",
      trust_3: "Общественное достояние",
      trust_4: "Работает офлайн",
      features_kicker: "ЧТО ВНУТРИ",
      features_title: "Всё важное — без лишнего шума",
      features_desc: "Несколько десятков полей о железе, собранных параллельно и поданных так, чтобы их было приятно читать.",
      f1_title: "Живые датчики",
      f1_desc: "Температуры GPU и hot spot, обороты вентиляторов, напряжение, мощность, SMART-температуры и остаток ресурса дисков.",
      f2_title: "Разметка дисков",
      f2_desc: "Физические диски, разделы, тома и занятое место — цветной полосой с легендой, а не стеной цифр.",
      f3_title: "Быстро",
      f3_desc: "Коллекторы работают параллельно: полный слепок ≈ 4,5 с из исходников и ≈ 5,7 с в собранном exe.",
      f4_title: "Приватно",
      f4_desc: "Флаг --redact прячет серийники, MAC и пользователя перед отправкой. Никакой телеметрии и собственных сетевых запросов.",
      editions_kicker: "ЧЕТЫРЕ ИЗДАНИЯ",
      editions_title: "Возьмите только то, что нужно",
      editions_desc: "Один код, четыре самостоятельные сборки. Любая работает без установки Python — распакуйте архив и запустите exe.",
      ed_popular: "ПОПУЛЯРНОЕ",
      ed_full_role: "Для всех и вся",
      ed_full_1: "Окно + консоль + датчики",
      ed_full_2: "SNAPSHOT.cmd в один клик",
      ed_full_3: "Уведомления третьих лиц внутри",
      ed_gui_tag: "ДЛЯ ДОМА",
      ed_gui_role: "Приятное окно, без консоли",
      ed_gui_1: "Обновлённый интерфейс RU / EN",
      ed_gui_2: "Меню экспорта TXT / JSON / MD",
      ed_gui_3: "Скриншот окна и датчики",
      ed_cli_tag: "ДЛЯ СКРИПТОВ",
      ed_cli_role: "Консоль для агентов и CI",
      ed_cli_1: "Флаги --summary, --output, --sections",
      ed_cli_2: "Опциональный microspek.json",
      ed_cli_3: "Никаких GUI-библиотек",
      ed_snap_tag: "ДЛЯ ВСТРАИВАНИЯ",
      ed_snap_role: "Максимально лёгкий и настраиваемый",
      ed_snap_1: "Настройки в microspek.json",
      ed_snap_2: "Только нужные разделы и без датчиков",
      ed_snap_3: "≈ 3,6 с на типичном наборе",
      preview_kicker: "ТАК ВЫГЛЯДИТ ОКНО",
      preview_title: "Спокойный интерфейс, всё на виду",
      preview_desc: "Вкладка «Сводка» собирает главное на одном экране, остальные показывают детали. Переключение языка — в правом верхнем углу.",
      cli_kicker: "КОМАНДНАЯ СТРОКА",
      cli_title: "Одна команда — готовый отчёт",
      cli_desc: "TXT для чата, JSON для скриптов, Markdown для Notion и Obsidian. Язык отчёта задаётся флагом --lang.",
      tab_cli: "CLI",
      tab_md: "Markdown",
      tab_json: "JSON",
      tab_config: "Конфиг",
      copy: "Копировать",
      copied: "Скопировано",
      note_1: "--redact скрывает серийные номера, MAC и пользователя — включайте перед отправкой.",
      note_2: "--no-dxdiag экономит до минуты: подробности DirectX обычно не нужны.",
      note_3: "--sections cpu,memory,storage и --no-sensors превращают полный сбор в быстрый частичный.",
      privacy_kicker: "ДАТЧИКИ И ПРИВАТНОСТЬ",
      privacy_title: "Ничего лишнего — даже в сети",
      privacy_desc: "MicroSpek работает локально. Единственные сетевые значения в отчёте — адаптеры и адреса, которые уже знает Windows.",
      p1_title: "Датчики и права",
      p1_desc: "Хелпер LibreHardwareMonitorLib работает без прав и сразу отдаёт доступное. Один запрос UAC добавляет температуры CPU и SMART дисков; отказ ничего не ломает. Для вентиляторов на многих платах нужен драйвер PawnIO — он не входит в архив.",
      p2_title: "Лицензия и чистота",
      p2_desc: "MicroSpek — Unlicense: используйте, меняйте и распространяйте без указания авторства. Лицензии LibreHardwareMonitorLib и HidSharp лежат в папке sensors рядом с программой. Никаких аккаунтов, ключей и телеметрии.",
      faq_kicker: "ЧАСТЫЕ ВОПРОСЫ",
      faq_title: "Коротко о главном",
      faq_desc: "Если ответа нет — issues на GitHub.",
      q1: "Нужно ли ставить Python?",
      a1: "Нет. В каждый архив входит готовый exe с Python внутри. Распакуйте папку целиком и запускайте.",
      q2: "Почему SmartScreen ругается?",
      a2: "Архивы не подписаны сертификатом. Нажмите «Подробнее» → «Выполнить в любом случае».",
      q3: "Где температуры CPU и SMART?",
      a3: "Их запрашивает кнопка «Датчики (админ)» или флаг --admin-sensors. Без прав остаются доступны GPU и SMART части дисков; для CPU-вентиляторов часто нужен PawnIO.",
      q4: "Чем Markdown лучше TXT?",
      a4: "Markdown — это таблицы и заголовки: файл сразу выглядит аккуратно в GitHub, Notion, Obsidian и чате с ИИ. TXT удобен для чтения в консоли.",
      q5: "Можно ли встроить в свою программу?",
      a5: "Да, для этого есть издание snapshot: microspek-snapshot.exe читает microspek.json, собирает только нужные разделы и пишет файл без окна и вопросов.",
      cta_title: "Пора посмотреть, что у вас внутри",
      cta_desc: "Скачайте любой из четырёх архивов — это бесплатно, офлайн и без регистрации.",
      cta_button: "Перейти к загрузке",
      footer_download: "Релиз",
      footer_license: "Общественное достояние · Unlicense",
      page_title: "MicroSpek — характеристики ПК без лишних движений",
      page_description: "MicroSpek — быстрый слепок железа ПК: GUI, CLI, TXT/JSON/Markdown и датчики. Четыре отдельные EXE-издания для Windows.",
      hero_image: "images/hero-ru.png",
      hero_alt: "MicroSpek — характеристики ПК без лишних движений",
      screen_alt_ru: "MicroSpek — вкладка «Сводка»",
      screen_alt_en: "MicroSpek — вкладка «Сводка» (RU)"
    },
    en: {
      nav_features: "Features",
      nav_editions: "Editions",
      nav_preview: "Screenshots",
      nav_cli: "CLI",
      nav_faq: "FAQ",
      download: "Download",
      eyebrow: "WINDOWS 10 / 11 · PORTABLE · OFFLINE",
      hero_lead: "PC specifications without the fuss",
      hero_desc: "CPU, memory with XMP profiles, disks with partitions and SMART, GPU, monitors, network and live sensors — in one window or one file for an AI.",
      btn_download: "Download for Windows",
      btn_explore: "See the window",
      stat_seconds: "for a full snapshot",
      stat_editions: "editions for different jobs",
      stat_offline: "telemetry or network calls",
      chip_b: "RU / EN",
      trust_1: "Ready-to-run .exe — no Python",
      trust_2: "Third-party notices included",
      trust_3: "Public domain software",
      trust_4: "Works offline",
      features_kicker: "INSIDE",
      features_title: "Everything important, nothing noisy",
      features_desc: "Dozens of hardware fields collected in parallel and presented so they are actually pleasant to read.",
      f1_title: "Live sensors",
      f1_desc: "GPU temperature and hot spot, fan RPM, voltage, power, disk SMART temperatures and remaining life.",
      f2_title: "Disk layout",
      f2_desc: "Physical disks, partitions, volumes and used space as a colour bar with a legend, not a wall of numbers.",
      f3_title: "Fast",
      f3_desc: "Collectors run in parallel: a full snapshot takes ~4.5 s from source and ~5.7 s in the packaged exe.",
      f4_title: "Private",
      f4_desc: "--redact hides serial numbers, MAC addresses and the user before sharing. No telemetry and no network calls of its own.",
      editions_kicker: "FOUR EDITIONS",
      editions_title: "Take only what you need",
      editions_desc: "One code base, four standalone builds. None needs Python: unpack the archive and run the exe.",
      ed_popular: "MOST POPULAR",
      ed_full_role: "For all and everything",
      ed_full_1: "GUI + CLI + sensor helper",
      ed_full_2: "SNAPSHOT.cmd in one click",
      ed_full_3: "Third-party notices included",
      ed_gui_tag: "FOR EVERYDAY USE",
      ed_gui_role: "A nicer window, no console",
      ed_gui_1: "Redesigned RU / EN interface",
      ed_gui_2: "One export menu: TXT / JSON / MD",
      ed_gui_3: "Window screenshot and sensors",
      ed_cli_tag: "FOR SCRIPTS",
      ed_cli_role: "Console for agents and CI",
      ed_cli_1: "--summary, --output, --sections flags",
      ed_cli_2: "Optional microspek.json",
      ed_cli_3: "No GUI libraries at all",
      ed_snap_tag: "FOR EMBEDDING",
      ed_snap_role: "The leanest, most configurable build",
      ed_snap_1: "Settings in microspek.json",
      ed_snap_2: "Only the sections you need, no sensors",
      ed_snap_3: "~3.6 s for a typical selection",
      preview_kicker: "THE WINDOW",
      preview_title: "A calm interface, everything in view",
      preview_desc: "The Summary tab puts the essentials on one screen; the other tabs show details. The language switch sits in the top-right corner.",
      cli_kicker: "COMMAND LINE",
      cli_title: "One command, a ready report",
      cli_desc: "TXT for a chat, JSON for scripts, Markdown for Notion and Obsidian. Set the report language with --lang.",
      tab_cli: "CLI",
      tab_md: "Markdown",
      tab_json: "JSON",
      tab_config: "Config",
      copy: "Copy",
      copied: "Copied",
      note_1: "--redact hides serial numbers, MAC addresses and the user — enable it before sharing.",
      note_2: "--no-dxdiag saves up to a minute: DirectX details are usually not needed.",
      note_3: "--sections cpu,memory,storage and --no-sensors turn a full run into a fast partial report.",
      privacy_kicker: "SENSORS & PRIVACY",
      privacy_title: "Nothing extra — not even on the network",
      privacy_desc: "MicroSpek works locally. The only network values in the report are the adapters and addresses Windows already knows.",
      p1_title: "Sensors and rights",
      p1_desc: "The LibreHardwareMonitorLib helper runs without elevation and returns what is available. One UAC prompt adds CPU temperatures and disk SMART; declining changes nothing else. Fan speeds on many boards need the PawnIO driver, which is not bundled.",
      p2_title: "Licence and cleanliness",
      p2_desc: "MicroSpek is Unlicense: use, modify and redistribute it without attribution. LibreHardwareMonitorLib and HidSharp notices sit in the sensors folder next to the program. No accounts, no keys, no telemetry.",
      faq_kicker: "FAQ",
      faq_title: "The short version",
      faq_desc: "If your question is not here — open an issue on GitHub.",
      q1: "Do I need Python installed?",
      a1: "No. Every archive contains a ready exe with Python bundled. Unpack the whole folder and run it.",
      q2: "Why does SmartScreen complain?",
      a2: "The archives are not code-signed. Choose More info → Run anyway.",
      q3: "Where are CPU temperatures and SMART?",
      a3: "The Sensors (admin) button or --admin-sensors asks for UAC once. Without elevation GPU and some disk SMART values still work; CPU fans often need PawnIO.",
      q4: "Why Markdown instead of TXT?",
      a4: "Markdown is headings and tables: it renders neatly in GitHub, Notion, Obsidian and AI chats. TXT is easier to read in a console.",
      q5: "Can I embed it into my app?",
      a5: "Yes — that is the snapshot edition: microspek-snapshot.exe reads microspek.json, collects only the sections you list and writes a file with no window and no questions.",
      cta_title: "See what is inside your PC",
      cta_desc: "Download any of the four archives — free, offline and without registration.",
      cta_button: "Go to downloads",
      footer_download: "Release",
      footer_license: "Public domain · Unlicense",
      page_title: "MicroSpek — PC specifications without the fuss",
      page_description: "MicroSpek — a fast hardware snapshot: GUI, CLI, TXT/JSON/Markdown and live sensors. Four standalone EXE editions for Windows.",
      hero_image: "images/hero.png",
      hero_alt: "MicroSpek — PC specifications without the fuss",
      screen_alt_ru: "MicroSpek — the Summary tab (RU)",
      screen_alt_en: "MicroSpek — the Summary tab"
    }
  };

  var CODE = {
    ru: {
      cli: [
        "microspek.exe --summary",
        "microspek.exe --output md --file pc.md --redact --lang ru",
        "microspek.exe --admin-sensors --output txt --file full.txt",
        "microspek.exe --sections cpu,memory,storage --no-sensors"
      ].join("\n"),
      md: [
        "## Процессор",
        "",
        "### Основное",
        "",
        "| Параметр | Значение | Примечание |",
        "| --- | --- | --- |",
        "| Модель | Intel(R) Xeon(R) CPU E3-1270 v3 @ 3.50GHz |  |",
        "| Ядра / потоки | 4 / 8 |  |",
        "| Частота | 3,50 ГГц |  |"
      ].join("\n"),
      json: [
        "{",
        "  \"schema\": \"microspek.snapshot/1\",",
        "  \"language\": \"ru\",",
        "  \"hostname\": \"DESKTOP-PC\",",
        "  \"sections\": [",
        "    { \"key\": \"cpu\", \"title\": \"Процессор\",",
        "      \"summary\": [{ \"label\": \"Модель\", \"value\": \"...\" }] }",
        "  ]",
        "}"
      ].join("\n"),
      config: [
        "{",
        "  \"output\": \"md\",",
        "  \"file\": \"reports/pc.md\",",
        "  \"redact\": true,",
        "  \"sections\": [\"os\", \"cpu\", \"memory\", \"storage\", \"gpu\"],",
        "  \"sensors\": true,",
        "  \"dxdiag\": false,",
        "  \"lang\": \"ru\",",
        "  \"quiet\": false",
        "}"
      ].join("\n")
    },
    en: {
      cli: [
        "microspek.exe --summary",
        "microspek.exe --output md --file pc.md --redact --lang en",
        "microspek.exe --admin-sensors --output txt --file full.txt",
        "microspek.exe --sections cpu,memory,storage --no-sensors"
      ].join("\n"),
      md: [
        "## Processor",
        "",
        "### General",
        "",
        "| Parameter | Value | Note |",
        "| --- | --- | --- |",
        "| Model | Intel(R) Xeon(R) CPU E3-1270 v3 @ 3.50GHz |  |",
        "| Cores / threads | 4 / 8 |  |",
        "| Clock | 3.50 GHz |  |"
      ].join("\n"),
      json: [
        "{",
        "  \"schema\": \"microspek.snapshot/1\",",
        "  \"language\": \"en\",",
        "  \"hostname\": \"DESKTOP-PC\",",
        "  \"sections\": [",
        "    { \"key\": \"cpu\", \"title\": \"Processor\",",
        "      \"summary\": [{ \"label\": \"Model\", \"value\": \"...\" }] }",
        "  ]",
        "}"
      ].join("\n"),
      config: [
        "{",
        "  \"output\": \"md\",",
        "  \"file\": \"reports/pc.md\",",
        "  \"redact\": true,",
        "  \"sections\": [\"os\", \"cpu\", \"memory\", \"storage\", \"gpu\"],",
        "  \"sensors\": true,",
        "  \"dxdiag\": false,",
        "  \"lang\": \"en\",",
        "  \"quiet\": false",
        "}"
      ].join("\n")
    }
  };

  var lang = "ru";
  var codeTab = "cli";
  var shot = "ru";

  function safeLang(value) {
    return value === "ru" || value === "en" ? value : null;
  }

  function readStoredLang() {
    try {
      return safeLang(window.localStorage.getItem("microspek-lang"));
    } catch (e) {
      return null;
    }
  }

  function storeLang(value) {
    try {
      window.localStorage.setItem("microspek-lang", value);
    } catch (e) {
      /* storage can be disabled; the switch still works for this page */
    }
  }

  function initialLang() {
    var query = new URLSearchParams(window.location.search).get("lang");
    var fromQuery = safeLang((query || "").toLowerCase());
    if (fromQuery) return fromQuery;
    var stored = readStoredLang();
    if (stored) return stored;
    return (navigator.language || "").toLowerCase().indexOf("ru") === 0 ? "ru" : "en";
  }

  function setShot(value) {
    shot = safeLang(value) || "ru";
    var image = document.getElementById("screenImage");
    image.src = "images/gui-preview-" + shot + ".png";
    image.alt = I18N[lang]["screen_alt_" + shot];
    var buttons = document.querySelectorAll(".shot-btn");
    for (var i = 0; i < buttons.length; i++) {
      buttons[i].classList.toggle("is-active", buttons[i].getAttribute("data-shot") === shot);
    }
  }

  function render() {
    var dict = I18N[lang];
    document.documentElement.lang = lang;
    document.title = dict.page_title;

    var description = document.querySelector('meta[name="description"]');
    if (description) description.setAttribute("content", dict.page_description);

    var nodes = document.querySelectorAll("[data-i18n]");
    for (var i = 0; i < nodes.length; i++) {
      var key = nodes[i].getAttribute("data-i18n");
      if (Object.prototype.hasOwnProperty.call(dict, key)) {
        nodes[i].textContent = dict[key];
      }
    }

    var hero = document.getElementById("heroImage");
    hero.src = dict.hero_image;
    hero.alt = dict.hero_alt;

    var langButtons = document.querySelectorAll(".lang-btn");
    for (var j = 0; j < langButtons.length; j++) {
      langButtons[j].classList.toggle(
        "is-active", langButtons[j].getAttribute("data-lang") === lang
      );
    }

    document.getElementById("codeBlock").textContent = CODE[lang][codeTab];
    setShot(shot);
  }

  function setLang(value) {
    var next = safeLang(value);
    if (!next || next === lang) return;
    lang = next;
    storeLang(lang);
    var url = new URL(window.location.href);
    url.searchParams.set("lang", lang);
    window.history.replaceState(null, "", url);
    setShot(lang);
    render();
  }

  function setupControls() {
    var langButtons = document.querySelectorAll(".lang-btn");
    for (var i = 0; i < langButtons.length; i++) {
      langButtons[i].addEventListener("click", function () {
        setLang(this.getAttribute("data-lang"));
      });
    }

    var shotButtons = document.querySelectorAll(".shot-btn");
    for (var s = 0; s < shotButtons.length; s++) {
      shotButtons[s].addEventListener("click", function () {
        setShot(this.getAttribute("data-shot"));
      });
    }

    var codeTabs = document.querySelectorAll(".code-tab");
    for (var t = 0; t < codeTabs.length; t++) {
      codeTabs[t].addEventListener("click", function () {
        codeTab = this.getAttribute("data-code");
        for (var k = 0; k < codeTabs.length; k++) {
          codeTabs[k].classList.toggle("is-active", codeTabs[k] === this);
        }
        document.getElementById("codeBlock").textContent = CODE[lang][codeTab];
      });
    }

    var copyBtn = document.getElementById("copyBtn");
    copyBtn.addEventListener("click", function () {
      var text = document.getElementById("codeBlock").textContent;
      function done() {
        copyBtn.textContent = I18N[lang].copied;
        window.setTimeout(function () {
          copyBtn.textContent = I18N[lang].copy;
        }, 1400);
      }
      if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(text).then(done, function () { done(); });
      } else {
        var area = document.createElement("textarea");
        area.value = text;
        document.body.appendChild(area);
        area.select();
        try { document.execCommand("copy"); } catch (e) { /* ignore */ }
        document.body.removeChild(area);
        done();
      }
    });

    var menuToggle = document.getElementById("menuToggle");
    var nav = document.getElementById("nav");
    menuToggle.addEventListener("click", function () {
      var open = nav.classList.toggle("open");
      menuToggle.setAttribute("aria-expanded", open ? "true" : "false");
    });
    nav.addEventListener("click", function (event) {
      if (event.target.tagName === "A") {
        nav.classList.remove("open");
        menuToggle.setAttribute("aria-expanded", "false");
      }
    });
  }

  function setupReveal() {
    var elements = document.querySelectorAll(".reveal");
    if (!("IntersectionObserver" in window)) {
      for (var i = 0; i < elements.length; i++) elements[i].classList.add("in-view");
      return;
    }
    var observer = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (entry.isIntersecting) {
          entry.target.classList.add("in-view");
          observer.unobserve(entry.target);
        }
      });
    }, { threshold: 0.1, rootMargin: "0px 0px -40px 0px" });
    for (var j = 0; j < elements.length; j++) observer.observe(elements[j]);
  }

  lang = initialLang();
  setupControls();
  render();
  setupReveal();
})();
