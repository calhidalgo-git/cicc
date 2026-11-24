# CICC — Arquitectura objetivo

Arquitecto: Claude. Dueño del producto: Carlos Linares. Fecha: 10 de noviembre de 2026.

Este documento manda sobre `ARQUITECTURA.md`, `DISEÑO.md` y `README.md` mientras dure el plan. La tarea T11 los pone al día.

## 1. Meta

Convertir el prototipo CICC en una **herramienta interna real** para la Sección de Control de Calidad, instalada en un **servidor interno** con PostgreSQL, usada por personas reales con cuentas reales, y mantenible por alguien que no la escribió.

No es meta: rediseñar la interfaz, cambiar de framework, ni integrarse con sistemas de la organización.

## 2. Principios

1. **Evolucionar, no reescribir.** Se conserva Django, la app `hub`, el modelo de datos, el diseño visual y las URLs actuales.
2. **Los datos de las personas no se pierden.** Progreso, intentos y auditoría sobreviven a reinicios, despliegues y migraciones.
3. **El contenido vive en la base de datos** y se edita desde el administrador, no en el código.
4. **Seguro por defecto.** Sin variables de entorno, la aplicación arranca en modo producción y se niega a funcionar con valores inseguros.
5. **Pocas piezas.** Un proceso web, una base de datos, una carpeta de archivos. Sin colas, sin caché externo, sin contenedores obligatorios.
6. **Cada cambio se prueba.** Ninguna tarea se cierra sin pruebas automáticas del comportamiento nuevo.

## 3. Estado de partida (diagnóstico)

| # | Problema | Dónde | Tarea |
|---|---|---|---|
| 1 | La pantalla que abre un recurso depende de su título; el dashboard además muestra títulos sustituidos | `hub/views.py` (`resource`), `templates/page.html` | T05 |
| 2 | 23 lecciones de tres cursos son plantillas HTML: sin búsqueda, sin progreso, sin edición | `templates/qa_weeks`, `qa_advanced_weeks`, `certification_topics` | T05 |
| 3 | Una sola vista ejecuta todas las consultas para cualquier sección; una sola plantilla de 13 KB dibuja 26 secciones | `page()`, `page.html` | T04 |
| 4 | Código compactado en una línea, difícil de revisar y de comparar en git | `hub/`, `config/`, plantillas | T01 |
| 5 | `DEBUG` vale 1 por defecto, clave secreta con valor fijo, sin validadores de contraseña, bloque de Vercel que guarda la base en `/tmp` | `config/settings.py` | T02 |
| 6 | Un solo permiso (`hub.view_audit`) abre reportes, auditoría y respaldo; el respaldo incluye intentos de todos | `GATES`, `backup()` | T06 |
| 7 | Roles y usuarios solo existen a través de `seed_demo`, que crea cuentas con contraseña pública | `seed_demo.py` | T06 |
| 8 | Editar o borrar una pregunta cambia la nota mostrada de intentos ya cerrados; dos inicios simultáneos crean dos intentos | `grade()`, `results()`, `start()` | T07 |
| 9 | Sin límite de intentos de login ni cambio de contraseña por el usuario | — | T08 |
| 10 | Sin servidor de aplicación, sin estáticos de producción, sin logs, sin respaldo automatizado | — | T09, T10 |
| 11 | Las rutas `/qa/...` no tienen pruebas; la documentación no las menciona; valores fijos en el dashboard ("02", "12 lecciones") | pruebas, docs, `page.html` | T04, T05, T11 |

## 4. Arquitectura objetivo

```
Navegador (intranet)
   │  HTTP o HTTPS
   ▼
[Proxy inverso opcional: IIS o Nginx, termina HTTPS]
   │
   ▼
Waitress (servidor WSGI, un proceso, hilos)
   │
   ▼
Django 5.2  ── WhiteNoise sirve /static/
   │   ├── app hub (vistas, plantillas, comandos)
   │   └── Django Admin (edición de contenido, usuarios, roles)
   ├──► PostgreSQL (datos)
   ├──► private_storage/ (adjuntos; nunca expuesto por el proxy)
   └──► logs/ (archivo rotativo)

Tareas programadas del sistema operativo:
   - cada 5 min: manage.py close_expired
   - cada noche: respaldo de base + private_storage
```

Modo local o demo (`CICC_DEMO=1`): mismo código con SQLite, `runserver` y datos ficticios. Es el modo para desarrollo y pruebas.

## 5. Estructura de código objetivo

