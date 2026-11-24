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

## T04 — Dividir vistas y plantillas
- Fecha: 2026-11-21
- Modelo / herramienta: Claude Opus 5.5 (Claude Code)
- Rama y pull request: `tarea/T04-dividir-vistas-y-plantillas` en `CICC_original`, creada desde `tarea/T03-integracion-continua`. Sin publicar.
- Estado: En revisión

### Qué se hizo
| Commit | Paso | Contenido |
|---|---|---|
| `61c9236` | 1 | Red de seguridad (`test_pages.py`) que pasaba con el código anterior. Cubre las 26 páginas de curso (`/qa/fundamentos` y sus 6 semanas, `/qa/avanzado` y sus 11, `/qa/certificacion` y sus 6 temas) con 200 autenticado, 302 a login y 404 fuera de rango. También un texto distintivo por cada una de las 26 secciones de `NAV` y los códigos 200/403/404/302 por sección para `ana`, `diego`, `lucia`, `admin` y sin sesión. |
| `6d43fd0` | 2–4 | `hub/urls.py` con todas las rutas (mismos patrones y nombres); `config/urls.py` solo con `admin/` e `include('hub.urls')`. `hub/permissions.py` con `NAV`, `GATES`, `allowed()` y `visible_nav(user)`; `hub.views` sigue exportando `NAV`. `hub/views.py` pasa a ser el paquete `hub/views/` con `common`, `pages`, `library`, `learning`, `exams` y `management`, según la sección 5. `hub/services/excel.py` contiene `workbook_response`, la plantilla, la importación y el reporte; es un traslado, sin cambios de lógica. |
| `806ee04` | 5 | Despachador: `page()` valida la sección (404) y el permiso (403) como antes y llama a una función por sección, que devuelve plantilla y contexto y consulta solo lo que usa. |
| `830f8fc` | 6 | Una plantilla por sección en `templates/pages/`, con sangría. El diseño común va en `pages/_section.html`, con bloques y sin condiciones por sección. Biblioteca, videoteca, enlaces, módulos y búsqueda comparten `pages/resources.html`. Se elimina `templates/page.html`. |
| `c4d25d1` | 6 | Valores fijos reemplazados por datos reales (ver abajo). Pruebas en `test_dashboard.py`. |
| `a368ee4` | 7 | Paquete `hub/tests/` con `test_core.py` (antes `hub/tests.py`), `test_cicc.py`, `test_config.py` y `test_pages.py`, más `test_excel_template.py` (T03) y `test_dashboard.py`. Solo cambian las importaciones. |
| `5f48d47` | 8 | Límite de consultas (`test_queries.py`) y optimizaciones sin cambiar lo que se muestra. |

Valores fijos del paso 6:
- `base.html`:
  - La insignia «02» de Evaluaciones muestra el número real. Viene del procesador de contexto y se calcula solo si la plantilla lo usa; el dashboard reutiliza su propio conteo.
  - El rol por defecto pasa de `'Administrador'` a `'Sin rol'`.
- Dashboard:
  - «12 lecciones» → total real (16 en la demo).
  - «Áreas de especialización 02» → número de áreas con recursos publicados, sin contar Transversal.
  - «Tu próximo desafío» → la primera evaluación que la persona no aprobó, o la primera. Muestra su título, minutos y número de preguntas; si no hay evaluaciones, un estado vacío.
- No se tocaron las comparaciones de títulos de recursos del dashboard ni de `resource()`; son de T05 y quedan marcadas con un comentario.

Optimizaciones del paso 8 (consultas máximas por sección, medidas con intentos y avance en la base):

| Sección | Antes | Después |
|---|---|---|
| Biblioteca y búsqueda (`ana`) | 39 (una por tarjeta, por `r.versions.count`) | 7; 10 con texto buscado |
| Glosario | 23 | 7 |
| Roles (`admin`) | 85 | 7 |
| Dashboard (`ana`) | 14 | 11 |
| Rutas | 10 | 8 |
| Máximo general | 85 | **11** (`ana` y `lucia`), 9 (`admin`) |

### Desviaciones respecto a la tarea
- **Áreas de especialización sin Transversal.** La ficha dice «áreas distintas con recursos publicados». El dato se presenta como especialización y viene con el texto «Mainframe + Distribuido», así que no se cuenta Transversal.
- **Descripción del próximo desafío.** El texto fijo («procesos batch, JCL y validación de datos») era de una evaluación concreta. Ahora es una frase general con el área de la evaluación recomendada.
- **El dashboard del participante cuenta preguntas.** El paso 6 exige mostrar el número real de preguntas, así que se usa `COUNT` dentro de la consulta de evaluaciones; nunca se leen las filas. Con usuarios y grupos pasa algo parecido: el menú lateral consulta los grupos y permisos del usuario de la sesión, nunca listados. `test_participant_dashboard_reads_only_its_own_data` lo comprueba.
- **Fragmentos en `templates/partials/`.** No se extrajo ninguno: tras la división no quedan fragmentos repetidos. El diseño común es `pages/_section.html`.
- **La tabla de Usuarios mantiene `'Administrador'`** como rol por defecto, porque la ficha solo nombra `base.html`.

### Verificación
- SQLite (`CICC_DEMO=1`): `System check identified no issues (0 silenced).` · `No changes detected` · `Ran 61 tests in 34.528s` · `OK`.
- PostgreSQL 16 local (modo producción, base de pruebas temporal): `System check identified no issues (0 silenced).` · `No changes detected` · `Ran 61 tests in 36.548s` · `OK`.
- `ruff check .` → `All checks passed!` · `ruff format --check .` → `58 files already formatted`.
- **Mismo HTML.** Antes de empezar se guardó el HTML de 67 direcciones para `ana`, `lucia` y `admin` (201 páginas: las 26 secciones, búsquedas, los 32 recursos, páginas de curso y resultados), con intentos y avance en la base. Se normalizaron los espacios, el token CSRF y las fechas.
  - Después de los pasos 2–4, 5 y 6 (división), las 201 páginas son idénticas.
  - Después del cambio de valores fijos solo cambian los 3 dashboards, con lo previsto: «16 lecciones», el título real de la evaluación y la frase general.
  - Después del paso 8 son idénticas al paso anterior.
- **Revisión visual manual a 1440 y 390 px: pendiente de Carlos.** No se tocaron CSS ni JavaScript, y el HTML es el mismo salvo esos valores del dashboard.

Criterios de aceptación:
- [x] `hub/views.py` y `templates/page.html` ya no existen.
- [x] Las pruebas anteriores pasan sin modificar sus aserciones; solo cambian sus importaciones.
- [x] Ninguna sección supera 12 consultas (máximo 11). El dashboard del participante no lista usuarios ni grupos, no consulta la auditoría y solo cuenta preguntas.
- [x] Las mismas URLs responden los mismos códigos para `ana`, `diego`, `lucia` y `admin` (red de seguridad escrita antes de los cambios).
- [x] No queda ninguno de los valores fijos del paso 6.
- [x] Revisión visual manual: Carlos la hizo el 21-11-2026 y dio su visto bueno.

### Preguntas para el arquitecto
- Ninguna. Las desviaciones están anotadas arriba.

### Observaciones
- Las vistas fuera de `/p/` (examen, resultados, recurso) no se midieron; el paso 8 solo cubre las secciones.
- La tabla de Usuarios sigue mostrando «Administrador» para quien no tiene grupo.

### Revisión de Carlos
- 21-11-2026: Carlos revisó la versión de T04 en la demo y la dio por buena («todo ok»).

## T05 — Cursos al modelo de datos
- Fecha: 2026-11-21
- Modelo / herramienta: Claude Opus 5.5 (Claude Code)
- Rama y pull request: `tarea/T05-cursos-al-modelo` en `CICC_original`, creada desde `tarea/T04-dividir-vistas-y-plantillas`. Commits `8fb453b`, `f61b92e` y `9f11fff`. Sin publicar.
- Estado: En revisión

### Punto de partida
- La versión de Carlos coincide con el contexto de la ficha: 23 plantillas de curso, tres portadas, `QA_WEEKS`, `QA_ADVANCED_WEEKS` y `hub/certification.py`. `resource()` y el dashboard decidían por el título del recurso. No hay tablas anteriores de cursos (`CourseWeek` o `WeekProgress`), así que no hay ediciones ni avance que trasladar.
- **Inventario del paso 2:** el HTML de las 23 lecciones y de las tres introducciones usa solo `h2`, `p`, `ul`, `li`, `strong` y `ol`, con `class` en dos `p` y un `h2`. Todo está en la lista de la ficha.
  - Las portadas tienen además `h1`, `article` y `small`. Se quedan en las plantillas Django que enmarcan la página: es el criterio que dio el arquitecto en la ronda anterior.

### Qué se hizo
| Commit | Contenido |
|---|---|
| `8fb453b` | `hub/content/courses/<slug>/` con `course.json`, `intro.html` y `NN.html` para `fundamentos-qa` (6), `qa-avanzado` (11) y `certificacion-requerimiento` (6). Son copia byte a byte de las plantillas; la introducción es el contenido del `article` de cada portada. Los títulos son los completos de las listas. Se agrega `nh3>=0.3,<0.4` (0.3.8, compatible con Python 3.12). |
| `f61b92e` | `LearningPath.slug` (único), `intro_html` y `position` (orden `position`, `id`); `Lesson.body_html` y restricción única (`path`, `position`). `save()` sanea con `nh3` y la lista de la ficha; `Lesson` deriva `body` del HTML. Las rutas nuevas sin slug lo reciben con sufijo. Migraciones 0004 (campos), 0005 (slugs sin duplicados, con los slugs acordados para los tres cursos, y renumeración de posiciones repetidas) y 0006 (únicos). `hub/services/courses.py` y comando `load_courses` (idempotente, `--force`), invocado desde `seed_demo`. Administrador: lecciones en línea y slug prellenado. |
| `9f11fff` | `/rutas/<slug>/` y `/rutas/<slug>/<position>/` en `hub/views/learning.py`, con plantillas `templates/learning/` que reutilizan las clases de las portadas y semanas. Redirecciones 301 desde las seis rutas `/qa/...`; fuera de rango, 404. `complete` acepta `next` validado con `url_has_allowed_host_and_scheme` y por defecto vuelve a la lección. `resource()` siempre muestra el recurso. El dashboard muestra los títulos reales y el bloque «Cursos» con las rutas por `position`. Búsqueda, Rutas y Lecciones enlazan a `/rutas/…`. Se eliminan `QA_WEEKS`, `QA_ADVANCED_WEEKS`, `hub/certification.py`, las vistas antiguas y las nueve plantillas de la ficha. |

