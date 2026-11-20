# Сайт MicroSpek на GitHub Pages

Публикация: https://dmitibrr.github.io/MicroSpek/  
Источник: ветка `main`, папка `/docs` (`.nojekyll` отключает обработку Jekyll).

Файлы:

- `index.html` — разметка, SEO-метаданные, Open Graph, JSON-LD;
- `styles.css` — стили;
- `app.js` — переключатель RU/EN, вкладки кода, копирование, анимации;
- `images/` — графика (генерируется `scripts/make_readme_art.py`);
- `robots.txt`, `sitemap.xml` — файлы для поисковиков.

## Добавление в поисковики

### Google Search Console

1. Выберите **«Ресурс с префиксом в URL»** (НЕ «Доменный ресурс» — домен
   `github.io` нам не принадлежит, DNS TXT не подтвердить).
2. Укажите точный адрес: `https://dmitibrr.github.io/MicroSpek/`
3. Способ подтверждения — **HTML-файл** или **HTML-тег**:
   - HTML-файл: скачайте выданный файл (`googleXXXXXXXX.html`), положите его
     в папку `docs/`, закоммитьте и запушьте; нажмите «Проверить»;
   - HTML-тег: пришлите мне строку `<meta name="google-site-verification" ...>`,
     я вставлю её в `docs/index.html` рядом с комментарием про verification.
4. После подтверждения откройте **Sitemaps**, введите
   `sitemap.xml` и нажмите «Отправить».
5. В разделе «Инспекция URL» введите корневой адрес и нажмите
   «Запросить индексацию».

### Яндекс Вебмастер

1. «Добавить сайт» → укажите `https://dmitibrr.github.io/MicroSpek/`.
2. Подтверждение — HTML-файл или meta-тег (аналогично Google).
3. «Индексирование» → «Карты сайта» → добавьте
   `https://dmitibrr.github.io/MicroSpek/sitemap.xml`.

### Bing Webmaster Tools

Проще всего «Import from Google Search Console» — подтянет сайт и
подтверждение автоматически. Либо отдельно HTML-файл/meta-тег и тот же
`sitemap.xml`.

## Что уже настроено для SEO

- `robots.txt` с разрешением индексации и ссылкой на sitemap;
- `sitemap.xml` с тремя URL: базовый, `?lang=ru`, `?lang=en`;
- `rel="canonical"` на базовый адрес;
- `hreflang` для ru / en / x-default;
- Open Graph и Twitter Card с карточкой 1200×630 (язык карточки меняется
  вместе с языком страницы);
- JSON-LD `SoftwareApplication` с версией 0.3.0, лицензией Unlicense и
  ссылкой на релиз;
- языковые метаданные и `<html lang>` переключаются на RU/EN.

## Важно

- В GSC не выбирайте «Доменный ресурс» — для `github.io` он не подойдёт.
- Подтверждающий HTML-файл должен лежать в корне **опубликованной** папки,
  то есть в `docs/`, а не в корне репозитория.
- После каждого пуша GitHub Pages пересобирает сайт автоматически (~30 с).
