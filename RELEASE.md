# Релиз MicroSpek

## Подготовка

1. Обновить `__version__` в `src/microspek/__init__.py` и `pyproject.toml`.
2. Добавить запись в `CHANGELOG.md`.
3. Прогнать локально:

   ```powershell
   python -m pip install -r requirements.txt
   python -m compileall -q src
   python -m unittest discover -s tests -v
   python scripts/build_release.py
   ```

4. Закоммитить изменения и получить тег:

   ```powershell
   git add -A
   git commit -m "Release v0.1.0"
   git tag v0.1.0
   git push origin main
   git push origin v0.1.0
   ```

   Workflow `.github/workflows/release.yml` соберёт `dist/*.zip` и создаст
   GitHub release с auto-generated notes.

## Релиз вручную через GitHub CLI

```powershell
gh auth login
gh repo create <owner>/microspek --public --source=. --remote=origin --push
python scripts/build_release.py
gh release create v0.1.0 dist/*.zip dist/*.sha256 --title "MicroSpek 0.1.0" --notes-file CHANGELOG.md
```

Проверка:

```powershell
gh release list
gh release view v0.1.0
```

## Публикация в PyPI (опционально)

```powershell
python -m pip install build twine
python -m build
twine check dist/*
twine upload dist/microspek-*.whl dist/microspek-*.tar.gz
```

После установки из PyPI команда `microspek` доступна через entry point
`microspek.__main__:main` из `pyproject.toml`.