### Desviaciones respecto a la tarea
- **Tres migraciones en lugar de una.** En PostgreSQL no conviene modificar filas y alterar la misma tabla en una transacción. La 0005 solo tiene datos.
- **Reversibilidad.** Se revierten sin error, pero se pierden `slug`, `position`, `intro_html` y `body_html`. Al volver a aplicarlas, los tres cursos recuperan su slug y `load_courses --force` repone el contenido. Las ediciones hechas a mano en el administrador después de T05 no se recuperan.
- **Mis lecciones (`/p/lessons/`).** Ahora se ordena por ruta y posición; antes mezclaba lecciones de todas las rutas. Las lecciones de curso muestran un extracto de 40 palabras y «Abrir la lección». Su formulario envía `next` para volver al mismo punto de la lista.
- **Descripción de las rutas.** Fundamentos usa el subtítulo de su portada. Las otras dos portadas no tenían, así que se usa la primera oración de su introducción, sin cambios.
- **CourseRoutes** (`test_pages.py`) espera 301 y el destino correcto, como pide el paso 10.

### Verificación
- SQLite (`CICC_DEMO=1`): `System check identified no issues (0 silenced).` · `No changes detected` · `Ran 80 tests` · `OK`.
- PostgreSQL 16 local (modo producción, base de pruebas temporal): `System check identified no issues (0 silenced).` · `No changes detected` · `Ran 80 tests in 42.156s` · `OK`.
- `ruff check .` → `All checks passed!` · `ruff format --check .` → sin hallazgos.
- `grep -rln "Guía de pruebas batch\|Checklist de pruebas\|Introducción a DB2" hub templates`: solo `seed_demo.py`, `tests/test_core.py` y `tests/test_courses.py`.
- No quedan las plantillas de cursos: `templates/` contiene `base`, `components`, `exam`, `learning/`, `login`, `notice`, `pages/`, `resource` y `result`.
- **Copia de `demo.sqlite3` con datos** (directorio temporal):
  - Antes se agregó un avance y una lección con posición repetida: 3 rutas, 17 lecciones y 1 avance.
  - Después de `migrate` (0004–0006) y `load_courses`: 6 rutas (`fundamentos-qa` 1, `qa-avanzado` 2, `certificacion-requerimiento` 3) y 40 lecciones. El avance se conserva. Las posiciones repetidas quedaron 1–4 en el mismo orden.
  - Una segunda carga no creó nada. Revertir a 0003 y volver a migrar terminó sin error.
- `hub/tests/test_migrations.py` repite la migración con títulos de ruta y posiciones repetidas, y pasa en SQLite y PostgreSQL.
- **Comparación visual de una lección de cada curso: pendiente de Carlos.** El texto de cada lección coincide con su archivo original (`test_each_lesson_text_matches_its_original_file`).

### Preguntas para el arquitecto
- Ninguna.

### Observaciones
- El dashboard ordenaba las rutas con una anotación que ignoraba `Meta.ordering`; ahora el orden es explícito (`position`, `id`).
- `ARQUITECTURA.md` todavía describe los cursos como plantillas (T11).

### Decisión de Carlos sobre D4
- 21-11-2026: Carlos vetó la consecuencia visible de D4. Los recursos «Guía de pruebas batch y JCL», «Checklist de pruebas de API REST» e «Introducción a DB2 para QA» deben verse como en su versión: con el nombre del curso y abriendo su teoría.
- Para cumplirlo sin depender del título (D6) se agregó `Resource.learning_path` (migración 0007, reversible), que se edita en el administrador. `seed_demo` lo asigna a esos tres recursos. La ficha `/resource/<pk>/` dibuja la portada de la ruta en la misma dirección (200, como antes) y el dashboard usa `display_title`. Commit `63b4f87`.
- La prueba original `test_all_admin_screens` pasa sin cambios. En `test_courses.py`, `test_course_resources_show_their_own_page` se reemplazó por `test_course_resources_open_their_course` y `test_renaming_a_resource_does_not_change_where_it_opens`.
- Verificación: SQLite y PostgreSQL `Ran 81 tests` · `OK`. `ruff check` y `ruff format --check` sin hallazgos. `makemigrations --check` → `No changes detected`.
- Pregunta para el arquitecto: registrar este veto de Carlos en D4.

## T12 — Una página con teoría para cada opción del menú
- Fecha: 2026-11-22
- Modelo / herramienta: Claude Opus 5.5 (Claude Code)
- Rama y pull request: `tarea/T12-paginas-del-menu` en `CICC_original`, creada desde `tarea/T05-cursos-al-modelo` (`beec6b6`), en el worktree `CICC-local\original\T12`. Commits `88048ed`, `3bf28e5`, `e7526ea` y `9bb57b9`. Sin publicar.
- Estado: En revisión

### Punto de partida
- Tarea pedida por Carlos el 22-11-2026, antes que T06 y T07. La carpeta de Carlos (`CICC_original`, rama T05) estaba limpia, sin stash y sin `.env`; `demo.sqlite3` no está versionada. No se cambió de rama ni se tocó nada allí.
- Ya existía el respaldo JSON (`/backup/`), pero no una restauración propia: se restaura con `manage.py loaddata`.

### Qué se hizo
| Commit | Contenido |
|---|---|
| `88048ed` | Ficha `tareas/T12-paginas-del-menu.md` y T12 en `PLAN.md`. |
| `3bf28e5` | `SectionPage` (slug único, título, `intro_html`, `intro` en texto plano, origen, fecha y autor de la última edición) y `SectionBlock` (título, `body_html`, `body`, posición). Migraciones 0008 (tablas) y 0009 (una página vacía por cada una de las 26 entradas de `NAV`; al revertir quita solo las vacías). `hub/services/pages.py` y comando `load_pages` (crea las páginas que falten y carga `hub/content/pages/<slug>.md` o `.html`; `--force`). Administrador con bloques en línea; un receptor `pre_save` vuelve a sanear el HTML de páginas, bloques, rutas y lecciones al restaurar con `loaddata`. `seed_demo` da `view_sectionpage` y `change_sectionpage` al Editor (el Administrador ya tiene todos) y ejecuta `load_pages`. Carpeta `hub/content/pages/` con `README.md` y `_ejemplo.md` ficticio. |
| `e7526ea` | `pages/_section.html` dibuja la teoría arriba del contenido de cada sección, o «Contenido pendiente», con «Editar contenido» para quien tiene el permiso. La Búsqueda global agrega «Teoría de las secciones». El respaldo incluye las dos tablas. Seis reglas CSS nuevas en `hub.css` (versión del enlace actualizada). |
| `9bb57b9` | `hub/tests/test_section_pages.py`: 30 pruebas. |

### Desviaciones respecto a la tarea
- **Cómo se protege una edición manual.** Guardar en el administrador marca la página con origen «administrador»; `load_pages` no la toca sin `--force`. Una página cargada desde archivo se actualiza si el archivo cambió (se compara un hash) y no se vuelve a escribir si no cambió.
- **Un único permiso.** Los bloques en línea usan `hub.change_sectionpage`, no permisos propios. En el administrador las páginas no se crean ni se borran: hay una por opción del menú.
- **Sin restricción única en (página, posición)**, para poder intercambiar posiciones en una sola edición del administrador. El orden es `position`, `id`.
- **Markdown propio y limitado** (párrafos, `###`, listas, negrita, cursiva, código y enlaces), porque la sección 8 no permite dependencias nuevas. El HTML escrito dentro de un `.md` se muestra como texto.
- **El archivo de ejemplo empieza con `_`** y no se carga, para que la demo no muestre texto ficticio como si fuera teoría.
- **Búsqueda:** solo muestra teoría de secciones que la persona puede abrir, y no muestra páginas vacías aunque coincida su título.
- **Restauración:** no había un comando de restauración; el saneado se aplica a cualquier `loaddata`.

### Verificación
- SQLite (`CICC_DEMO=1`): `System check identified no issues (0 silenced).` · `No changes detected` · `Ran 111 tests in 69.941s` · `OK`.
- PostgreSQL 16 local (`Iniciar-PostgreSQL.ps1`, modo producción, base temporal `cicc_t12_tmp` creada y borrada): `System check identified no issues (0 silenced).` · `No changes detected` · `Found 111 test(s)` · `OK`.
- `ruff check .` → `All checks passed!` · `ruff format --check .` → `67 files already formatted`.
- **Copia de `demo.sqlite3`** en el worktree: antes 6 rutas, 39 lecciones, 4 usuarios y 32 recursos. `migrate` aplicó 0008 y 0009: 26 páginas y los mismos datos. `load_pages` dos veces: `Páginas creadas: 0; cargadas desde archivo: 0`. `migrate hub 0007` revirtió sin error (la tabla desaparece) y volver a migrar dejó 26 páginas. El hash SHA-256 del `demo.sqlite3` original fue el mismo antes y después (`333f4566…53ed09`).
- **Consultas:** el máximo por sección sigue en el límite de T04: 12, en `lucia /p/search/?q=prueba` (+1 por la teoría y +1 por buscarla). `test_queries` pasa sin cambios.
- **HTML renderizado** (cliente de pruebas sobre la copia de la demo): el dashboard con el ejemplo cargado muestra el panel de teoría arriba del bloque principal, y el glosario muestra «Contenido pendiente · Editar contenido ↗» para `diego`. Después se vació otra vez el ejemplo.
- **Revisión visual en el navegador: pendiente de Carlos.** La extensión de Chrome no pudo abrir el servidor local.

### Preguntas para el arquitecto
- Ninguna.

### Observaciones
- La búsqueda con texto quedó justo en el límite de 12 consultas. Una sección nueva que consulte más tendrá que optimizar.
- Las tablas de respaldo guardan `updated_by` como id de usuario, igual que `Audit`, `Progress` y `Attempt`; restaurar en una base sin esos usuarios falla. Es de T10.
- En una base que ya existía, el grupo Editor recibe el permiso nuevo al volver a ejecutar `seed_demo` (solo demo) o, más adelante, `bootstrap_roles` (T06).

## T02 — Correcciones de la revisión de Codex (22-11-2026)
- Fecha: 2026-11-22
- Modelo / herramienta: Claude Opus 5.5 (Claude Code)
- Rama y pull request: `tarea/T02-configuracion-por-entorno`, worktree `CICC-local\original\T02`. Commit `53128a5`. Sin publicar.
- Estado: En revisión

### Qué se corrigió
Hallazgos de `revision-codex-original-22nov.md`, según el encargo de Carlos del 22-11-2026:
- **Alta: claves publicadas.** `config/settings.py` rechaza en producción, además de las tres de antes:
  - el ejemplo literal del README de T01 (`README.md:25`), `reemplazar-con-un-secreto-aleatorio`;
  - la clave fija que usaban estas pruebas;
  - la clave fija del flujo de CI de T03.
