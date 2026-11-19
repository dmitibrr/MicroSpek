# Релиз MicroSpek 0.3.0

## Что публикуем

Четыре архива из `dist/` (вместе с `.sha256` рядом):

| Архив | Содержимое |
| --- | --- |
| `MicroSpek-0.3.0-full-WIN64.zip` | GUI + CLI + хелпер датчиков + `SNAPSHOT.cmd` |
| `MicroSpek-0.3.0-gui-WIN64.zip` | только окно |
| `MicroSpek-0.3.0-cli-WIN64.zip` | только консоль |
| `MicroSpek-0.3.0-snapshot-WIN64.zip` | лёгкий снапшот + `microspek.json` |

Все архивы содержат `LICENSE` (Unlicense), `README.txt` и папку `sensors/`
с уведомлениями третьих лиц.

## Подготовка релиза

1. Версия уже выставлена в `src/microspek/__init__.py` и `pyproject.toml` — `0.3.0`.
2. Запись в `CHANGELOG.md` добавлена.
3. Локальная проверка перед публикацией:

   ```powershell
   python -m compileall -q src
   python -m unittest discover -s tests -v     # 33 теста
   python scripts/build_exe.py --edition all   # 4 ZIP + SHA256 в dist/
   ```

4. Проверить каждый `.exe`: версию, `--summary`, экспорт MD, запуск окна,
   конфиг `microspek.json` (снапшот-издание).

## Публикация

```powershell
gh auth status
gh repo create dmitibrr/MicroSpek --public --source=. --remote=origin --push
git tag v0.3.0
git push origin v0.3.0
gh release create v0.3.0 `
  dist/MicroSpek-0.3.0-full-WIN64.zip `
  dist/MicroSpek-0.3.0-gui-WIN64.zip `
  dist/MicroSpek-0.3.0-cli-WIN64.zip `
  dist/MicroSpek-0.3.0-snapshot-WIN64.zip `
  dist/*.sha256 `
  --title "MicroSpek 0.3.0" --notes-file CHANGELOG.md
```

Workflow `.github/workflows/release.yml` при пуше тега тоже соберёт четыре
издания (сначала скачивает зависимости датчиков через
`scripts/fetch_sensors_vendor.py`) и создаст GitHub release с автозаметками.

Проверка после публикации:

```powershell
gh release list
gh release view v0.3.0
```

## Важно

Публикация в GitHub выполняется только после того, как автор протестирует
собранные архивы и подтвердит, что всё работает.
