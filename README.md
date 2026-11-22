# CICC — Centro Integral de Control de Calidad

[![CI](https://github.com/calhidalgo-git/CICC/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/calhidalgo-git/CICC/actions/workflows/ci.yml)

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
python manage.py createsuperuser
```

No ejecutes `seed_demo` contra esta base: crea cuentas de demostración con una contraseña conocida.

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

Credenciales ficticias: `admin`, `ana`, `diego`, `lucia`, todos con contraseña `DemoQA!2026`. admin administra; ana participa; diego edita contenido; lucia gestiona evaluaciones y consulta reportes. El comando seed es idempotente y conserva contraseñas existentes. Nunca ejecutes seed en producción.

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