- **Claves efímeras.** `hub/test_config.py` genera la clave de producción con `secrets.token_urlsafe(50)` en cada ejecución. El flujo de CI se corrige en T03.
- **Pruebas nuevas.**
  - El ejemplo histórico exacto se rechaza con PostgreSQL y con `QA_SQLITE=1`.
  - Las dos claves fijas de pruebas y de CI se rechazan.
  - Una clave publicada con espacios alrededor también se rechaza.
  - La clave de las pruebas no es ninguna de las publicadas.
- **Media: pantalla de acceso.** En `templates/login.html`, el bloque «Demostración: admin / …», las otras cuentas, «Solo datos ficticios» y «Credenciales exclusivas para uso local» solo aparecen con `cicc_demo`. Nuevas pruebas `LoginScreen`: `/login/` sin sesión en producción (200, sin la ayuda), con error de acceso y en modo demo (con la ayuda).
- **T01 aprobada.** Por decisión expresa de Carlos (22-11-2026), T01 queda `Hecha` en `PLAN.md`.

### Desviaciones respecto a la tarea
- Ninguna nueva. La protección de `seed_demo` sigue siendo de T06.

### Verificación
Las cinco pruebas nuevas de claves y acceso fallan con la configuración y la plantilla anteriores (`FAILED (failures=5)`) y pasan con la corrección.
- SQLite (`CICC_DEMO=1`): `System check identified no issues (0 silenced).` · `No changes detected` · `Ran 53 tests in 22.179s` · `OK`.
- PostgreSQL 16 local (`Iniciar-PostgreSQL.ps1`, modo producción, clave aleatoria, base temporal `cicc_corr_t02` creada y borrada): `System check identified no issues (0 silenced).` · `No changes detected` · `Ran 53 tests in 22.476s` · `FAILED (failures=1)`. Falla solo `test_excel_and_backup`: es la falla previa del ID fijo de la plantilla Excel, anotada en la entrada original y corregida en T03.
- `ruff check .` → `All checks passed!` · `ruff format --check .` → `43 files already formatted`.

### Preguntas para el arquitecto
- Ninguna.

## T03 — Correcciones de la revisión de Codex (22-11-2026)
- Fecha: 2026-11-22
- Modelo / herramienta: Claude Opus 5.5 (Claude Code)
- Rama y pull request: `tarea/T03-integracion-continua`, worktree `CICC-local\original\T03`. Merge de T02 `eccc860` y commit `5a757fa`. Sin publicar.
- Estado: En revisión

### Qué se corrigió
- **Merge de T02** con sus correcciones (claves publicadas y pantalla de acceso). En `BITACORA.md` se conservaron las entradas de ambos lados.
- **Insignia.** Se retiró del `README.md` la insignia que apuntaba a `calhidalgo-git/CICC`. En su lugar, una línea explica que el flujo existe, que el proyecto aún no tiene un remoto aprobado y que la evidencia queda en la bitácora.
- **Clave de CI.** `DJANGO_SECRET_KEY` ya no está escrita en `.github/workflows/ci.yml`. El paso «Clave secreta efímera» del trabajo `pruebas-postgres` la genera con `secrets.token_urlsafe(64)`, la oculta con `::add-mask::` y la exporta por `GITHUB_ENV`. La clave fija anterior queda rechazada en producción desde T02.
- **Plantilla Excel.** Se conserva la corrección de `91e1462`. `test_excel_and_backup` y las dos pruebas de `hub/test_excel_template.py` pasan en PostgreSQL.
- **Pruebas nuevas** en `hub/test_config.py`. El flujo no puede contener `DJANGO_SECRET_KEY:` ni las claves publicadas, y debe generarla. El README no enlaza insignias.

### Verificación
- El YAML se cargó con PyYAML (`uv run -p 3.12 --with pyyaml`, sin red). Tiene los trabajos `estilo`, `pruebas-sqlite` y `pruebas-postgres`. El de PostgreSQL ya no tiene `DJANGO_SECRET_KEY` en `env` y sí el paso nuevo antes de `check`. Las tres líneas del paso se ejecutaron en bash con un `GITHUB_ENV` temporal y dejaron una clave de 86 caracteres.
- SQLite (`CICC_DEMO=1`): `System check identified no issues (0 silenced).` · `No changes detected` · `Ran 57 tests in 19.858s` · `OK`.
- PostgreSQL 16 local (modo producción, clave aleatoria, base temporal `cicc_corr_t03` creada y borrada): `System check identified no issues (0 silenced).` · `No changes detected` · `Ran 57 tests in 20.412s` · `OK`.
- `ruff check .` → `All checks passed!` · `ruff format --check .` → `44 files already formatted`.
- Sigue pendiente la ejecución en GitHub: el proyecto no tiene remoto. Queda a criterio de Carlos aceptar la evidencia local.

### Preguntas para el arquitecto
- Ninguna.

### Decisión de Carlos
- 22-11-2026: Carlos acepta la evidencia local (las pruebas ejecutadas en su PC) en lugar de los tres trabajos en verde en el pull request de GitHub, porque el proyecto no tiene remoto. Con esto se da por cumplido ese criterio de aceptación.
- 22-11-2026: Carlos aprobó T03, que pasa a `Hecha`.

## T04 — Correcciones de la revisión de Codex (22-11-2026)
- Fecha: 2026-11-22
- Modelo / herramienta: Claude Opus 5.5 (Claude Code)
- Rama y pull request: `tarea/T04-dividir-vistas-y-plantillas`, worktree `CICC-local\original\T04`. Merge de T03 `e6920c4` y commit `9a5cb18`. Sin publicar.
- Estado: En revisión

### Qué se corrigió
- **Merge de T03** con las correcciones de T02 y T03. En `BITACORA.md` se conservaron las entradas de ambos lados.
- **Áreas del panel (decisión 2 de Carlos, 22-11-2026).** El contador cuenta las tres áreas con recursos publicados: Mainframe, Distribuido y Transversal. Se retira la desviación «Áreas de especialización sin Transversal» de la entrada original.
  - `hub/views/pages.py` usa una sola consulta agrupada por área. Da el total de recursos y las áreas con publicados, en el orden de las opciones del modelo, así que no suma consultas.
  - La línea bajo el número decía «Mainframe + Distribuido», un texto fijo. Ahora nombra las áreas contadas («Mainframe + Distribuido + Transversal» en la demo), para que no contradiga el número.
  - `hub/tests/test_dashboard.py` espera 3 con la demo, 2 al despublicar Distribuido y 1 al despublicar también Transversal.

### Excepción registrada: conteo de preguntas y datos de la sesión
La ficha prohíbe que el dashboard del participante consulte usuarios, grupos o auditoría y que lea preguntas. Por eso queda escrita esta excepción, que ya existía en la implementación y en `hub/tests/test_queries.py` (`test_participant_dashboard_reads_only_its_own_data`):
- **Preguntas.** Solo se cuentan con `COUNT("hub_question"."id")` dentro de la consulta de evaluaciones, para el número real del próximo desafío que exige el paso 6. Ninguna consulta hace `FROM "hub_question"` ni lee enunciados.
- **Usuario y grupos.** Solo se leen el usuario de la sesión, sus grupos y sus permisos (filtrados por su id), que usan la autenticación y el menú lateral. Nunca se listan otros usuarios ni grupos.
- **Auditoría.** No se consulta.

### Verificación
- SQLite (`CICC_DEMO=1`): `System check identified no issues (0 silenced).` · `No changes detected` · `Ran 70 tests in 33.271s` · `OK`.
- PostgreSQL 16 local (modo producción, clave aleatoria, base temporal `cicc_corr_t04` creada y borrada): `System check identified no issues (0 silenced).` · `No changes detected` · `Ran 70 tests in 38.892s` · `OK`.
- `ruff check .` → `All checks passed!` · `ruff format --check .` → `58 files already formatted`.
- `test_queries` pasa sin cambios: ninguna sección supera 12 consultas y el dashboard del participante cumple la excepción anterior.
- Cambio visible: en el panel, «02» pasa a «03» y la línea bajo el número nombra las tres áreas. Falta que Carlos lo vea.

### Preguntas para el arquitecto
- Ninguna.

## T05 — Correcciones de la revisión de Codex (22-11-2026)
- Fecha: 2026-11-22
- Modelo / herramienta: Claude Opus 5.5 (Claude Code)
- Rama y pull request: `tarea/T05-cursos-al-modelo`. El trabajo se hizo en el worktree `CICC-local\original\T05`, con HEAD separado, y la rama se adelantó desde la carpeta de Carlos con `merge --ff-only`. Merge de T04 `0b42cc3` y commit `130b628`. Sin publicar.
- Estado: En revisión

### Qué se corrigió
- **Merge de T04** con las correcciones de T02 a T04.
  - En `hub/views/pages.py` se unieron el contador de 3 áreas y el orden y `select_related` de T05.
  - En `BITACORA.md` se conservaron las entradas de ambos lados y la decisión de Carlos sobre D4 sigue dentro de la entrada de T05.
- **Alta: identidad reservada de los tres cursos.** Los slugs `fundamentos-qa`, `qa-avanzado` y `certificacion-requerimiento`, leídos de `hub/content/courses/*/course.json`, solo los usa `load_courses`.
  - `LearningPath.save()` da a una ruta nueva un slug no reservado: una ruta local «Fundamentos QA» queda en `fundamentos-qa-2`. También rechaza que otra ruta tome un slug reservado.
  - `LearningPath.clean()` muestra el error en el administrador.
  - La migración 0005 ya no asigna el slug oficial solo por el título. Lo hace únicamente si la ruta conserva el título y todas las lecciones del curso, con su posición y su título, que es lo que ocurre al volver a aplicarla tras revertir. Una ruta local con el mismo nombre recibe otro slug.
  - Como no hay cambios de esquema, no hace falta una migración nueva. Las bases ya migradas no cambian.
- **Media: vínculos históricos (veto de Carlos a D4).** Cada `course.json` lista en `legacy_resource_titles` los títulos que abrían ese curso en T04: los tres recursos históricos y las variantes que reconocía `resource()`.
  - `load_courses` vincula esos recursos al crear el curso o con `--force`. Solo toca los recursos sin ruta asignada, así que respeta una ruta elegida en el administrador y nunca vincula con una ruta local.
  - Una carga normal no deshace una desvinculación manual. El comando informa los recursos vinculados.
- **Media: respaldo JSON de T04.** `loaddata` admite directamente el archivo de T04, mediante receptores `pre_save` con `raw`:
  - la ruta sin slug recibe uno no reservado;
  - una lección con la posición repetida pasa al final de su ruta;
  - si una fila del respaldo ocuparía un curso oficial que ya existe, la restauración se detiene sin aplicar nada.
  - Hay que restaurar en una base vacía de contenido y ejecutar después `load_courses`. Está documentado en `README.md`.
