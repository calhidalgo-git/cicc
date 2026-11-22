# Bitácora de implementación

Cada implementador agrega una entrada al final al terminar o bloquear una tarea. No edites entradas de otros. El arquitecto usa este archivo en la revisión final.

## Formato

```
## TNN — Título de la tarea
- Fecha:
- Modelo / herramienta:
- Rama y pull request:
- Estado: En revisión | Bloqueada

### Qué se hizo
(3 a 8 líneas; archivos principales tocados)

### Desviaciones respecto a la tarea
(ninguna, o qué y por qué)

### Verificación
(salida real y resumida de: check, makemigrations --check, test, ruff; más cualquier comprobación manual de los criterios de aceptación)

### Preguntas para el arquitecto
(ninguna, o lista)

### Observaciones
(problemas vistos fuera del alcance, sin arreglar)
```

---

## T01 — Higiene del repositorio y línea base
- Fecha: 2026-11-21
- Modelo / herramienta: Claude Opus 5.5 (Claude Code)
- Rama y pull request: `tarea/T01-higiene-y-linea-base` en el proyecto local `CICC_original`, creada desde `main` (`ea61b75`). Sin publicar y sin remoto configurado.
- Estado: En revisión

### Punto de partida
`CICC_original` es un proyecto nuevo, creado el 21-11-2026 a pedido de Carlos. Parte de su versión: el commit `bc7110f` (18-10-2026) más sus cambios locales y el curso de Certificación (commit `ea61b75`). El rediseño `mejoras-cicc` de GitHub no forma parte de este proyecto. Carlos no reconoce la cuenta que lo hizo. Las ramas que se hicieron antes sobre ese rediseño siguen en el repositorio `CICC` como referencia.

### Qué se hizo
| Commit | Contenido |
|---|---|
| `35a9894` | `AGENTS.md`, `CLAUDE.md` y `docs/arquitecto/`, sin cambios respecto al original (commit `a799773` del repositorio CICC). |
| `eb8ea12` | Higiene. Los 18 `.pyc` versionados salen del índice con `git rm --cached` y siguen en disco. `.gitignore` agrega `staticfiles/`, `logs/`, `*.log`, `.ruff_cache/`, `.vercel/`, `.env.*`, `!.env.example` y `demo-credentials.txt`. `pyproject.toml` configura ruff (línea de 100, `py312`, reglas `E F I B UP`, sin `hub/migrations` ni `.venv`). `requirements-dev.txt` agrega `ruff>=0.6,<1`. |
| `9fed336` | Solo formato. `ruff format` en `config/`, `hub/` y `manage.py`. Los tres `import *` pasan a importaciones explícitas. Correcciones de `ruff check` sin cambiar lógica: orden de importaciones, `from django.db.models import Q` al inicio de `views.py`, `type(x) is not int` en lugar de `!=` (equivalentes para tipos), `_label` en un bucle de `seed_demo` y un mensaje partido en dos literales. |

### Desviaciones respecto a la tarea
- **`demo.sqlite3` sigue versionada.** Es la misma excepción que Carlos aprobó el 18-11-2026: el bloque de Vercel de `config/settings.py` la copia del repositorio, y se retira en T02, junto con Vercel.
- **Comillas simples** (`quote-style = "single"`). El código ya las usa, y así el formato no reescribe cada cadena.
- **E501 se ignora solo en `hub/catalog.py` y `seed_demo.py`.** Son textos de contenido de cientos de caracteres; partirlos cambiaría muchas líneas sin aportar legibilidad. En `views.py` la única línea larga se partió.
- **Prueba sin cambios:** en `hub/tests.py`, `l = Lesson.objects.first()` lleva `# noqa: E741` en lugar de renombrar la variable. `ruff --fix` quitó una importación sin uso (`User`) de ese archivo. Es una línea de importación, la excepción que admite la ficha. `ruff format` también reformateó las pruebas, sin cambiar su contenido.