```
config/
  settings.py          configuración única, dirigida por variables de entorno
  urls.py              solo incluye hub.urls y admin
  wsgi.py
hub/
  models.py
  admin.py
  urls.py              todas las rutas de la app
  permissions.py       NAV, GATES y ayudas de permisos
  services/
    exams.py           iniciar, guardar, calificar, cerrar vencidos
    courses.py         carga y saneado de contenido de cursos
    excel.py           plantilla, importación, exportaciones
  views/
    __init__.py
    pages.py           dashboard, secciones de gestión, healthz
    library.py         biblioteca, módulos, búsqueda, recurso, descarga
    learning.py        rutas, lecciones, progreso
    exams.py           evaluación, guardado, resultados
    management.py      importación, reportes, respaldo
  content/courses/     contenido inicial de los tres cursos (HTML + course.json)
  management/commands/
    bootstrap_roles.py crea grupos y permisos; seguro en producción
    load_courses.py    carga cursos iniciales; idempotente
    close_expired.py   cierra intentos vencidos
    seed_demo.py       solo con CICC_DEMO=1
  tests/               un archivo por área
templates/
  base.html
  pages/               una plantilla por sección
  ...
scripts/               arranque, respaldo y restauración (PowerShell y bash)
docs/
```

## 6. Decisiones de arquitectura

Cada decisión es definitiva para los implementadores. Carlos puede vetar las marcadas con ⚑ antes de que empiece la tarea correspondiente.

**D1. Se mantiene el monolito Django con plantillas de servidor.** Sin API REST separada ni framework de frontend. El equipo es pequeño y la aplicación es de lectura y formularios.

**D2. Configuración única por variables de entorno** (tabla en la sección 9). Sin `CICC_DEMO=1` la aplicación exige clave secreta y hosts, y `DEBUG` vale 0. Se elimina el bloque de Vercel y `.vercel.app`.

**D3. PostgreSQL en el servidor; SQLite solo en modo demo y pruebas.** La integración continua ejecuta las pruebas en ambos motores.

**D4. ⚑ Los tres cursos pasan a `LearningPath` y `Lesson`.** Fundamentos QA, QA Avanzado y Certificación de un Requerimiento dejan de ser plantillas y se cargan a la base con `load_courses`. Ganan progreso, búsqueda y edición en el administrador. Consecuencia visible: los recursos "Guía de pruebas batch y JCL", "Checklist de pruebas de API REST" e "Introducción a DB2 para QA" vuelven a mostrarse como lo que son, y los cursos se abren desde Rutas de aprendizaje y desde el dashboard.

  **Veto de Carlos (21-11-2026, registrado el 24-11-2026).** La consecuencia visible no se aplica. Los tres recursos siguen viéndose como antes de T05: con el nombre de su curso y abriendo su teoría. El vínculo se guarda en `Resource.learning_path` (migración 0007) y no depende del título (D6); se edita en el administrador. Los cursos también se abren desde Rutas de aprendizaje y desde el dashboard.

**D5. Contenido enriquecido como HTML saneado.** `Lesson.body_html` y `LearningPath.intro_html` guardan HTML limitado a una lista de etiquetas permitidas, saneado con `nh3` al guardar. `Lesson.body` conserva el texto plano (derivado del HTML cuando existe) y es lo único que usa la búsqueda.

**D6. Ninguna lógica depende de títulos.** La navegación usa claves estables (`slug`, `pk`, `kind`). Se eliminan las comparaciones de título en vistas y plantillas.

**D7. Las URLs actuales siguen funcionando.** Las rutas `/p/<sección>/` se conservan. Las rutas `/qa/...` redirigen de forma permanente a las nuevas `/rutas/<slug>/...`.

**D8. Los intentos guardan una copia de sus preguntas.** Al iniciar, `Attempt.snapshot` almacena enunciado, opciones, índice correcto y explicación. Examen, guardado, nota y resultados leen de esa copia. Editar el banco no altera intentos existentes.

**D9. Un solo intento abierto por persona y evaluación,** garantizado por una restricción de unicidad condicional en la base. `Assessment.max_attempts` limita intentos cerrados (0 = sin límite).

**D10. Permisos separados:** `hub.view_reports` (reportes y exportación Excel), `hub.view_audit` (auditoría), `hub.export_backup` (respaldo JSON, solo Administrador).

**D11. Roles sin datos demo.** `bootstrap_roles` crea los cuatro grupos y sus permisos y puede ejecutarse en producción las veces que haga falta. `seed_demo` lo invoca y solo corre con `CICC_DEMO=1`. El primer administrador real se crea con `createsuperuser`.

**D12. Waitress + WhiteNoise.** Funcionan igual en Windows y Linux y no requieren compilar nada. HTTPS, si se usa, lo termina un proxy inverso; `CICC_HTTPS=1` activa cookies seguras y cabeceras.