- **Media: recuperación tras revertir.** Está documentada en `README.md`: qué se pierde al volver a 0003, cómo `load_courses --force` repone el contenido y los vínculos, y cómo un respaldo JSON hecho antes de revertir conserva las ediciones manuales.
- **Baja: rangos históricos.** `/qa/fundamentos/semana/<n>/`, `/qa/avanzado/semana/<n>/` y `/qa/certificacion/tema/<n>/` responden 404 fuera de 1–6, 1–11 y 1–6, aunque la ruta tenga más lecciones. Las ampliaciones se abren en `/rutas/<slug>/<n>/`.
- **Pruebas.**
  - `hub/tests/test_course_identity.py` tiene 13 pruebas: identidad reservada, administrador, carga normal y `--force` con avance, vínculos, rangos antiguos y respaldo de T04 con varias rutas y avance, incluido el rechazo sin cambios.
  - `hub/tests/test_migrations.py` agrega 3 pruebas de actualización real desde 0003.
  - Con el código anterior, las pruebas nuevas dan `FAILED (failures=4, errors=1)`.

### Desviaciones respecto a la tarea
- **Cambio en una prueba existente.** En `test_existing_paths_lessons_and_progress_survive`, una ruta titulada «QA Avanzado y Especialización» y sin lecciones esperaba el slug `qa-avanzado`. Ahora espera `qa-avanzado-y-especializacion`: es una ruta local y el encargo pide que no tome la identidad del curso oficial. El resto de las aserciones no cambió.
- **Migración 0005 modificada.** Solo cambia su lógica de datos. Las bases que ya la aplicaron no se ven afectadas.

### Verificación
- SQLite (`CICC_DEMO=1`): `System check identified no issues (0 silenced).` · `No changes detected` · `Ran 106 tests in 56.214s` · `OK`.
- PostgreSQL 16 local (modo producción, clave aleatoria, base temporal `cicc_corr_t05` creada y borrada): `System check identified no issues (0 silenced).` · `No changes detected` · `Ran 106 tests in 65.266s` · `OK`.
- `ruff check .` → `All checks passed!` · `ruff format --check .` → `62 files already formatted`.
- **Escenarios con datos reales** (copias en el directorio temporal; el `demo.sqlite3` de Carlos conservó su huella `333f4566e875e09a` antes y después):
  1. **Actualización.** Base histórica de T01 (0003) con el código de T04, más una ruta local «Fundamentos QA», su lección «Mi lección local» completada y otro avance. `migrate` y `load_courses` dieron `Rutas creadas: 3; lecciones creadas: 23; reescritas: 0; recursos vinculados: 3`, con 7 rutas y 40 lecciones. La local quedó en `fundamentos-qa-2` con su lección y su avance, y la oficial en `fundamentos-qa` con 6. Los tres recursos históricos responden 200 y abren su ruta. Con `--force`, la ruta local y los avances no cambiaron.
  2. **Respaldo de T04.** El JSON exportado por `/backup/` con T04 tenía 76 objetos. Se restauró con `loaddata` en una base T05 vacía de contenido, con las 4 cuentas: `Installed 76 object(s)`. Se restauraron todos los objetos por modelo, con los avances idénticos. Después, `load_courses` agregó los tres cursos y vinculó los tres recursos.
  3. **Revertir.** En una copia de la demo de Carlos (0007: 6 rutas, 39 lecciones, 23 lecciones y 3 introducciones con HTML, 3 recursos vinculados) se ejecutó `migrate hub 0003` y luego `migrate`. Los tres cursos recuperaron su slug, sin duplicados, y el HTML y los vínculos quedaron en 0. `load_courses` sin `--force` no los repone. `load_courses --force` repuso 23 y 3 HTML y 3 vínculos.
  4. **Recuperar ediciones.** Con una edición manual y un respaldo JSON de T05 hecho antes de revertir, el ciclo revertir, migrar y `loaddata` (`Installed 98 object(s)`) devolvió la edición, el HTML y los vínculos.

### Preguntas para el arquitecto
- Sigue abierta la de la entrada original: registrar en D4 el veto de Carlos.

### Observaciones
- Una base que ya aplicó el T05 anterior con una ruta local llamada como un curso oficial tiene esa ruta mezclada con el curso. No se puede separar de forma automática. No hay indicios de que ocurra en la demo de Carlos: sus 6 rutas son las 3 de la demo y las 3 oficiales.
- Si se edita el título de una lección oficial y después se revierte a 0003, al volver a migrar esa ruta se trata como local y `load_courses` crea el curso de nuevo. Lo indica el README: conviene hacer un respaldo antes de revertir.

## T12 — Integración de las correcciones de T02 a T05 (22-11-2026)
- Fecha: 2026-11-22
- Modelo / herramienta: Claude Opus 5.5 (Claude Code)
- Rama y pull request: `tarea/T12-paginas-del-menu`, worktree `CICC-local\original\T12`. Merge de T05 `758c387`. Sin publicar.
- Estado: En revisión

### Qué se hizo
- **Merge de T05** con las correcciones de T02 a T05, sin reescribir la historia.
- **Conflicto en `hub/models.py`.** `LearningPath.save()` reserva los slugs oficiales (T05) y sanea con `clean_learning_path` (T12). Los receptores de restauración de T05 (`restore_learning_path`, `restore_lesson`) conviven con `sanitize_restored_html` de T12.
- **Conflicto en `BITACORA.md`.** Se conservaron las entradas de ambos lados: la de T12 y, a continuación, las correcciones de T02 a T05.
- **`PLAN.md`** se fusionó sin conflicto: T01 está `Hecha` y T12 sigue antes que T06 y T07 (decisión 3 de Carlos).

### Verificación
- SQLite (`CICC_DEMO=1`): `System check identified no issues (0 silenced).` · `No changes detected` · `Ran 136 tests in 81.204s` · `OK`.
- PostgreSQL 16 local (modo producción, clave aleatoria, base temporal `cicc_corr_t12` creada y borrada): `System check identified no issues (0 silenced).` · `No changes detected` · `Ran 136 tests in 89.829s` · `OK`.
- `ruff check .` → `All checks passed!` · `ruff format --check .` → `68 files already formatted`.
- **Páginas de T12.** Se usó un worktree temporal con una copia del `demo.sqlite3` de esta carpeta. Su huella `2adcff98932634ed` no cambió.
  - `migrate` no tenía nada que aplicar. `load_courses` y `load_pages` no crearon ni cambiaron nada.
  - Las 26 secciones `/p/` respondieron 200 como `admin`, con 26 páginas de sección. El dashboard muestra «Contenido pendiente» y las tres áreas.
  - Los tres recursos históricos abren su curso.
  - `/qa/fundamentos/semana/6/` responde 301 y `/semana/7/` responde 404.
  - La pantalla de acceso de la demo muestra la ayuda.

### Preguntas para el arquitecto
- Ninguna.

## Decisiones de Carlos — 22-11-2026
- **T02, T03 y T04 aprobadas.** Carlos las aprobó de forma expresa tras la segunda revisión de Codex (`revision-codex-original-2.md`). Pasan a `Hecha` en `PLAN.md`. Carlos escribió «T02, T02 y T04»: la segunda «T02» se entiende como T03, que era la que esperaba su aprobación.
- **T03: evidencia local.** Carlos acepta las pruebas ejecutadas en su PC en lugar de los tres trabajos en verde en un pull request de GitHub, porque el proyecto no tiene remoto. Queda anotado también en la entrada de T03.
- El código de T02, T03 y T04 no cambió. Estas notas se llevan a las ramas T05 y T12.

## T05 — Correcciones de la segunda revisión de Codex (22-11-2026)
- Fecha: 2026-11-22
- Modelo / herramienta: Claude Opus 5.5 (Claude Code)
- Rama y pull request: `tarea/T05-cursos-al-modelo`, en la carpeta de Carlos. Commit de código `5ca5f83`. Sin publicar.
- Estado: En revisión

### Qué se corrigió
Hallazgos de `revision-codex-original-2.md`:
- **Alta: una copia local de un curso oficial se confundía con él.** La migración 0005 reconocía el curso por el título y por los títulos y posiciones de sus lecciones. Una ruta local con esos mismos datos, pero con sus propios textos, tomaba el slug oficial y `load_courses --force` borraba sus textos.
  - Ahora una ruta recupera el slug oficial solo si conserva todo lo que `load_courses --force` reescribiría: título, área y descripción del curso, y en cada lección oficial la posición, el título y el texto (`body`, el texto plano que guarda `Lesson.save()`).
  - Si coincide en todo, tomarla por oficial no cambia nada de lo que contiene. Si no coincide, los datos no permiten saber de dónde viene: queda como ruta local, con otra dirección, su texto y su avance, y `load_courses` crea el curso oficial aparte.
  - Vale para la primera actualización desde T04 y para la vuelta después de revertir.
  - Se compara también cuando hay posiciones repetidas, que antes de T05 eran posibles.
- **Media: vínculos de las instalaciones con la T05 anterior (`beec6b6`).** Nueva opción `load_courses --relink`.
  - Solo vincula con su curso oficial los recursos históricos (`legacy_resource_titles`) que no abren ninguna ruta.
  - No crea ni reescribe rutas ni lecciones, y no cambia un recurso que ya abre otra ruta.
  - No se puede combinar con `--force`. La carga normal sigue sin tocar los vínculos de un curso que ya existe, así que respeta una desvinculación manual.
- **Media: dirección de un curso oficial.**
  - `LearningPath.clean()` y `save()` rechazan el cambio de slug de una ruta guardada con un slug oficial.
  - En el administrador, el slug de un curso oficial es de solo lectura y no se rellena desde el título. Las rutas locales pueden seguir cambiando el suyo.
- **README.** Se explica `--relink`, que la dirección oficial no se puede cambiar y cómo se reconoce ahora un curso al volver a migrar.
- **Pruebas nuevas (6) y una ajustada.**
  - `test_migrations.LocalCopyOfAnOfficialCourse` prueba la primera actualización desde 0003 y la vuelta tras revertir. La copia local tiene los seis títulos en orden, seis textos propios y la tercera lección completada; en el caso de la reversión se creó antes que el curso oficial, así que tiene el número interno menor. Tras migrar, con la carga normal y con `--force`, comprueba la dirección, la descripción, los seis textos, la lección completada y su texto, y que el curso oficial tiene sus propios textos.
  - `test_course_identity.OfficialAddressIsFixed` prueba el modelo y el formulario de edición del administrador. El campo no aparece, el envío con otra dirección guarda la descripción pero conserva `fundamentos-qa`, la dirección sigue en 200 con el avance y la carga no crea un segundo curso. También comprueba que una ruta local sí puede cambiar su dirección.
  - `HistoricalResources` prueba `--relink` sobre una instalación con la T05 anterior. Hay tres recursos sin vínculo, uno elegido para una ruta local, una descripción y una lección editadas y una lección oficial borrada. Vincula 2 y respeta el resto. Una segunda ejecución vincula 0. Otra prueba comprueba que no se combina con `--force`.
  - Con el código anterior, las pruebas nuevas dan `FAILED (failures=4, errors=1)`.