### Verificación
**Paso 1, informe de estado** (antes de los commits de T01):
- `git status`: limpio.
- `git branch -a`: `main` y `tarea/T01-higiene-y-linea-base`. No hay remoto: el proyecto se creó sin conexión a GitHub, así que `origin/mejoras-cicc` no existe aquí y las comparaciones con esa rama no aplican.
- `git log --oneline -10`: `35a9894`, `ea61b75`, `bc7110f Enhance settings.py for Vercel deployment`, `04f08f6`, `88af6a4`, `fdc5fa1`, `2cb0e13`, `41aafd6 Initial commit`.
- `git ls-files` filtrado: 18 `.pyc` en `config/__pycache__/`, `hub/__pycache__/`, `hub/management/…/__pycache__/` y `hub/migrations/__pycache__/`, más `demo.sqlite3`. Ningún `.log`, `.env`, `private_storage/` ni `.venv/`.

**Paso 2, línea base** (`QA_SQLITE=1`, `DEBUG=1`), antes y después de los commits:
```
System check identified no issues (0 silenced).
No changes detected
Ran 12 tests in 7.278s   (antes)
OK
Ran 12 tests in 7.241s   (después)
OK
```
- `ruff check .` → `All checks passed!` · `ruff format --check .` → `40 files already formatted`.
- Comparación del árbol sintáctico de cada `.py` antes y después del formato:
  - Las únicas diferencias son las importaciones explícitas, la importación sin uso quitada en las pruebas y, en el cuerpo, `seed_demo.handle` (`_label`), `views.save` e `views.import_excel` (`is not` y el mensaje partido).
  - `config/settings.py`, `urls.py`, `wsgi.py`, `hub/models.py`, `admin.py`, `catalog.py`, `test_cicc.py` y `manage.py` tienen el mismo cuerpo.
- `git show --stat 9fed336`: no toca `templates/`, `static/`, migraciones ni documentación.

Criterios de aceptación:
- [~] `git ls-files` sin `.sqlite3`, `.pyc`, `.log`, `.env`, `private_storage/` ni `.venv/`: cumplido salvo `demo.sqlite3` (excepción aprobada, se retira en T02).
- [x] `ruff check .` y `ruff format --check .` sin hallazgos.
- [x] Ningún `import *` en `hub/` ni `config/`.
- [x] Las 12 pruebas pasan; solo cambian su formato, una importación y un `# noqa`.
- [x] El commit de formato no toca plantillas, estáticos, migraciones ni documentación.
- [x] La bitácora incluye el informe del paso 1.

### Preguntas para el arquitecto
- Ninguna nueva. La excepción de `demo.sqlite3` y el traslado de ruff a `pyproject.toml` ya los aprobó Carlos.

### Observaciones
- Los `.pyc` siguen en disco y quedan ignorados. Vercel no los necesita.
- El proyecto usa el entorno virtual de la carpeta `CICC` (Django 5.2, ruff 0.17.5), porque esta carpeta aún no tiene uno propio.

## T02 — Configuración por entorno
- Fecha: 2026-11-21
- Modelo / herramienta: Claude Opus 5.5 (Claude Code)
- Rama y pull request: `tarea/T02-configuracion-por-entorno` en `CICC_original`, creada desde `tarea/T01-higiene-y-linea-base`. Commit `b9fe456`. Sin publicar.
- Estado: En revisión

### Qué se hizo
Se reutilizó el diseño de la T02 que ya revisó Codex en el repositorio CICC, con sus correcciones, adaptado al código de Carlos:
- **`config/env.py`:** `load_env_file`, `env_bool`, `env_list` y `env_required`.
- **`config/settings.py`:**
  - Sin variables arranca en producción y exige `DJANGO_SECRET_KEY`, `CICC_ALLOWED_HOSTS` y `PGDATABASE`, `PGUSER`, `PGPASSWORD` y `PGHOST`. `PGPORT` vale 5432 por defecto.
  - Rechaza las claves publicadas: la de demo, la que tenía esta configuración antes (`local-prototype-only-change-before-deployment`) y la de ejemplo (`genera-una-clave-aleatoria`).
  - Valida los hosts después de separar la lista.
  - `DEBUG` solo se activa con `DEBUG=1`.
  - `CICC_DEMO=1` usa SQLite y la clave de desarrollo. `QA_SQLITE=1` solo cambia el motor.
  - Incluye `CICC_CSRF_TRUSTED_ORIGINS`, `CICC_HTTPS` (cookies seguras, redirección, HSTS y cabecera del proxy) y los cuatro validadores de contraseña, con un mínimo de 10 caracteres.
  - Se elimina el bloque de Vercel y `.vercel.app`.
