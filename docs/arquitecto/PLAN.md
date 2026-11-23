# Plan de trabajo

Estados: `Pendiente` → `En curso` → `En revisión` → `Hecha` (solo Carlos o el arquitecto marcan `Hecha`). `Bloqueada` si hay una pregunta abierta.

Las tareas se ejecutan en orden. Una tarea puede empezar solo cuando todas sus dependencias están en `Hecha` y fusionadas en `main`.

| Tarea | Título | Depende de | Tamaño | Estado |
|---|---|---|---|---|
| [T01](tareas/T01-higiene-y-linea-base.md) | Higiene del repositorio y línea base | — | M | Hecha |
| [T02](tareas/T02-configuracion-por-entorno.md) | Configuración por entorno | T01 | M | Hecha |
| [T03](tareas/T03-integracion-continua.md) | Integración continua | T02 | S | Hecha |
| [T04](tareas/T04-dividir-vistas-y-plantillas.md) | Dividir vistas y plantillas | T03 | L | Hecha |
| [T05](tareas/T05-cursos-al-modelo.md) | Cursos al modelo de datos | T04 | L | En revisión |
| [T06](tareas/T06-roles-y-permisos.md) | Roles, permisos y administrador | T04 | M | Pendiente |
| [T07](tareas/T07-evaluaciones-robustas.md) | Evaluaciones robustas | T04 | L | Pendiente |
| [T08](tareas/T08-seguridad-de-acceso.md) | Seguridad de acceso | T02, T06 | M | Pendiente |
| [T09](tareas/T09-despliegue-servidor-interno.md) | Despliegue en servidor interno | T02, T07 | M | Pendiente |
| [T10](tareas/T10-respaldos.md) | Respaldos y restauración | T09 | S | Pendiente |
| [T11](tareas/T11-documentacion-y-cierre.md) | Documentación y cierre | todas | S | Pendiente |

**Decisiones de Carlos (22-11-2026).** Aprobó de forma expresa T02, T03 y T04, que pasan a `Hecha`. En T03 aceptó la evidencia local, es decir, las pruebas ejecutadas en su PC, en lugar de los tres trabajos en verde en un pull request de GitHub, porque el proyecto no tiene remoto.

T05, T06 y T07 tocan áreas distintas, pero las tres generan migraciones. Ejecútalas **una tras otra**, no en paralelo, para evitar migraciones en conflicto.

## Fases

- **Fase 0 — Base (T01–T03).** Código legible, configuración segura y pruebas automáticas en cada cambio. Sin cambios visibles para el usuario.
- **Fase 1 — Estructura (T04–T06).** Vistas y plantillas separadas, contenido en la base, roles reales.
- **Fase 2 — Robustez (T07–T08).** Evaluaciones consistentes y acceso protegido.
- **Fase 3 — Operación (T09–T11).** Instalación en el servidor, respaldos, documentación.

## Revisión final

Al quedar T11 en `En revisión`, Carlos abre una sesión con el arquitecto. El arquitecto recorre `REVISION-FINAL.md` contra el código real y la bitácora.