### Desviaciones respecto a la tarea
- **Prueba existente ajustada.** En `test_reapplying_after_a_revert_recognises_the_official_course`, el curso revertido se creaba con textos de relleno (`body='b'`, descripción `'d'`). Ahora se crea con el área, la descripción y el texto reales del curso, que es lo que deja una reversión. Con la regla nueva, una ruta con textos de relleno es local. Las aserciones no cambiaron.
- **Migración 0005 modificada otra vez.** Solo cambia su lógica de datos. Usa `sanitize_html` y `html_to_text` de `hub/services/courses.py` para calcular el texto esperado de cada lección.
- **Un curso oficial editado y revertido queda local.** Si se cambió la descripción o el texto de una lección oficial y después se revierte a 0003, al volver a migrar esa ruta queda local con sus ediciones, y `load_courses` crea el curso de nuevo. Es la consecuencia de no adivinar el origen. Está en el README.

### Verificación
- SQLite (`CICC_DEMO=1`): `System check identified no issues (0 silenced).` · `No changes detected` · `Ran 113 tests in 51.458s` · `OK`.
- PostgreSQL 16 local (`Iniciar-PostgreSQL.ps1`; modo producción, clave aleatoria, base temporal `cicc_corr2_t05` creada y borrada): `System check identified no issues (0 silenced).` · `No changes detected` · `Ran 113 tests in 58.117s` · `OK`.
- `ruff check .` → `All checks passed!` · `ruff format --check .` → `62 files already formatted` (Ruff 0.17.6).
- **Copia de la demo de Carlos** (en el directorio temporal; el `demo.sqlite3` conservó su huella `333f4566…53ed09`):
  - Partida: 6 rutas, 39 lecciones, 23 con HTML y 3 vínculos.
  - Después de `migrate hub 0003` y `migrate`, los tres cursos recuperaron `fundamentos-qa`, `qa-avanzado` y `certificacion-requerimiento` con los mismos números internos 4, 5 y 6, sin duplicados.
  - `load_courses` → `Rutas creadas: 0; lecciones creadas: 0; reescritas: 0; recursos vinculados: 0`.
  - `load_courses --relink` → `recursos vinculados: 3`.
  - `load_courses --force` → `reescritas: 26`. Quedaron 23 lecciones con HTML y 3 vínculos.

### Preguntas para el arquitecto
- Sigue abierta la de la entrada original: registrar en D4 el veto de Carlos.

### Observaciones
- `--relink` no distingue un recurso histórico desvinculado a propósito de uno que perdió el vínculo en la T05 anterior, porque ambos están vacíos. Por eso es una opción expresa y el README lo advierte.

## T12 — Correcciones de la segunda revisión de Codex (22-11-2026)
- Fecha: 2026-11-22
- Modelo / herramienta: Claude Opus 5.5 (Claude Code)
- Rama y pull request: `tarea/T12-paginas-del-menu`, worktree `CICC-local\original\T12`. Merge de T05 `25b8ec8` y commit `262f93d`. Sin publicar.
- Estado: En revisión

### Qué se corrigió
- **Merge de T05** con las correcciones de la segunda revisión (copia local de un curso oficial, `load_courses --relink` y dirección oficial fija) y con las decisiones de Carlos del 22-11-2026 (T02, T03 y T04 `Hecha`; evidencia local en T03). En `hub/models.py`, el control nuevo del slug oficial quedó junto a `clean_learning_path()` de T12. En `BITACORA.md` se conservaron las entradas de ambos lados.
- **Alta: respaldo con números internos de sección distintos.** Al revertir 0009 y volver a aplicarla, las secciones vacías se crean con otro número. Un JSON con esos números fallaba en una instalación recién migrada porque la misma sección ya existía con otro número.
  - `SectionPage` tiene clave natural: `natural_key()` devuelve el slug y su gestor tiene `get_by_natural_key(slug)`. No hay cambio de esquema ni migración nueva.
  - `/backup/` (`hub/views/management.py`) serializa `SectionPage` y `SectionBlock` con claves naturales. Las secciones van sin número interno y cada bloque apunta a su sección por el slug (`"page": ["environment"]`); el autor de la página, por el nombre de usuario. Los demás modelos conservan el formato anterior, así que los respaldos de T04 y T05 se restauran igual.
  - Al restaurar, `loaddata` busca cada sección por su slug y actualiza la que existe, con el número de la instalación nueva. Los bloques llegan a su sección y el HTML se vuelve a sanear como antes. Restaurar el mismo respaldo dos veces no duplica nada.
  - `README.md` lo explica. Un respaldo exportado con la versión anterior de T12 guarda los números internos y hay que volver a exportarlo.
- **Prueba nueva** `test_section_pages.BackupRestoresBySectionSlug`:
  - parte de la demo con teoría y bloques en dos secciones;
  - revierte 0009 y la vuelve a aplicar, y comprueba que cambian números internos;
  - exporta por `/backup/` y vacía el contenido;
  - vuelve a crear las 26 secciones con números nuevos y restaura;
  - compara la teoría, los bloques, el autor, los conteos de contenido, la página de la sección y la búsqueda;
  - restaura de nuevo sin duplicados.
  - Con el código anterior la prueba falla (`FAILED (failures=1)`): el JSON trae el número interno de cada sección.

### Desviaciones respecto a la tarea
- Ninguna. El formato del respaldo cambia solo en las dos tablas de T12.

### Verificación
- SQLite (`CICC_DEMO=1`): `System check identified no issues (0 silenced).` · `No changes detected` · `Ran 144 tests in 75.928s` · `OK`.
- PostgreSQL 16 local (`Iniciar-PostgreSQL.ps1`; modo producción, clave aleatoria, base temporal `cicc_corr2_t12` creada y borrada): `System check identified no issues (0 silenced).` · `No changes detected` · `Ran 144 tests in 90.791s` · `OK`.
- `ruff check .` → `All checks passed!` · `ruff format --check .` → `68 files already formatted` (Ruff 0.17.6).
- **Escenario de Codex con dos bases reales, en SQLite y en PostgreSQL**:
  - *Origen:* `migrate`, `seed_demo` y teoría con dos bloques en `environment` (editada por admin). Después, `migrate hub 0008` y `migrate`: `dashboard` pasó del número 1 al 27, y `environment` siguió en el 3.
  - *Exportación y destino:* se exportó con la vista `/backup/`, 126 objetos. El destino era una base nueva con `migrate` y las 8 cuentas y grupos del origen.
  - *Con la corrección:* `loaddata` → `Installed 126 object(s) from 1 fixture(s)` en ambos motores. El destino conserva sus números (`dashboard` = 1), 26 secciones y los mismos 32 recursos, 6 rutas, 39 lecciones y 2 bloques. La teoría, el origen `admin` y el autor `admin` llegaron, más la entrada de auditoría de la exportación.
  - *En la base SQLite restaurada:* el administrador abrió las 26 páginas con 200. `/p/environment/` muestra el bloque y la búsqueda de «ónice» lo encuentra.
  - *Control con el código anterior (`f5e4b1b`, extraído con `git archive` a una carpeta temporal):* el mismo procedimiento falla como en la revisión. SQLite: `Could not load hub.SectionPage(pk=27): UNIQUE constraint failed: hub_sectionpage.slug`. PostgreSQL: `duplicate key value violates unique constraint "hub_sectionpage_slug_key"` · `Key (slug)=(dashboard) already exists.`. El destino queda sin contenido.
  - Las bases temporales de PostgreSQL se borraron.

### Preguntas para el arquitecto
- Ninguna.

## T05 — Correcciones de la tercera revisión de Codex (23-11-2026)
- Fecha: 2026-11-23
- Modelo / herramienta: Claude Opus 5.5 (Claude Code)
- Rama y pull request: `tarea/T05-cursos-al-modelo`, en la carpeta de Carlos. Commit de código `3f8333f`. Sin publicar.
- Estado: En revisión

### Qué se corrigió
Hallazgos de `revision-codex-original-3.md` que tocan T05:
- **Alta: ejercicios propios junto a las lecciones oficiales.** Una ruta con las seis lecciones oficiales y dos ejercicios en la posición 0 recibía la dirección oficial. Al renumerar, los ejercicios pasaban a las posiciones 1 y 2, y `load_courses --force` los reescribía con el texto oficial.
  - Ahora cada posición del curso debe tener una sola lección, la oficial.
  - Solo se admiten lecciones propias **después** de la última lección oficial, porque ahí conservan su número y `--force` no las toca.
  - Una lección propia antes de la última, o una posición repetida, deja la ruta como local.
- **Alta: al revertir, la dirección oficial pasaba a una copia.** Si dos rutas cumplían la regla, la tomaba la de número interno menor, que podía ser una copia creada antes que el curso.
  - Ahora, con dos o más candidatas, ninguna toma la dirección. `load_courses` crea el curso aparte, y el avance sigue en su ruta.
  - El respaldo hecho antes de revertir ya se puede restaurar justo después de migrar, como indica el README: devuelve la dirección y el avance al curso correcto.
- **Media: recurso propio con el título de uno histórico.** `link_legacy_resources` reconocía el recurso por título y vínculo vacío.
  - Ahora, si hay más de un recurso con ese título, no vincula ninguno. Vale para la carga normal, `--force` y `--relink`.
  - `load_courses` avisa: «Hay más de un recurso titulado «…»: no se vinculó ninguno. Elige en el administrador cuál abre su curso.»
- **Media: cambio en lote de la dirección oficial.** Nuevo `LearningPathQuerySet`.
  - `update(slug=…)` rechaza cambiar una dirección oficial o dársela a otra ruta. `bulk_update(…, ['slug'])` aplica las mismas reglas que `save()`.
  - Las rutas locales y los demás campos se siguen actualizando en lote.
- **Alta (en T05 y T12): respaldo con cuentas numeradas de otra forma.** `backup_json()` guarda en `Progress`, `Attempt` y `Audit` a la persona por su nombre de usuario (clave natural de `User`), con `select_related('user')`.
  - Si falta la cuenta, `loaddata` se detiene sin aplicar nada.
  - Un respaldo anterior, con números, se sigue cargando.
- **README.** Se explican la regla nueva al revertir, el aviso de títulos repetidos y el requisito de las cuentas al restaurar. Un respaldo anterior al 23-11-2026 conviene volver a exportarlo.