- **Archivo `.env`:** se lee de la raíz, si existe, sin sobrescribir variables del sistema. `CICC_ENV_FILE` indica otra ruta o, vacía, ninguna; así las pruebas no dependen del `.env` del desarrollador. `.env.example` deja la clave vacía.
- **Plantillas:** `hub.context_processors.cicc` entrega `cicc_demo`. En `templates/base.html` solo cambian las condiciones de «ENTORNO DEMO» y «Datos ficticios de demostración».
- **Documentación y demo:** `START-DEMO.ps1` usa `CICC_DEMO=1`. El README separa la demo de la instalación con PostgreSQL (`migrate` y `createsuperuser`, sin `seed_demo` y con una clave aleatoria) y documenta las variables. `INSTRUCCIONES-WINDOWS.md` usa `CICC_DEMO`.
- **`demo.sqlite3`:** sale del índice (`git rm --cached`) y sigue en disco con el mismo hash (`09f477c4b8bb…`). Cierra la excepción de T01.
- **Pruebas:** `hub/test_config.py`, con 34. No había `vercel.json` ni carpeta `api/`.

### Desviaciones respecto a la tarea
- **Correcciones de la revisión de Codex incluidas desde el principio.** Son el rechazo de claves conocidas, la validación de hosts después de separar la lista, el aislamiento del `.env` en las pruebas, `QA_SQLITE` sin relajar las `PG*` y los arranques separados en el README.
- **Sin correo ni WhiteNoise.** La versión de Carlos no los tiene, y WhiteNoise corresponde a T09.

### Verificación
- `CICC_DEMO=1`: `System check identified no issues (0 silenced).` · `No changes detected` · `Ran 46 tests in 16.031s` · `OK`. Son las 12 originales más 34 de configuración.
- PostgreSQL 16 local (modo producción, base de pruebas temporal): `check` y `makemigrations --check` sin incidencias. `Ran 46 tests` con `FAILED (failures=1)`: falla `test_excel_and_backup`. **La falla es previa a T02:**
  - La plantilla de importación (`views.py`) trae fija la evaluación con ID 1.
  - En PostgreSQL las secuencias no se reinician entre pruebas, así que la evaluación ya no tiene ID 1.
  - La prueba pasa sola (`Ran 1 test … OK`) y falla dentro de la suite.
  - No se corrigió, porque está fuera del alcance (ver Observaciones).
- `ruff check .` → `All checks passed!` · `ruff format --check .` → `43 files already formatted`.
- Sin variables (`env -i`, `CICC_ENV_FILE` vacía): `manage.py check` termina con `ImproperlyConfigured: Falta la variable de entorno obligatoria DJANGO_SECRET_KEY…`.
- `grep -ril vercel .` (sin `.git`, `.venv`, `docs`): solo `.gitignore`, por la regla `.vercel/` que exige T01.
- **Demo desde cero** (copia temporal sin `demo.sqlite3`, `CICC_DEMO=1`): `migrate` y `seed_demo` funcionaron. `/login/` respondió 200, `ana` inició sesión y `/p/dashboard/` respondió 200 con «ENTORNO DEMO».
  - En modo producción (`QA_SQLITE=1` y variables ficticias), el dashboard no muestra «ENTORNO DEMO» ni «Datos ficticios».
  - `START-DEMO.ps1` no se ejecutó completo, porque crea un entorno virtual nuevo e instala dependencias desde Internet. Se probaron sus mismos pasos con el entorno existente.
- `.env` está ignorado (`.gitignore:6`) y `.env.example` está versionado.

Criterios de aceptación:
- [x] Sin variables, `check` falla nombrando la variable.
- [x] `CICC_DEMO=1` y `test hub` pasan completos.
- [x] `grep -ri vercel` solo encuentra `.gitignore`, que lo exige T01.
- [x] Sin `CICC_DEMO` no aparecen «ENTORNO DEMO» ni «Datos ficticios».
- [~] `START-DEMO.ps1` desde cero: se probaron sus pasos; la instalación desde Internet no se ejecutó.
- [x] `.env` ignorado y `.env.example` versionado.

### Preguntas para el arquitecto
- Ninguna.

