# T10 — Respaldos y restauración

**Depende de:** T09. **Tamaño:** S.

## Objetivo

Tener un respaldo completo automatizable (base de datos + adjuntos) y una restauración **probada**.

## Contexto

`ARQUITECTURA.md` describe un respaldo manual con `pg_dump` y copia de `private_storage`. Nunca se ha probado una restauración. El respaldo JSON de la aplicación solo cubre contenido y no sustituye al respaldo completo.

## Pasos

1. **`scripts/respaldar` (`.ps1` y `.sh`):**
   - Requiere `CICC_BACKUP_DIR`; falla si no está definida o si apunta dentro del repositorio.
   - Crea una carpeta `cicc-AAAAMMDD-HHMMSS` con: `db.dump` (`pg_dump -Fc`), copia de `private_storage/` y `manifiesto.txt` (fecha, commit de git, versión de PostgreSQL, número de archivos adjuntos y tamaño total).
   - La contraseña llega por `PGPASSWORD` o por el archivo de contraseñas de PostgreSQL; nunca como argumento ni escrita en el script.
   - Elimina respaldos con más de `CICC_BACKUP_KEEP_DAYS` días (por defecto 14), solo carpetas cuyo nombre cumpla el patrón `cicc-*`.
   - Código de salida distinto de cero ante cualquier fallo, y no borra respaldos antiguos si el nuevo falló.
2. **`scripts/restaurar` (`.ps1` y `.sh`):** recibe la carpeta del respaldo y el nombre de una base **destino**. Se niega a continuar si la base destino no está vacía o si la carpeta `private_storage` destino existe y no está vacía. Restaura con `pg_restore`, copia adjuntos y ejecuta `manage.py check` y `migrate --check`.
3. **Interfaz:** en la sección Respaldos, cambia el texto para dejar claro que la descarga es una "exportación de contenido" y enlaza conceptualmente al procedimiento completo (texto, sin enlaces a archivos del servidor).
4. **`docs/RESPALDOS.md`:** qué cubre cada tipo de respaldo, cómo programar el respaldo nocturno (Windows y Linux), dónde guardar las copias (otro disco o servidor), cómo restaurar paso a paso, y recomendación de un simulacro de restauración trimestral.
5. **Simulacro obligatorio.** Con PostgreSQL local: carga datos, sube un adjunto, completa una lección y un intento; respalda; restaura en una base nueva; arranca la aplicación contra la base restaurada y comprueba que el login, el progreso, el intento y la descarga del adjunto funcionan. Copia la evidencia (comandos y resultados) en la bitácora.
   **Si no tienes PostgreSQL disponible, no marques la tarea como terminada:** déjala `Bloqueada` e indícalo.

## Criterios de aceptación

- [ ] El simulacro del paso 5 está documentado con salida real en la bitácora.
- [ ] `restaurar` se niega a escribir sobre una base o carpeta con datos (probado).
- [ ] `respaldar` falla con mensaje claro sin `CICC_BACKUP_DIR` y cuando `pg_dump` no está disponible.
- [ ] Ningún script ni documento contiene credenciales o rutas reales de la organización.

## Fuera de alcance

Respaldo desde la interfaz web, cifrado de respaldos, replicación, envío a la nube, respaldo de SQLite.