### Desviaciones respecto a la tarea
- **Migración 0005 modificada otra vez.** Solo cambia su lógica de datos. Las bases que ya la aplicaron no se ven afectadas.
- **Un curso oficial con una lección propia antes de la última, o con dos candidatas, queda local al volver a migrar.** Es la consecuencia de no adivinar el origen, y está en el README.

### Verificación
- SQLite (`CICC_DEMO=1`): `System check identified no issues (0 silenced).` · `No changes detected` · `Ran 126 tests in 79.440s` · `OK`.
- PostgreSQL 16 local (modo producción, clave aleatoria, base de pruebas temporal): `System check identified no issues (0 silenced).` · `No changes detected` · `Ran 126 tests in 79.336s` · `OK`.
- `ruff check .` → `All checks passed!` · `ruff format --check .` → `63 files already formatted`.
- **Pruebas nuevas** (`hub/tests/test_codex_review_3.py`, 13), una o más por hallazgo:
  - Con el código anterior, las de los hallazgos de cursos, recursos y cambio en lote dan `FAILED (failures=7)`.
  - Las del respaldo, con el `backup_json` anterior, dan `FAILED (failures=2)`.
- **Copia de la demo de Carlos** (en `CICC-local\tmp-t05-demo`, borrada al terminar; el `demo.sqlite3` conservó su huella `333f4566e875e09a`):
  - Partida: 6 rutas, 39 lecciones, 23 con HTML y 3 vínculos.
  - `migrate hub 0003` y `migrate`: los tres cursos recuperaron `fundamentos-qa`, `qa-avanzado` y `certificacion-requerimiento` con los números 4, 5 y 6.
  - `load_courses` → 0 en todo. `--relink` → `recursos vinculados: 3`. `--force` → `reescritas: 26`.
  - Quedaron 23 lecciones con HTML y 3 vínculos.

### Preguntas para el arquitecto
- Sigue abierta: registrar en D4 el veto de Carlos.

### Observaciones
- El hallazgo de Codex sobre el texto plano que queda vacío al guardar una lección con `<p> </p>` es previo a T05 (`Lesson.save()`) y no se cambió.

## T12 — Correcciones de la tercera revisión de Codex (23-11-2026)
- Fecha: 2026-11-23
- Modelo / herramienta: Claude Opus 5.5 (Claude Code)
- Rama y pull request: `tarea/T12-paginas-del-menu`, en `CICC-local\original\T12`. Merge de T05 con las correcciones: `9553baf`. Sin publicar.
- Estado: En revisión

### Qué se corrigió
- **Correcciones de T05.** Llegan con el merge `9553baf`: los ejercicios propios, la dirección oficial al revertir, los títulos repetidos, el cambio en lote y el respaldo por nombre de usuario. Ver la entrada de T05 del mismo día.
- **Alta: avances, notas y auditoría asignados a otra cuenta.** El conflicto del merge en `hub/views/management.py` se resolvió así:
  - `SectionPage` y `SectionBlock` siguen con su clave natural, como en la segunda corrección.
  - `Progress`, `Attempt` y `Audit` guardan a la persona por su nombre de usuario.
  - El autor de una página ya se guardaba por nombre.
- **Baja: una consulta por bloque al exportar.** `backup_json()` carga junto con cada fila lo que necesita para escribir su clave: la página del bloque, el autor de la página y la persona del avance, del intento o de la auditoría (`RELATED`, con `select_related`). El número de consultas ya no crece con las filas.
- **Pruebas nuevas** (`hub/tests/test_backup_queries.py`, 2):
  - 50 bloques, 20 avances y 20 intentos no agregan consultas al respaldo.
  - Restauración con las cuentas creadas en otro orden: el avance y el intento vuelven a Ana, la página a Diego como autor, y el bloque se ve en `/p/glossary/`.
  - Las 13 pruebas de T05 (`test_codex_review_3.py`) también corren en T12.

### Desviaciones respecto a la tarea
Ninguna.

### Verificación
- SQLite (`CICC_DEMO=1`): `System check identified no issues (0 silenced).` · `No changes detected` · `Ran 159 tests in 97.353s` · `OK`.
- PostgreSQL 16 local (modo producción, clave aleatoria, base de pruebas temporal): `System check identified no issues (0 silenced).` · `No changes detected` · `Ran 159 tests in 118.073s` · `OK`.
- `ruff check .` → `All checks passed!` · `ruff format --check .` → `70 files already formatted`.
- Con el `backup_json` anterior, `test_backup_queries` da `FAILED (failures=2)`: `62 != 12` consultas, y el avance de Ana restaurado a nombre de Diego (`'diego' != 'ana'`).

### Preguntas para el arquitecto
Ninguna nueva.

### Observaciones
- La restauración se probó dentro de la suite en los dos motores, no con dos bases reales separadas como hizo Codex.

## Decisiones de Carlos — 24-11-2026
Tras la cuarta revisión de Codex (`revision-codex-original-4.md`):
- **D4: veto registrado.** Carlos confirmó que su veto del 21-11-2026 se anote en D4. Queda en `ARQUITECTURA-OBJETIVO.md`, bajo D4. Se cierra la pregunta abierta de T05.
- **T06: el avance es de solo lectura para todos.** Nadie borra un avance (`Progress`) desde el administrador, tampoco el superusuario. Se corrige en T06.
- **T06: el Editor sigue editando la teoría de las páginas del menú.** Conserva `view_sectionpage` y `change_sectionpage`. Se anota en la matriz de T06 y en D11.

## T05 — Correcciones de la cuarta revisión de Codex (24-11-2026)
- Fecha: 2026-11-24
- Modelo / herramienta: Claude Opus 5.5 (Claude Code)
- Rama y pull request: `tarea/T05-cursos-al-modelo`, en la carpeta de Carlos. Commit de código `4d964f8`. Sin publicar.
- Estado: En revisión

### Qué se corrigió
Hallazgos de `revision-codex-original-4.md` que tocan T05:
- **Alta: una base ya migrada perdía ejercicios con `--force`.** La 0005 anterior pudo dar la dirección oficial a una ruta con ejercicios en la posición 0 y renumerarla: los ejercicios quedaron en 1 y 2, y las lecciones oficiales en 3 a 8.
  - Ahora `load_courses` comprueba cada curso antes de tocarlo (`shifted_lessons`). Si una lección oficial, por su título, está fuera de su posición, no reescribe ni crea ninguna lección de ese curso, ni siquiera con `--force`.
  - El comando avisa: «“…” tiene lecciones oficiales fuera de su posición…: ordénalas en el administrador y vuelve a ejecutar el comando». Una vez ordenadas, `--force` vuelve a funcionar y los ejercicios, ya después de la última lección oficial, no se tocan.
- **Alta: un curso editado cedía su dirección a la copia.** Con la copia creada antes (seis lecciones intactas y una séptima) y una lección oficial editada, solo la copia cumplía la regla.
  - Ahora, si otra ruta del mismo título conserva alguna lección oficial intacta, ninguna toma la dirección. Una copia con todos sus textos propios sigue sin impedir que se reconozca el curso (las pruebas de las revisiones anteriores no cambiaron).
- **Alta: la recuperación fallaba según el orden de creación.** El respaldo listaba las rutas por posición; al restaurar, la copia pedía `fundamentos-qa-2` mientras el curso todavía la ocupaba.
  - Ahora `backup_json()` guarda cada modelo por número interno, el mismo orden en que la migración reparte las direcciones locales. Al restaurar en la misma base, cada dirección se libera antes de que otra ruta la recupere.
  - Se probó en los dos órdenes, con y sin edición: el curso vuelve a «1 de 6» con su avance y su edición.
  - El README da las dos formas comprobadas: en la misma base justo después de migrar, o en una base nueva (`migrate`, cuentas, `loaddata`), siempre antes de `load_courses`. Un respaldo anterior al 24-11-2026 conviene restaurarlo en una base nueva.
- **Media: una expresión podía dar una dirección reservada.** `LearningPathQuerySet.update()` comprueba ahora el slug que queda guardado, dentro de una transacción. Si una ruta cambia una dirección oficial o toma una, se deshace todo el cambio. Los valores literales se siguen comprobando antes.
- **Media: un recurso histórico renombrado.** Si algún recurso ya abre el curso, `link_legacy_resources` no vincula otro. El aviso de títulos repetidos se mantiene.
- **Baja: `bulk_update` con un iterador.** Se convierte en lista antes de comprobarlo.
- **D4.** Se anota el veto de Carlos (decisión del 21-11-2026) en `ARQUITECTURA-OBJETIVO.md`.

### Desviaciones respecto a la tarea
- **Migración 0005 modificada otra vez.** Solo cambia su lógica de datos. Las bases que ya la aplicaron no se ven afectadas; para ellas está la protección de `load_courses`.

### Verificación
- SQLite (`CICC_DEMO=1`): `System check identified no issues (0 silenced).` · `No changes detected` · `Ran 136 tests in 132.655s` · `OK`.
- PostgreSQL 16.16 local (modo producción, clave aleatoria, base temporal `cicc_rev4_t05` borrada al terminar): `System check identified no issues (0 silenced).` · `No changes detected` · `Ran 136 tests in 133.337s` · `OK`.
- `ruff check .` → `All checks passed!` · `ruff format --check .` → `64 files already formatted`.
- **Pruebas nuevas** (`hub/tests/test_codex_review_4.py`, 10). Con el código anterior: `FAILED (failures=6, errors=1)`. Las otras tres comprueban que lo que ya funcionaba sigue funcionando.
- **Copia de la demo de Carlos** (worktree temporal en `CICC-local\tmp-rev4-t05`, borrado al terminar; el `demo.sqlite3` conservó su huella `333f4566e875e09a`):
  - `migrate hub 0003` y `migrate`: los tres cursos recuperaron su dirección con los números 4, 5 y 6.
  - `load_courses` → 0 en todo. `--relink` → `recursos vinculados: 3`. `--force` → `reescritas: 26`.
  - Quedaron 6 rutas, 39 lecciones, 23 con HTML y 3 vínculos, como al principio.

### Preguntas para el arquitecto
- Ninguna. La de D4 queda resuelta.

### Observaciones
- PostgreSQL local se apagó una vez durante la verificación porque faltaba `datos\postmaster.pid`. Se volvió a arrancar con `Iniciar-PostgreSQL.ps1` y las pruebas se repitieron.

## T12 — Correcciones de la cuarta revisión de Codex (24-11-2026)
- Fecha: 2026-11-24
- Modelo / herramienta: Claude Opus 5.5 (Claude Code)
- Rama y pull request: `tarea/T12-paginas-del-menu`, en `CICC-local\original\T12`. Merge de T05 con las correcciones: `b6c84ac`. Sin publicar.
- Estado: En revisión

