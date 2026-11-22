# T09 — Despliegue en servidor interno

**Depende de:** T02, T07. **Tamaño:** M. **Decisiones:** D12.

## Objetivo

Que CICC pueda instalarse, arrancar como servicio y actualizarse en un servidor interno con PostgreSQL siguiendo un único documento.

## Contexto

Hoy solo existe `runserver`, que no es apto para uso real. No hay servidor de aplicación, los estáticos no se sirven con `DEBUG=0`, no hay logs en archivo ni forma de saber si la aplicación está viva. **Aún no se sabe si el servidor es Windows o Linux** (pregunta abierta 1): esta tarea entrega ambos caminos.

## Pasos

1. **Dependencias:** agrega `waitress` y `whitenoise` a `requirements.txt`.
2. **Estáticos:** middleware de WhiteNoise justo después de `SecurityMiddleware`. Fuera del modo demo, almacenamiento de estáticos comprimido con manifiesto. Quita el parámetro manual `?v=...` de `base.html`. `collectstatic` debe funcionar sin errores de referencias.
3. **Salud:** `/healthz` sin autenticación; ejecuta una consulta trivial a la base y responde `200 {"status": "ok"}` o `503 {"status": "error"}`. No revela versión, rutas ni mensajes de error. No escribe en auditoría.
4. **Logs:** `LOGGING` con archivo rotativo `cicc.log` en `CICC_LOG_DIR` (5 MB, 5 archivos) y consola; errores de `django.request` y `django.security` siempre al archivo. La carpeta se crea si no existe. En modo demo, solo consola.
5. **Scripts** en `scripts/`, en PowerShell (`.ps1`) y bash (`.sh`), equivalentes:
   - `instalar-o-actualizar`: crea el entorno virtual si falta, instala requisitos, `migrate`, `collectstatic --noinput`, `bootstrap_roles`, `load_courses`, y termina con `check --deploy`. Se detiene al primer error. No ejecuta `seed_demo`.
   - `iniciar-servidor`: lanza Waitress sobre `config.wsgi:application` en `CICC_LISTEN`, con 8 hilos.
   Ningún script contiene credenciales; todo sale de `.env` o del entorno.
6. **Tarea periódica:** documenta cómo programar `manage.py close_expired` cada 5 minutos (Programador de tareas de Windows y `cron`/temporizador de systemd).
7. **`docs/DESPLIEGUE.md`**, escrito para alguien que no conoce el proyecto:
   - Requisitos (Python 3.12, PostgreSQL, puertos).
   - Crear la base y un usuario de PostgreSQL con privilegios mínimos sobre esa base.
   - Variables de entorno a partir de `.env.example` y cómo generar la clave secreta.
   - Primera instalación paso a paso, `createsuperuser`, comprobación con `/healthz` y login.
   - Arranque como servicio: en Windows con el Programador de tareas al inicio del sistema y una cuenta de servicio; en Linux con una unidad systemd de ejemplo y un usuario sin privilegios.
   - Proxy inverso opcional con HTTPS (IIS y Nginx, configuración mínima), con la advertencia de no exponer `private_storage/`, `logs/` ni `.env`.
   - Actualización a una versión nueva y vuelta atrás (código anterior + restauración del respaldo previo).
   - Permisos de carpeta: solo la cuenta de servicio lee `.env` y escribe en `private_storage/` y `logs/`.
8. **Verificación real.** En una carpeta nueva (clon limpio), sin `CICC_DEMO`, sigue tu propio documento en tu sistema operativo hasta iniciar sesión por Waitress con `DEBUG=0`. Usa PostgreSQL si lo tienes disponible; si no, `QA_SQLITE=1` y dilo en la bitácora. Indica con claridad qué camino (Windows o Linux) verificaste y cuál quedó **sin verificar**.
9. **Pruebas:** `/healthz` 200 y 503 (simulando fallo de base); no requiere sesión; no crea registros de auditoría.

## Criterios de aceptación

- [ ] Con `DEBUG=0`, Waitress sirve la aplicación con estilos, Bootstrap y Chart.js cargando correctamente.
- [ ] `instalar-o-actualizar` es repetible: ejecutarlo dos veces seguidas no falla ni duplica datos.
- [ ] `/healthz` cumple el paso 3.
- [ ] Los errores 500 quedan en `logs/cicc.log` con traza; el navegador solo ve una página de error genérica en español (`templates/500.html`, y también `404.html` y `403.html` con el diseño existente).
- [ ] `docs/DESPLIEGUE.md` no contiene nombres de servidores, IP ni credenciales reales.
- [ ] La bitácora declara qué se verificó de verdad y qué no.

## Fuera de alcance

Contenedores, despliegue automático, alta disponibilidad, monitoreo externo, configuración real del proxy o de certificados de la organización, respaldos (T10).