### Observaciones
- **ID fijo en la plantilla de importación.** La plantilla trae fija la evaluación con ID 1, y la prueba de Excel falla en PostgreSQL dentro de la suite. Bloqueará el trabajo de PostgreSQL de T03 si no se corrige. Lo natural es corregirlo en T03 (CI) o en T07 (Excel), con la aprobación de Carlos.
- `seed_demo` usa la contraseña fija `DemoQA!2026`, y `START-DEMO.ps1` y el README la muestran. Es alcance de T06.
- `ARQUITECTURA.md` y `CAMBIOS-CICC.md` mencionan `QA_SQLITE` y `DEBUG=0` como antes (T11).

## T03 — Integración continua
- Fecha: 2026-11-21
- Modelo / herramienta: Claude Opus 5.5 (Claude Code)
- Rama y pull request: `tarea/T03-integracion-continua` en `CICC_original`, creada desde `tarea/T02-configuracion-por-entorno`. Commits `91e1462` y `f9f9d55`. Sin publicar (el proyecto no tiene remoto).
- Estado: En revisión

### Qué se hizo
- **`.github/workflows/ci.yml`** (`f9f9d55`): se ejecuta en `push` a `main` y en todo `pull_request`, con Python 3.12 y caché de pip. Es idéntico byte a byte al flujo de la T03 anterior del repositorio CICC.
  - `estilo`: `ruff check .` y `ruff format --check .`.
  - `pruebas-sqlite`: `CICC_DEMO=1` y los tres comandos de Django.
  - `pruebas-postgres`: servicio `postgres:16` con comprobación de salud, en modo producción (sin `CICC_DEMO`). Las `PG*`, `DJANGO_SECRET_KEY` y `CICC_ALLOWED_HOSTS=localhost,testserver` son ficticias y van escritas en el flujo. `POSTGRES_USER` es superusuario del servicio y puede crear la base de pruebas.
  - No usa secretos del repositorio.
- **Insignia** del flujo al inicio de `README.md`.
- **Paso 5, prueba que falla solo en PostgreSQL** (`91e1462`): `test_excel_and_backup` fallaba porque `excel_template()` escribía la evaluación con ID 1. El defecto estaba en el código: un usuario real tampoco podía importar la plantilla tal como se descarga si su primera evaluación no era la 1. Carlos autorizó corregirlo en esta tarea (21-11-2026). La fila de ejemplo ahora usa la primera evaluación existente. Hay dos pruebas nuevas en `hub/test_excel_template.py`. La prueba original no cambió.

### Desviaciones respecto a la tarea
- **Defecto corregido en lugar de bloquear la tarea:** el paso 5 pide anotarlo y bloquearla. Se corrigió con la autorización de Carlos.

### Verificación
- SQLite (`CICC_DEMO=1`): `System check identified no issues (0 silenced).` · `No changes detected` · `Ran 48 tests in 17.711s` · `OK`.
- PostgreSQL 16 local en modo producción (equivale al trabajo `pruebas-postgres`): `System check identified no issues (0 silenced).` · `No changes detected` · `Ran 48 tests in 19.398s` · `OK`. Antes de la corrección: `FAILED (failures=1)`.
- `estilo`: `ruff check .` → `All checks passed!` · `ruff format --check .` → `44 files already formatted`.
- **Control negativo:** se agregó `x=1;y=2` a `hub/context_processors.py`. `ruff format --check .` terminó con código 1 y `ruff check .` con código 1. Después se restauró el archivo.
- YAML: no hay PyYAML en el entorno. El archivo es idéntico (`cmp`) al flujo validado con PyYAML en la T03 anterior.

Criterios de aceptación:
- [ ] Los tres trabajos en verde en el pull request: **pendiente**. El proyecto no está en GitHub; se comprobó en local con los mismos comandos. El 19-11-2026 Carlos aceptó la evidencia local para la T03 anterior; queda a su criterio repetirlo aquí.
- [x] Sin secretos reales ni secretos del repositorio.
- [~] Un error de formato hace fallar `estilo`: comprobado en local.

### Preguntas para el arquitecto
- Ninguna.

### Observaciones
- La insignia apunta a `calhidalgo-git/CICC`. Mientras ese `main` tenga la versión `mejoras-cicc`, mostrará el estado de esa versión y no el de este proyecto.