### Qué se corrigió
- **Correcciones de T05.** Llegan con el merge `b6c84ac`: ejercicios de bases ya migradas, curso editado frente a copia, recuperación en los dos órdenes, expresiones en `update()`, recurso histórico renombrado e iteradores en `bulk_update()`. Ver la entrada de T05 del mismo día.
- **Baja: conflicto de integración en el README.** La sección de recuperación tenía marcas de Git del merge `9553baf` y dos versiones del mismo párrafo. Queda una sola: el párrafo de las páginas de sección y la guía de T05 para revertir y restaurar.
- **Conflicto en `hub/views/management.py`.** `backup_json()` ordena cada modelo por número interno (T05) y conserva `RELATED` con `select_related` (T12): el respaldo sigue sin una consulta por fila.

### Desviaciones respecto a la tarea
Ninguna.

### Verificación
- SQLite (`CICC_DEMO=1`): `System check identified no issues (0 silenced).` · `No changes detected` · `Ran 169 tests in 166.300s` · `OK`.
- PostgreSQL 16.16 local (modo producción, base temporal `cicc_rev4_t12` borrada al terminar): `System check identified no issues (0 silenced).` · `No changes detected` · `Ran 169 tests in 190.010s` · `OK`.
- `ruff check .` → `All checks passed!` · `ruff format --check .` → `71 files already formatted`.
- `test_backup_queries.py` sigue pasando: el número de consultas del respaldo no crece con los bloques.
- **Copia de la demo de Carlos** (worktree temporal `CICC-local\tmp-rev4-t12`, borrado; huella `333f4566e875e09a` sin cambios): `migrate` dejó 6 rutas, 39 lecciones, 23 con HTML, 3 vínculos y 26 páginas. Tras `migrate hub 0003`, `migrate`, `--relink` (3) y `--force` (26), los mismos números. Las 7 pantallas de gestión respondieron 200 al administrador.

### Preguntas para el arquitecto
Ninguna.

## Decisión de Carlos — 24-11-2026 (tras la quinta revisión de Codex)
- **Opción 2.** Tras `revision-codex-original-5.md`, Carlos decidió corregir lo grave y lo que afecta al uso normal, y dejar el resto anotado como límites conocidos en el README. Son estos:
  - restaurar en la misma base con direcciones propias cruzadas: se restaura en una base nueva;
  - `--relink` cuando otro recurso ya abre el curso: se asigna en el administrador;
  - `update()` desde código con una ruta creada al mismo tiempo desde otra conexión.

## T05 — Correcciones de la quinta revisión de Codex (24-11-2026)
- Fecha: 2026-11-24
- Modelo / herramienta: Claude Opus 5.5 (Claude Code)
- Rama y pull request: `tarea/T05-cursos-al-modelo`, en la carpeta de Carlos. Commit de código `2ea3b72`. Sin publicar.
- Estado: En revisión

### Qué se corrigió
- **Alta: un ejercicio completado se convertía en una semana oficial.** `shifted_lessons` reconoce ahora la lección oficial por su título **o por su texto**. Con la semana 6 renombrada en la posición 7 y un ejercicio en la 6, el curso queda protegido y `load_courses` avisa. Una vez movido el ejercicio después del curso, `--force` repone la semana 6.
- **Alta: la copia heredaba la dirección al revertir.** La 0005 deja todas las rutas locales si cualquier otra ruta, se llame como se llame, conserva el título o el texto de una lección oficial en su posición. Cubre el curso renombrado y el curso con sus seis textos editados. En ambos casos, el respaldo restaurado en la misma base devuelve **1 de 6**.
- **Media: reordenar desde el administrador daba error 500.** `LearningPathAdmin.save_formset()` lleva antes a posiciones libres las lecciones que cambian de posición. Después cada una recibe la suya, en un solo guardado.
- **Baja: una práctica con el título de una semana bloqueaba la carga.** No cuenta como desplazada si esa semana ya está en su lugar. La semana que falta se crea.
- **Límites conocidos** (decisión de Carlos, opción 2): están en el README.

### Desviaciones respecto a la tarea
- **Migración 0005 modificada otra vez.** Solo cambia su lógica de datos.
- **Prueba existente ajustada.** En `test_migrations.test_reapplying_after_a_revert_keeps_the_local_copy_apart`, la copia conserva los títulos oficiales. Con la regla nueva, el curso no se reconoce y `load_courses` lo crea aparte. La prueba espera ahora que el curso anterior no tome la dirección oficial, y tres rutas en lugar de dos. Las comprobaciones de la copia (textos, avance y dirección `fundamentos-qa-2`) no cambiaron.

### Verificación
- SQLite (`CICC_DEMO=1`): `System check identified no issues (0 silenced).` · `No changes detected` · `Ran 142 tests in 125.250s` · `OK`.
- PostgreSQL 16.16 local (base temporal borrada): `System check identified no issues (0 silenced).` · `No changes detected` · `Ran 142 tests in 127.356s` · `OK`.
- `ruff check .` → `All checks passed!` · `ruff format --check .` → `65 files already formatted`.
- **Pruebas nuevas** (`hub/tests/test_codex_review_5.py`, 6). Con el código anterior: `FAILED (failures=4, errors=1)`. La sexta comprueba que `--force` vuelve a funcionar después de ordenar.
- **Copia de la demo de Carlos** (worktree temporal borrado; huella `333f4566e875e09a` sin cambios): tras `migrate hub 0003` y `migrate`, los tres cursos recuperaron su dirección (4, 5 y 6). `--relink` → 3. `--force` → 26. Quedaron 6 rutas, 39 lecciones, 23 con HTML y 3 vínculos.

## T12 — Correcciones de la quinta revisión de Codex (24-11-2026)
- Fecha: 2026-11-24
- Modelo / herramienta: Claude Opus 5.5 (Claude Code)
- Rama y pull request: `tarea/T12-paginas-del-menu`, en `CICC-local\original\T12`. Merge de T05: `5b18195`. Sin publicar.
- Estado: En revisión

### Qué se corrigió
- **Correcciones de T05.** Llegan con el merge `5b18195`: semanas reconocidas por título o texto, curso renombrado o reescrito al revertir, reordenación en un solo guardado, práctica con título repetido y límites conocidos (opción 2 de Carlos). Ver la entrada de T05 del mismo día.
- **Conflictos.** En `hub/admin.py` se juntaron las importaciones `Count` (T12) y `Max` (T05). En el README se conservó el párrafo de las páginas de sección y la guía nueva de T05. Queda una sola guía de recuperación.

### Desviaciones respecto a la tarea
Ninguna.

### Verificación
- SQLite (`CICC_DEMO=1`): `System check identified no issues (0 silenced).` · `No changes detected` · `Ran 175 tests in 162.975s` · `OK`.
- PostgreSQL 16.16 local (base temporal borrada): `System check identified no issues (0 silenced).` · `No changes detected` · `Ran 175 tests in 176.031s` · `OK`.
- `ruff check .` → `All checks passed!` · `ruff format --check .` → `72 files already formatted`.
- README: una sola sección «Revertir las migraciones de cursos», un solo «Límites conocidos» y ninguna marca de conflicto.

## Decisión de Carlos — 24-11-2026 (tras la sexta revisión de Codex)
- **Opción 1: dejar de adivinar.** Tras `revision-codex-original-6.md`, Carlos eligió cambiar el diseño en lugar de seguir con parches:
  - al revertir, la 0005 ya no reconoce ningún curso;
  - `--force` solo reescribe lecciones con marca de «lección oficial».
- Se corrigen también los tres hallazgos sencillos: reutilizar un puesto en el mismo guardado, la posición máxima y el aviso de T06 en español.

## T05 — Correcciones de la sexta revisión de Codex: no adivinar (24-11-2026)
- Fecha: 2026-11-24
- Modelo / herramienta: Claude Opus 5.5 (Claude Code)
- Rama y pull request: `tarea/T05-cursos-al-modelo`, en la carpeta de Carlos. Commit de código `651399e`. Sin publicar.
- Estado: En revisión

### Qué se corrigió
- **Alta: un ejercicio completado se reescribía.** Las variantes que encontró Codex (mismo título que una semana desplazada, semana con título y texto cambiados) venían de reconocer las lecciones por posición, título o texto.
  - Nuevo campo `Lesson.official_key` (migración 0008), con valor «<slug>:<posición oficial>». Solo lo escribe `load_courses` al crear la lección, no se edita en formularios y es único en cada ruta.
  - `--force` reescribe solo lecciones con marca, estén donde estén.
  - Una lección oficial que falta se crea en su posición si está libre. Si la ocupa una lección propia, esa lección se conserva y el comando avisa.
- **Lecciones sin marca.** Son las de instalaciones y respaldos anteriores. La 0008 y `load_courses` marcan solo las idénticas a la oficial (posición, título y texto). Reescribir una lección idéntica no cambia nada, y un ejercicio con texto propio nunca lo es. Las editadas quedan sin marca, y `--force` no las toca.
- **Alta: la copia heredaba la dirección al revertir.** La 0005 ya no reconoce ningún curso: todas las rutas reciben un slug propio. La dirección vuelve restaurando el respaldo hecho antes de revertir. Se probó también con el curso reordenado (caso de la sexta revisión).
- **Media: quitar una lección y reutilizar su puesto daba error 500.** `save_formset()` lleva también a posiciones libres las lecciones marcadas para quitar.
- **Baja: posición máxima.** Las posiciones temporales son los números libres más bajos, no «máximo + 1», así que siempre caben en el campo.
- **Baja: práctica de repaso que impedía recuperar una semana.** Ya no hay detección de lecciones desplazadas: la semana que falta se crea si su posición está libre.
- **README.** La guía de cursos está reescrita: marca de lección oficial, `--force`, revertir y restaurar.

### Desviaciones respecto a la tarea
- **Migración 0005 simplificada** y **migración nueva 0008**. Las bases que ya aplicaron la 0005 no cambian.
- **Pruebas existentes ajustadas al diseño nuevo:**
  - `test_migrations.test_reapplying_after_a_revert_leaves_every_path_local` (antes «…recognises_the_official_course») espera ahora que el curso intacto quede local.
  - `test_codex_review_4` espera el aviso de posición ocupada en lugar del de lecciones desplazadas.
  - `test_codex_review_5.ForceKeepsAnUnrecognisedLesson` usa lecciones con marca.
  - Las comprobaciones de textos y avances no cambiaron.

