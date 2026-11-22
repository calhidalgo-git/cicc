# T11 — Documentación y cierre

**Depende de:** todas las anteriores en `Hecha`. **Tamaño:** S.

## Objetivo

Que la documentación describa el sistema tal como quedó y que el proyecto esté listo para la revisión final del arquitecto.

## Contexto

`README.md`, `ARQUITECTURA.md`, `DISEÑO.md`, `VALIDACION.md` e `INSTRUCCIONES-WINDOWS.md` describen el prototipo anterior al plan. `CAMBIOS-CICC.md` es un registro histórico.

## Pasos

1. **`README.md`:** qué es CICC, inicio rápido en modo demo (`START-DEMO.ps1`), enlace a `docs/DESPLIEGUE.md` y `docs/RESPALDOS.md`, cómo ejecutar pruebas y estilo, roles, y una sección "Límites conocidos" actualizada. Elimina afirmaciones que ya no son ciertas (prototipo, 12 pruebas, credenciales demo presentadas como acceso general).
2. **`ARQUITECTURA.md`:** diagrama y modelo de datos actualizados (campos y restricciones nuevos), matriz de permisos real, flujo de exámenes con copia de preguntas, estructura de código, variables de entorno. Sustituye la sección de respaldo por un enlace a `docs/RESPALDOS.md`.
3. **`DISEÑO.md`:** inventario de pantallas y mapa de navegación con las rutas `/rutas/...`, `/cuenta/clave/` y las redirecciones de `/qa/...`.
4. **`INSTRUCCIONES-WINDOWS.md`:** solo modo demo local; para servidor, remite a `docs/DESPLIEGUE.md`.
5. **`VALIDACION.md`:** fecha, versiones, número real de pruebas y resultado en SQLite y PostgreSQL (con enlace a la ejecución de integración continua), y pendientes reales.
6. **`CAMBIOS-CICC.md`:** no lo reescribas; agrega al final una sección "Plan de arquitectura (noviembre 2026)" con un párrafo por tarea y un apartado "Al actualizar una instalación existente" con el orden de comandos.
7. **Coherencia:** busca en todo el repositorio (sin `.venv`, `.git`) menciones a Vercel, `QA_SQLITE` como mecanismo principal, `page.html`, `hub/views.py`, rutas `/qa/` como vigentes y cifras antiguas; corrige las que queden en documentación.
8. **Autoevaluación:** en tu entrada de bitácora, recorre `docs/arquitecto/REVISION-FINAL.md` punto por punto e indica para cada uno "cumple", "no cumple" o "no verificado", con la evidencia. **No marques las casillas del archivo**: las marca el arquitecto.
9. Lista en la bitácora las preguntas abiertas de la sección 11 de la arquitectura objetivo que sigan sin respuesta y todas las "Observaciones" acumuladas de tareas anteriores, agrupadas, como insumo para una fase siguiente.

## Criterios de aceptación

- [ ] Un lector nuevo puede levantar la demo siguiendo solo `README.md`.
- [ ] Ningún documento describe funcionalidad que no existe ni omite las rutas, roles y comandos nuevos.
- [ ] La autoevaluación cubre todos los puntos de `REVISION-FINAL.md`.
- [ ] Esta tarea no modifica código Python, plantillas, migraciones ni scripts. Si detectas un defecto, va a "Observaciones".

## Fuera de alcance

Cualquier cambio de código, manual de usuario final, capturas de pantalla, material de capacitación.
