# T01 — Higiene del repositorio y línea base

**Depende de:** nada. **Tamaño:** M.

## Objetivo

Dejar el repositorio limpio y el código Python legible, **sin cambiar ningún comportamiento**, para que las tareas siguientes produzcan diferencias de git revisables.

## Contexto

El código de `hub/` y `config/` está compactado: varias sentencias por línea separadas con `;`, `if` en una línea, `from .models import *`. El `.gitignore` excluye `*.sqlite3` y `private_storage/`, pero puede haber archivos versionados antes de esa regla. Existe una rama remota `mejoras-cicc` cuyo contenido no se conoce.

## Pasos

1. **Informe de estado (no cambia nada).** Ejecuta y copia en la bitácora la salida de:
   - `git status`
   - `git branch -a` y `git log --oneline -10`
   - `git log --oneline main..origin/mejoras-cicc` y `git log --oneline origin/mejoras-cicc..main`
   - `git ls-files` filtrado por `sqlite3`, `private_storage`, `.pyc`, `.log`, `.env`, `.venv`
   No fusiones ni borres `mejoras-cicc`. Si tiene commits que `main` no tiene, anótalo en "Preguntas para el arquitecto" y continúa.
2. **Línea base de pruebas.** Con `QA_SQLITE=1` y `DEBUG=1`, ejecuta `manage.py check`, `makemigrations --check --dry-run` y `test hub -v 2`. Anota el número de pruebas y el resultado. Si algo falla antes de tocar nada, detente y reporta.
3. **Commit 1 — higiene.**
   - Quita del índice (sin borrar del disco) cualquier archivo versionado que deba ignorarse: `git rm --cached`.
   - Amplía `.gitignore` con: `staticfiles/`, `logs/`, `*.log`, `.ruff_cache/`, `.vercel/`, `.env.*` y la excepción `!.env.example`.
   - Crea `pyproject.toml` con configuración de ruff: `line-length = 100`, `target-version = "py312"`, reglas `E`, `F`, `I`, `B`, `UP`; excluye `hub/migrations` y `.venv`.
   - Crea `requirements-dev.txt` con `-r requirements.txt` y `ruff` con rango de versión.
4. **Commit 2 — solo formato.**
   - Ejecuta `ruff format .` sobre `config/`, `hub/` y `manage.py`.
   - Sustituye cada `from .models import *` y `from hub.models import *` por importaciones explícitas.
   - Corrige lo que marque `ruff check .` sin alterar la lógica. Si una corrección exige cambiar comportamiento, usa `# noqa` con el código de la regla y anótalo en "Observaciones".
   - No reformatees plantillas HTML, CSS ni JavaScript (lo hace T04 al dividirlas).
5. Repite el paso 2 y confirma el mismo número de pruebas aprobadas.

## Criterios de aceptación

- [ ] `git ls-files` no lista ningún `.sqlite3`, `.pyc`, `.log`, `.env` ni archivos de `private_storage/` o `.venv/`.
- [ ] `ruff check .` y `ruff format --check .` terminan sin hallazgos.
- [ ] No queda ningún `import *` en `hub/` ni `config/`.
- [ ] Las 12 pruebas existentes pasan sin haber sido modificadas (salvo sus líneas de importación).
- [ ] El commit de formato no contiene cambios en `templates/`, `static/`, migraciones ni documentación.
- [ ] La bitácora incluye el informe del paso 1.

## Fuera de alcance

Cambiar `settings.py` más allá del formato, mover archivos, renombrar funciones, tocar plantillas, borrar `demo.sqlite3` del disco, fusionar ramas.
