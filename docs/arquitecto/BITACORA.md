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
