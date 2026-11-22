# T03 — Integración continua

**Depende de:** T02. **Tamaño:** S. **Decisiones:** D3, D15.

## Objetivo

Que cada pull request ejecute automáticamente estilo y pruebas en SQLite y en PostgreSQL, para que ningún implementador pueda declarar "pasa" sin evidencia.

## Contexto

El repositorio está en GitHub (`origin`). Hasta ahora las pruebas solo se han ejecutado en SQLite; `VALIDACION.md` lista PostgreSQL como pendiente.

## Pasos

1. Crea `.github/workflows/ci.yml` que se ejecute en `push` a `main` y en todo `pull_request`, con Python 3.12 y caché de pip.
2. Trabajo `estilo`: instala `requirements-dev.txt`; ejecuta `ruff check .` y `ruff format --check .`.
3. Trabajo `pruebas-sqlite`: con `CICC_DEMO=1` ejecuta `manage.py check`, `makemigrations --check --dry-run` y `test hub -v 2`.
4. Trabajo `pruebas-postgres`: servicio `postgres:16` con comprobación de salud; variables `PGDATABASE`, `PGUSER`, `PGPASSWORD`, `PGHOST=localhost`, `DJANGO_SECRET_KEY` (valor ficticio escrito en el flujo, solo para pruebas) y `CICC_ALLOWED_HOSTS=localhost,testserver`; sin `CICC_DEMO`. Ejecuta los mismos tres comandos. El usuario del servicio debe poder crear la base de pruebas.
5. Si alguna prueba falla solo en PostgreSQL, **no la desactives**: corrige la prueba únicamente si el defecto está en la prueba; si está en el código, anótalo en "Preguntas para el arquitecto" y deja la tarea `Bloqueada`.
6. Agrega la insignia del flujo al inicio de `README.md`.

## Criterios de aceptación

- [ ] Los tres trabajos aparecen y terminan en verde en el pull request de esta tarea.
- [ ] El flujo no contiene secretos reales ni depende de secretos del repositorio.
- [ ] Un commit de prueba con un error de formato hace fallar `estilo` (compruébalo en una rama aparte y descártala; anota el enlace o la salida).

## Fuera de alcance

Despliegue automático, cobertura de código, análisis de seguridad, publicación de artefactos.
