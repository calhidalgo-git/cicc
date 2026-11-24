# CICC — Centro Integral de Control de Calidad

**Integración continua:** `.github/workflows/ci.yml` revisa el estilo y ejecuta las pruebas en SQLite y en PostgreSQL. Este proyecto todavía no tiene un repositorio remoto aprobado, así que no muestra insignia de estado; los resultados de cada tarea se registran en `docs/arquitecto/BITACORA.md`.

Ampliación del ZIP original, con 32 recursos, 16 lecciones y búsqueda global de recursos publicados, academia, rutas y evaluaciones. Incluye conocimiento del área, ambiente de certificación, mapa conceptual navegable, Mainframe, Distribuido, ciclo de vida y pruebas, QA/ClearQuest, procedimientos, incidentes y glosario. Todos los escenarios y accesos son ficticios.

**Windows, demo sin PostgreSQL:** extrae el ZIP y ejecuta `powershell -ExecutionPolicy Bypass -File .\START-DEMO.ps1` desde la carpeta `cicc`. Consulta [INSTRUCCIONES-WINDOWS.md](INSTRUCCIONES-WINDOWS.md). Acceso: `admin` / `DemoQA!2026`.

**Validación CICC:** 12 pruebas aprobadas con SQLite. Consulta [VALIDACION.md](VALIDACION.md) y [CAMBIOS-CICC.md](CAMBIOS-CICC.md). El ambiente de certificación es formativo y ClearQuest se describe sin integración. La aplicación solo requiere Python y librerías abiertas; no requiere los productos comerciales estudiados.


Prototipo Django navegable en español para personal QA Mainframe y Distribuido. Todas las herramientas son gratuitas y de código abierto. No requiere servicios de pago ni conexión para su interfaz: Bootstrap y Chart.js se incluyen localmente.

## Demo local (Windows PowerShell)

