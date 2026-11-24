# T06 — Roles, permisos y administrador

**Depende de:** T04. **Tamaño:** M. **Decisiones:** D10, D11.

## Objetivo

Separar los permisos de gestión, permitir crear los roles en producción sin datos demo e impedir que `seed_demo` se ejecute fuera del modo demo.

## Contexto

- `GATES` usa `hub.view_audit` para tres cosas distintas: reportes, auditoría y respaldo. El respaldo JSON incluye intentos y auditoría de todas las personas.
- Los grupos Participante, Editor, Evaluador y Administrador solo se crean dentro de `seed_demo`, junto con cuatro cuentas de contraseña conocida.
- `hub/admin.py` registra todos los modelos sin configuración: sin columnas, sin búsqueda, y permite editar auditoría e intentos.

## Pasos

1. **Permisos nuevos** mediante `Meta.permissions`: `view_reports` en `Attempt` ("Puede ver reportes globales") y `export_backup` en `Audit` ("Puede exportar el respaldo de contenido"). Agrega un índice sobre `Audit.created`.
2. **Migración de datos** para instalaciones existentes: todo grupo que hoy tenga `view_audit` recibe también `view_reports`; el grupo `Administrador`, si existe, recibe `export_backup`. Reversible.
3. **`GATES` y vistas:** `reports` y la exportación `/report.xlsx` → `hub.view_reports`; `audit` → `hub.view_audit`; `backups` y `/backup/` → `hub.export_backup`.
4. **Comando `bootstrap_roles`:** crea o actualiza los cuatro grupos con esta matriz y nada más (no crea usuarios, no borra grupos ajenos). Idempotente y seguro en producción.

   | Grupo | Permisos |
   |---|---|
   | Participante | ninguno |
   | Editor | ver, agregar y cambiar: `resource`, `resourceversion`, `learningpath`, `lesson`; `view_sectionpage` y `change_sectionpage` (teoría de las páginas del menú, T12; decisión de Carlos, 24-11-2026) |
   | Evaluador | ver, agregar y cambiar: `question`, `assessment`; `view_audit`; `view_reports` |
   | Administrador | todos los permisos de `hub` y `auth` |

5. **`seed_demo`:** lanza `CommandError` con mensaje claro si `settings.CICC_DEMO` es falso; usa `bootstrap_roles` en lugar de definir los roles por su cuenta. El resto no cambia.
6. **Administrador Django** (`hub/admin.py`), una clase por modelo:
   - `Resource`: columnas título, área, tipo, publicado; filtros por área, tipo y publicado; búsqueda por título y descripción; versiones en línea.
   - `Assessment`: preguntas en línea; `Question` ejecuta su validación `clean()` al guardar.
   - `Attempt` y `Audit`: solo lectura (sin agregar ni cambiar; borrar solo superusuario); columnas útiles, filtro por fecha y búsqueda por usuario.
   - `Progress`: solo lectura. Nadie lo borra, tampoco un superusuario (decisión de Carlos, 24-11-2026).
7. **Pruebas.** Cambio de comportamiento autorizado: en `test_excel_and_backup`, `lucia` (Evaluador) ahora recibe **403** en `POST /backup/`; agrega que `admin` recibe 200. Además:
   - Matriz completa: para cada rol y cada sección restringida, el código esperado (200 o 403).
   - `bootstrap_roles` dos veces deja los mismos permisos; no crea usuarios.
   - `seed_demo` falla con `CICC_DEMO` falso (`override_settings`).
   - Un Evaluador no puede cambiar un `Attempt` ni un `Audit` desde el administrador.
   - La migración de datos conserva el acceso a reportes de un grupo que tenía `view_audit`.

## Criterios de aceptación

- [ ] En una base vacía con `CICC_DEMO` sin definir: `migrate`, `bootstrap_roles` y `createsuperuser` dejan un sistema utilizable sin ninguna cuenta demo.
- [ ] `seed_demo` sin `CICC_DEMO=1` termina con error y no escribe nada.
- [ ] Solo el rol Administrador (o un superusuario) puede descargar el respaldo.
- [ ] El administrador de `Attempt` y `Audit` no ofrece botones de agregar ni guardar.
- [ ] Las pruebas pasan en SQLite y PostgreSQL.

## Fuera de alcance

Pantallas propias de gestión de usuarios fuera del administrador, autorización por área (Mainframe/Distribuido siguen siendo filtros), auditoría inmutable, cambios en el contenido del respaldo.