### Verificación
- SQLite (`CICC_DEMO=1`): `System check identified no issues (0 silenced).` · `No changes detected` · `Ran 151 tests in 100.523s` · `OK`.
- PostgreSQL 16.16 local (base temporal borrada): `System check identified no issues (0 silenced).` · `No changes detected` · `Ran 151 tests in 117.809s` · `OK`.
- `ruff check .` → `All checks passed!` · `ruff format --check .` → `66 files already formatted`.
- **Pruebas nuevas** (`hub/tests/test_codex_review_6.py`, 9). Con el código anterior, 6 de las 8 primeras fallan: `FAILED (failures=2, errors=4)`. La novena, del respaldo sin marcas, se agregó después.
- **Copia de la demo de Carlos** (worktree temporal borrado; huella `333f4566e875e09a` sin cambios):
  - Al migrar desde 0007, las 23 lecciones oficiales quedan marcadas. `load_courses` → 0. `--force` → 26.
  - Respaldo, `migrate hub 0003` y `migrate`: 6 rutas, ninguna oficial, 0 marcas.
  - `loaddata` del respaldo en la misma base: `Installed 97 object(s)`, los tres cursos en sus direcciones (4, 5 y 6), 23 marcas, 23 lecciones con HTML y 3 vínculos. `load_courses` → 0.

## T12 — Correcciones de la sexta revisión de Codex (24-11-2026)
- Fecha: 2026-11-24
- Modelo / herramienta: Claude Opus 5.5 (Claude Code)
- Rama y pull request: `tarea/T12-paginas-del-menu`, en `CICC-local\original\T12`. Merge de T05: `2d2f92c`. Sin publicar.
- Estado: En revisión

### Qué se corrigió
- **Correcciones de T05.** Llegan con el merge `2d2f92c`: marca de lección oficial, 0005 sin reconocimiento al revertir y posiciones del formulario de la ruta. Ver la entrada de T05 del mismo día.
- **Migración de unión `0010_merge_lesson_official_key`.** La 0008 nueva de T05 y las 0008 y 0009 de T12 salen de 0007. La unión no tiene operaciones. Una base con T12 ya aplicada solo añade la 0008 de T05.
- **Conflictos.** En `hub/admin.py`, T05 ya no usa `Max` y se conserva `Count` de T12. En el README se conservaron el párrafo de las páginas de sección y la guía nueva de T05.

### Desviaciones respecto a la tarea
- La migración de unión, necesaria porque T05 y T12 agregaron migraciones en paralelo.

### Verificación
- SQLite (`CICC_DEMO=1`): `System check identified no issues (0 silenced).` · `No changes detected` · `Ran 184 tests in 157.697s` · `OK`.
- PostgreSQL 16.16 local (base temporal borrada): `System check identified no issues (0 silenced).` · `No changes detected` · `Ran 184 tests in 198.733s` · `OK`.
- `ruff check .` → `All checks passed!` · `ruff format --check .` → `73 files already formatted`.
- **Actualización de una base con T12 anterior** (copia de la demo, worktrees temporales borrados; huella `333f4566e875e09a` sin cambios):
  - Con `30415f2`, la copia quedó en 0009.
  - Con la versión nueva, `migrate` aplicó `0008_lesson_official_key` y `0010_merge_lesson_official_key`.
  - Resultado: 26 páginas, 6 rutas y 23 lecciones oficiales marcadas.

## T05 — Revisión completa de pendientes (24-11-2026)
- Fecha: 2026-11-24
- Modelo / herramienta: Claude Opus 5.5 (Claude Code)
- Rama y pull request: `tarea/T05-cursos-al-modelo`, en la carpeta de Carlos. Sin publicar.
- Estado: En revisión

### Qué se corrigió
Revisión pedida por Carlos para no dejar pendientes:
- **Ayuda de `load_courses`.** Decía «por slug y posición». Ahora describe la marca de lección oficial, también en `--force`.
- **`ARQUITECTURA-OBJETIVO.md`.** La tabla de modelos incluye `Lesson.official_key`.
- **Pruebas sin efecto.**
  - Se quitó `test_codex_review_4.test_after_ordering_the_lessons_force_works_again`. Con el diseño nuevo pasaba sin comprobar nada; lo cubren las pruebas de `test_codex_review_6.py`.
  - `test_codex_review_5.PracticeWithARepeatedTitle` comprueba el aviso nuevo en lugar del que ya no existe.

### Criterios de aceptación de la ficha
- [x] El `grep` de títulos solo encuentra `seed_demo.py`, pruebas y los `course.json`. Esos `course.json` llevan `legacy_resource_titles` por el veto de Carlos a D4, anotado en la corrección de la primera revisión.
- [x] Las plantillas trasladadas ya no existen.
- [x] Las migraciones se aplican sobre una copia de `demo.sqlite3` sin perder rutas, lecciones ni progreso, y se revierten. Tras revertir, los cursos se recuperan con el respaldo (decisión de Carlos).
- [x] Pruebas en SQLite y PostgreSQL.
- [ ] **Comparación visual de una lección de cada curso contra `main`: pendiente de Carlos.** El texto de cada lección coincide con su archivo (`test_each_lesson_text_matches_its_original_file`).
- **Desviación del paso 4.** `load_courses` identifica las lecciones por su marca y no por `slug` y `position` (decisión de Carlos, 24-11-2026).

### Estado de observaciones anteriores
- **Resueltas:**
  - «ID fijo en la plantilla de importación» (T02) se corrigió en T03.
  - «Insignia ajena» (T03) se corrigió en T03.
  - «`updated_by` como id de usuario» (T12) se resolvió en la tercera revisión: el respaldo guarda las personas por nombre de usuario.
- **Superadas por el diseño nuevo:**
  - «Ruta local mezclada con el curso» y «título editado y reversión» (22-11-2026). Una lección propia sin marca ya no se reescribe con `--force`. Al revertir no se reconoce ningún curso.
- **Siguen abiertas:**
  - `<p> </p>` deja el texto plano vacío (`Lesson.save()`, anterior a T05).
  - `ARQUITECTURA.md` y `CAMBIOS-CICC.md` describen la versión anterior (T11).
  - Las vistas fuera de `/p/` no se miden en consultas (T04).


## T05 — Correcciones de la séptima revisión de Codex (24-11-2026)
- Fecha: 2026-11-24
- Modelo / herramienta: Claude Opus 5.5 (Claude Code)
- Rama y pull request: `tarea/T05-cursos-al-modelo`, en la carpeta de Carlos. Commit de código `6ee00de`. Sin publicar.
- Estado: En revisión

### Qué se corrigió
Hallazgos de `revision-codex-original-7.md` (Carlos aprobó corregir los 8):
- **1 (Alta, en T12 y T06): volver a la versión anterior del programa.** README, «Volver a una versión anterior del programa». Antes de actualizar se hace una copia completa de la base (archivo de SQLite o `pg_dump -Fc`), y para volver atrás se restaura con el programa anterior. Revertir migraciones no basta: la marca de lección oficial puede quedar en la base. Se comprueba en T12.
- **2 (Media): devolver una lección a su curso daba error 500.** `Lesson.save()` quita la marca a una lección que pasa a otra ruta. `load_courses` repone la oficial, y la lección movida vuelve como lección propia sin chocar.
- **3 (Media): aviso de posición ocupada.** Distingue «otra lección oficial, «…», que se movió ahí» de «una lección propia, «…»». Aclara que el resto del curso sí se cargó.
- **4 (Media): qué es una lección idéntica.** El README explica que se compara el texto sin formato y que `--force` devolvería el formato oficial. La ayuda del comando ya describía la marca.
- **5 (Media): restaurar con la posición máxima.** `restore_lesson` usa el primer número libre cuando el final está en el máximo del campo.
- **7 (Baja): límite de direcciones cruzadas.** Descrito para cualquier dirección que otra ruta ocupe al volver a migrar.
- **8 (Baja): restos en las pruebas.**
  - Ayudante `hub/tests/temp.py`: las carpetas temporales se borran al terminar cada prueba. Antes y después de la suite, el número de carpetas temporales es el mismo (2840).
  - Se quitó `test_codex_review_3.LoadCoursesErrors`, igual a la de `test_course_identity`.
- **Ficha de T05.** Notas en los pasos 4 y 7 (marca de lección oficial y veto). El criterio del `grep` y la prueba del recurso histórico se ajustan al veto.
- El hallazgo 6 (archivos Markdown con firma UTF-8) es de T12.

### Verificación
- SQLite (`CICC_DEMO=1`): `No changes detected` · `Ran 153 tests in 172.560s` · `OK`. PostgreSQL 16.16: `No changes detected` · `Ran 153 tests in 183.342s` · `OK`. `check` sin incidencias en ambos.
- `ruff check .` → `All checks passed!` · `ruff format --check .` → `68 files already formatted`.
- **Pruebas nuevas** (`hub/tests/test_codex_review_7.py`, 4). Con el código anterior: `FAILED (failures=3, errors=1)`.

## T12 — Correcciones de la séptima revisión de Codex (24-11-2026)
- Fecha: 2026-11-24
- Modelo / herramienta: Claude Opus 5.5 (Claude Code)
- Rama y pull request: `tarea/T12-paginas-del-menu`, en `CICC-local\original\T12`. Merge de T05 con las correcciones de T12: `71584a8`. Sin publicar.
- Estado: En revisión

### Qué se corrigió
- **Correcciones de T05.** Llegan con el merge `71584a8`. En `hub/models.py`, `Lesson.save()` junta `clean_lesson()` (T12) con `drop_official_key_when_moved()` (T05).
- **Hallazgo 1 (Alta): volver a la versión anterior del programa.** La guía está en el README, en la sección «Volver a una versión anterior del programa». Se comprobó con una copia de la demo:
  - Con el programa anterior (`30415f2`), la base llega a 0009 y se hace la copia completa.
  - Con el programa nuevo, se ejecuta `migrate`.
  - **Solo revertir** (`migrate hub 0009`) y volver al programa anterior: crear una lección falla (`NOT NULL constraint failed: hub_lesson.official_key`), como encontró Codex.
  - **Restaurar la copia completa** con el programa anterior: la lección se crea, y quedan 26 páginas y todas las lecciones.
- **Hallazgo 6 (Baja): Markdown con firma UTF-8.** `parse_page_file` lee con `utf-8-sig`. El título se reconoce con firma y sin ella (`test_codex_review_7_pages.py`).
- **Hallazgo 8: restos en las pruebas.** `test_section_pages` usa `temp_folder`.
- **`ARQUITECTURA-OBJETIVO.md`.** `SectionPage` y `SectionBlock` están en la tabla de modelos.

### Verificación
- SQLite (`CICC_DEMO=1`): `No changes detected` · `Ran 187 tests in 211.156s` · `OK`. PostgreSQL 16.16: `No changes detected` · `Ran 187 tests in 250.026s` · `OK`. `check` sin incidencias en ambos.
- `ruff check .` → `All checks passed!` · `ruff format --check .` → `76 files already formatted`.
- La huella del `demo.sqlite3` de Carlos no cambió (`333f4566e875e09a`).