Instala Python 3.12. La forma más simple es `START-DEMO.ps1`. A mano, desde esta carpeta:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
$env:CICC_DEMO='1'
python manage.py migrate
python manage.py seed_demo
python manage.py runserver 127.0.0.1:8000
```

`CICC_DEMO=1` activa el modo de demostración: SQLite en `demo.sqlite3`, `DEBUG` activo y una clave de desarrollo. Abre http://127.0.0.1:8000.

## Instalación con PostgreSQL

Sin `CICC_DEMO` la aplicación arranca en modo producción: `DEBUG` queda desactivado y se exigen `DJANGO_SECRET_KEY`, `CICC_ALLOWED_HOSTS` y las variables `PG*`. Crea primero una base y un usuario con acceso. Las variables pueden ir en el entorno o en un archivo `.env` en la raíz (copia `.env.example` y completa los valores).

```powershell
$env:PGDATABASE='cicc'
$env:PGUSER='cicc_app'
$env:PGPASSWORD='tu-clave'
$env:PGHOST='localhost'
$env:DJANGO_SECRET_KEY=python -c "import secrets; print(secrets.token_urlsafe(64))"
$env:CICC_ALLOWED_HOSTS='cicc.ejemplo.local'
python manage.py migrate
python manage.py load_courses
python manage.py bootstrap_roles
python manage.py createsuperuser
```

`bootstrap_roles` crea o actualiza los cuatro roles con sus permisos. No crea cuentas ni toca otros grupos, y se puede repetir: vuelve a dejar cada rol con su lista de permisos. Si la base no tiene todas las migraciones, o falta uno de los permisos de los roles, se detiene sin cambiar nada y pide ejecutar `migrate`.

| Rol | Puede |
|---|---|
| Participante | Estudiar, rendir evaluaciones y ver sus resultados. |
| Editor | Ver, agregar y cambiar recursos, versiones, rutas, lecciones y la teoría de las páginas del menú. |
| Evaluador | Ver, agregar y cambiar evaluaciones y preguntas; ver la auditoría y los reportes. |
| Administrador | Todos los permisos de la aplicación y de las cuentas. Es el único que descarga el respaldo. |

Asigna los roles a cada persona desde `/admin/`, en Usuarios. El primer administrador lo crea `createsuperuser`.

`seed_demo` se niega a correr sin `CICC_DEMO=1`, porque crea cuentas de demostración con una contraseña conocida.

**Actualizar desde una versión anterior a T06.** Al migrar, todo grupo que podía ver la auditoría recibe también el permiso de reportes, así que conserva el acceso. El grupo `Administrador` recibe el permiso de respaldo. Otros grupos que abrían Respaldos dejan de hacerlo. Después ejecuta `bootstrap_roles` para dejar los cuatro roles con la lista completa. Si vuelves a una versión anterior (`migrate hub 0009`), los dos permisos nuevos se borran, también de las cuentas a las que se dieron directamente. Los intentos y la auditoría son de solo lectura en el administrador, y solo un superusuario los borra. El avance de las personas no lo borra nadie.

| Variable | Uso |
|---|---|
| `CICC_DEMO` | `1` activa el modo de demostración local. Sin definir: modo producción. |
| `DEBUG` | Solo `1` lo activa. En modo demo vale `1` salvo `DEBUG=0`. |
| `DJANGO_SECRET_KEY` | Obligatoria en producción; se rechazan las claves de ejemplo publicadas. |
| `CICC_ALLOWED_HOSTS` | Obligatoria en producción: hosts separados por comas. |
| `CICC_CSRF_TRUSTED_ORIGINS` | Orígenes de confianza para CSRF (si hay proxy), separados por comas. |
| `CICC_HTTPS` | `1` si se sirve por HTTPS: cookies seguras, redirección y HSTS. |
| `PGDATABASE`, `PGUSER`, `PGPASSWORD`, `PGHOST`, `PGPORT` | Conexión PostgreSQL; `PGPORT` es opcional (5432). |
| `QA_SQLITE` | Alias histórico: `1` usa SQLite sin relajar las demás reglas. |

Credenciales ficticias: `admin`, `ana`, `diego`, `lucia`, todos con contraseña `DemoQA!2026`. admin administra y descarga el respaldo; ana participa; diego edita contenido; lucia gestiona evaluaciones y consulta reportes y auditoría. El comando seed es idempotente y conserva contraseñas existentes. Solo corre con `CICC_DEMO=1`.

## Cursos: actualizar, restaurar y revertir

Los tres cursos oficiales (`fundamentos-qa`, `qa-avanzado` y `certificacion-requerimiento`) vienen en `hub/content/courses/` y solo `load_courses` los crea. Su dirección está reservada: una ruta propia que se llame igual, por ejemplo «Fundamentos QA», recibe otra (`fundamentos-qa-2`) y conserva sus lecciones y su avance. El administrador no permite elegir una dirección reservada ni cambiar la de un curso oficial.

**Actualizar desde una versión anterior a T05.** Haz primero un respaldo de la base. Después:

```powershell
python manage.py migrate
python manage.py load_courses
```

`load_courses` crea los cursos que falten. Al crearlos, vincula con su curso los recursos que lo abrían antes, como «Guía de pruebas batch y JCL», «Checklist de pruebas de API REST» e «Introducción a DB2 para QA». Solo toca los recursos sin ruta asignada. Si hay dos o más recursos con uno de esos títulos, no vincula ninguno y avisa: elige en el administrador cuál abre el curso. Si algún recurso ya abre el curso, no vincula otro, aunque tenga el título antiguo de un recurso histórico renombrado. Sin `--force` no modifica lo que ya existe.

Si en un curso oficial una lección oficial está fuera de su posición, por ejemplo porque hay lecciones propias antes de ella, `load_courses` no reescribe ni crea ninguna lección de ese curso, ni siquiera con `--force`, y avisa. Pasa en bases que aplicaron la T05 anterior al 24-11-2026 con ejercicios propios en la posición 0. Ordena las lecciones en el administrador, en un solo guardado, y vuelve a ejecutar el comando. Una lección oficial se reconoce por su título o por su texto, así que también se protege el curso si, por ejemplo, la semana 6 renombrada quedó en la posición 7. Una práctica propia que repite el título de una semana que ya está en su lugar no bloquea la carga.

**Si ya aplicaste la T05 anterior** y los tres recursos históricos quedaron sin abrir su curso, ejecuta:

```powershell
python manage.py load_courses --relink
```

Solo vincula con su curso los recursos históricos que no abren ninguna ruta. No crea ni reescribe rutas ni lecciones, así que conserva tus ediciones, y no cambia un recurso que ya abre otra ruta. Si desvinculaste uno de esos recursos a propósito, vuelve a quitarle la ruta en el administrador después.

**Restaurar un respaldo JSON (`/backup/`).** Se admite el archivo de T04 y el de T05. Restaura en una base vacía de contenido: `migrate` y las cuentas, sin `seed_demo` ni `load_courses`. Después ejecuta `load_courses`:

```powershell
python manage.py migrate
python manage.py loaddata cicc-content-backup.json
python manage.py load_courses
```

El respaldo no incluye las cuentas: las personas que aparecen en el avance, los intentos y la auditoría deben existir antes, con el mismo nombre de usuario. El respaldo las guarda por ese nombre, no por su número interno, así que no importa en qué orden se crearon; si falta una, `loaddata` se detiene sin aplicar nada. Un respaldo exportado antes del 23-11-2026 guarda los números internos: solo se restaura bien si las cuentas tienen los mismos números que en el origen. Vuelve a exportarlo. Un respaldo de T04 no trae direcciones de ruta. Cada ruta recibe una propia, nunca la de un curso oficial. Si dos lecciones de una ruta comparten posición, la segunda pasa al final. Si el respaldo ocuparía un curso oficial que ya está en la base, `loaddata` se detiene sin aplicar nada.

Las páginas de sección del menú se guardan en el respaldo por su clave (`dashboard`, `glossary`, …) y no por su número interno. La teoría y sus bloques llegan a la sección con esa clave, aunque la instalación nueva la haya creado con otro número, por ejemplo después de revertir y volver a aplicar la migración 0009. Restaurar el mismo respaldo dos veces no duplica secciones ni bloques. Un respaldo exportado con la versión anterior de T12 guarda los números internos y puede fallar en otra instalación: vuelve a exportarlo.

**Revertir las migraciones de cursos** (`migrate hub 0003`). Se conservan las rutas, las lecciones, el texto plano y el avance. Se pierden la dirección, la posición de la ruta, el HTML de introducciones y lecciones y el vínculo de los recursos con su curso. Al volver a migrar, un curso recupera su dirección oficial solo si conserva exactamente su contenido: título, área, descripción y, en cada posición del curso, una sola lección con el título y el texto oficiales. Se admiten lecciones propias después de la última lección oficial, pero no antes ni en una posición repetida. Cualquier otra ruta, aunque copie el nombre, los títulos o el orden del curso, queda como ruta propia con otra dirección, su texto y su avance; `load_courses` crea entonces el curso oficial aparte. Esto incluye un curso oficial editado a mano. Si dos rutas cumplen estas condiciones, o si otra ruta, se llame como se llame, conserva el título o el texto de alguna lección oficial en su posición (por ejemplo, el curso oficial con lecciones editadas o con otro nombre), no se puede saber cuál es la oficial: todas quedan como rutas propias, `load_courses` crea el curso aparte y el avance sigue en la ruta propia. Para devolverlo al curso, restaura el respaldo hecho antes de revertir, de una de estas dos formas, siempre **antes** de ejecutar `load_courses`:

- en la misma base, justo después de volver a migrar (`loaddata cicc-content-backup.json`). Funciona con respaldos exportados desde el 24-11-2026, que guardan las rutas en el orden en que reciben su dirección;
- o en una base nueva: `migrate`, crear las cuentas con los mismos nombres de usuario y `loaddata`. Es la opción para un respaldo anterior, y la que funciona siempre.

Para recuperar el resto, elige una de estas opciones:

- `python manage.py load_courses --force` repone el contenido distribuido y los vínculos de los recursos históricos. Solo reescribe las rutas con dirección oficial, que tras volver a migrar son las que no tenían ediciones.
- Para conservar esas ediciones, haz un respaldo JSON **antes** de revertir. Vuelve a migrar y restáuralo con `loaddata` **antes** de ejecutar `load_courses`.

**Límites conocidos** (aceptados por Carlos el 24-11-2026):

- Restaurar en la misma base después de revertir puede fallar si dos rutas propias tenían direcciones personalizadas que se cruzan (por ejemplo, la ruta A con la dirección `ruta-b`). `loaddata` se detiene sin aplicar nada. Restaura entonces en una base nueva.
- Si otro recurso ya abre un curso, `load_courses --relink` no vincula el recurso histórico de ese curso. Asígnalo en el administrador.
- Las comprobaciones de la dirección oficial en las operaciones en lote hechas desde código (`update()`) no cubren una ruta creada al mismo tiempo desde otra conexión. Las pantallas y los comandos no hacen esas operaciones.

## Qué puedes probar

1. Ingresa como ana; busca «batch», filtra Mainframe y abre la versión 2 de una guía. Descarga el archivo protegido.
2. Abre rutas, entra a lecciones y completa una. Comprueba el contador del dashboard.
3. Inicia una evaluación. Responde, espera el indicador de guardado y recarga: la selección se recupera. Finaliza y revisa puntaje y explicación.
4. Como lucia, descarga la plantilla del banco de preguntas e impórtala. Una fila inválida debe rechazar todo el lote. Exporta resultados a Excel.
5. Como admin, gestiona recursos, versiones, usuarios y grupos desde los enlaces al administrador Django. Revisa auditoría y exporta contenido.
6. Como ana, intenta entrar a `/p/users/` o descargar `/report.xlsx`: debe responder 403.

## Pruebas

```powershell
$env:CICC_DEMO='1'
python manage.py check
python manage.py test hub -v 2
```

Las pruebas cubren acceso por rol, pantallas, recuperación de intentos, cálculo de notas, aislamiento entre usuarios, expiración, respuestas inválidas, progreso idempotente, descargas protegidas, búsqueda, Excel y rollback de importación. Para verificar PostgreSQL, quita CICC_DEMO, define las variables de producción, configura una base de pruebas y ejecuta el mismo comando con un usuario autorizado a crear bases. El servidor de desarrollo es para revisión local.

## Límites del prototipo

- Videoteca navegable con fichas y referencias públicas; no se adjuntan grabaciones. Puedes adjuntar archivos desde versiones en el administrador. El reproductor de video local es una extensión pendiente.
- CRUD de recursos, rutas, lecciones, preguntas, usuarios y roles mediante Django Admin. No se ha creado un editor visual alternativo para cada entidad.
- Configuración muestra parámetros reales; infraestructura se cambia por variables de entorno, evaluaciones por el administrador.
- Respaldo web exporta contenido JSON; el respaldo completo y su restauración son operaciones de infraestructura documentadas en ARQUITECTURA.md.
- Catálogos publicados visibles a todos los participantes autenticados. Mainframe/Distribuido son filtros, no barreras de autorización.
- Cada evaluación debe mantener sus preguntas y opciones estables durante los intentos. La congelación de un examen por versión, límites de intentos y asignación por cohortes quedan para una fase posterior.
- No contiene correo, recuperación de contraseña, SSO, supervisión antifraude ni emisión de certificados.

Consulta [DISEÑO.md](DISEÑO.md) para navegación, pantallas y estilos, y [ARQUITECTURA.md](ARQUITECTURA.md) para datos, permisos, seguridad y respaldos.