**D13. Sin correo.** No hay recuperación de contraseña por correo; un administrador restablece contraseñas desde el administrador y cada persona puede cambiar la suya dentro de la aplicación.

**D14. Bloqueo de login con `django-axes`:** 5 fallos por usuario e IP bloquean 15 minutos.

**D15. Estilo de código:** `ruff format` y `ruff check` con la configuración de `pyproject.toml`. Una sentencia por línea. Las plantillas se escriben con sangría, una etiqueta de bloque por línea.

## 7. Cambios al modelo de datos

| Modelo | Cambio | Tarea |
|---|---|---|
| `LearningPath` | + `slug` (único), + `intro_html` (opcional), + `position` (orden en listados) | T05 |
| `Lesson` | + `body_html` (opcional); restricción única (`path`, `position`); + `official_key` (marca de lección oficial, solo la escribe `load_courses`; única en cada ruta; decisión de Carlos del 24-11-2026) | T05 |
| `SectionPage`, `SectionBlock` | Nuevos: la teoría de cada opción del menú. Una página por `slug` de `NAV` (clave natural en el respaldo), con introducción, origen, fecha y autor; bloques por página y posición. HTML saneado y texto plano para la búsqueda | T12 |
| `Attempt` | + `snapshot` (JSON); restricción única (`user`, `assessment`) cuando `finished=False`; permiso `view_reports` | T06, T07 |
| `Assessment` | + `max_attempts` (entero, 0 = sin límite) | T07 |
| `Audit` | permiso `export_backup`; índice por `created` | T06 |

No se elimina ni se renombra ningún campo existente.

## 8. Dependencias permitidas

Producción: `Django>=5.2,<5.3`, `psycopg[binary]>=3.2,<4`, `openpyxl>=3.1,<4`, `waitress`, `whitenoise`, `nh3`, `django-axes`.
Desarrollo (`requirements-dev.txt`): `ruff`.

Quien agregue cada dependencia fija un rango de versión mayor y confirma en la bitácora que es compatible con Django 5.2 y Python 3.12. Cualquier otra dependencia requiere aprobación del arquitecto.

## 9. Variables de entorno

| Variable | Producción | Demo (`CICC_DEMO=1`) | Uso |
|---|---|---|---|
| `CICC_DEMO` | no definida | `1` | Modo local: SQLite, `DEBUG` 1 por defecto, clave de desarrollo, `seed_demo` permitido, etiqueta "ENTORNO DEMO" |
| `DJANGO_SECRET_KEY` | obligatoria | opcional | Clave secreta |
| `DEBUG` | 0 | 1 | Solo `1` lo activa |
| `CICC_ALLOWED_HOSTS` | obligatoria, separada por comas | `localhost,127.0.0.1,testserver` | Hosts aceptados |
| `CICC_CSRF_TRUSTED_ORIGINS` | si hay proxy | — | Orígenes de confianza |
| `CICC_HTTPS` | `1` si se sirve por HTTPS | — | Cookies `Secure`, HSTS, cabecera del proxy |
| `PGDATABASE`, `PGUSER`, `PGPASSWORD`, `PGHOST`, `PGPORT` | obligatorias | — | PostgreSQL |
| `QA_SQLITE` | — | alias histórico | Fuerza SQLite; se conserva por compatibilidad |
| `CICC_LOG_DIR` | opcional, por defecto `logs/` | — | Carpeta de logs |
| `CICC_LISTEN` | opcional, por defecto `127.0.0.1:8000` | — | Dirección y puerto de Waitress |
| `CICC_BACKUP_DIR` | obligatoria para los scripts de respaldo | — | Carpeta destino de respaldos, fuera del repositorio |

Un archivo `.env` en la raíz, si existe, se carga al inicio con un lector propio de pocas líneas (sin dependencia nueva). `.env` no se versiona; `.env.example` sí.

## 10. Fuera de alcance de este plan

SSO o directorio activo, envío de correo, certificados emitidos, reproductor de video, editor visual propio fuera del administrador, API pública, aplicación móvil, supervisión antifraude, internacionalización.

## 11. Preguntas abiertas para Carlos

Los implementadores no deben asumir respuestas; las tareas afectadas indican qué hacer mientras tanto.

1. ¿El servidor interno es Windows Server o Linux? (T09 documenta ambos hasta saberlo.)
2. ¿Habrá HTTPS con certificado interno? (Afecta `CICC_HTTPS`.)
3. ¿Quién administra PostgreSQL: tú o el área de infraestructura? (Afecta T10.)
4. ¿Aceptas la decisión D4 sobre los tres recursos que hoy abren cursos?
5. ¿La rama remota `mejoras-cicc` tiene trabajo que deba integrarse antes de empezar? (T01 lo reporta.)
