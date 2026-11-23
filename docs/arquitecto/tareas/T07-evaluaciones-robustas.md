# T07 — Evaluaciones robustas

**Depende de:** T04. **Tamaño:** L. **Decisiones:** D8, D9.

## Objetivo

Que el resultado de una evaluación sea estable en el tiempo y correcto bajo concurrencia, y cerrar los riesgos conocidos de importación y exportación Excel.

## Contexto

- `grade()` y `results()` leen las preguntas vivas de la evaluación. Si un evaluador edita o borra una pregunta, cambia el detalle (y potencialmente la nota mostrada) de intentos ya cerrados, y un intento en curso puede quedar con respuestas a preguntas inexistentes.
- `start()` busca un intento abierto y, si no hay, crea uno: dos peticiones simultáneas crean dos.
- Los intentos vencidos solo se cierran si el usuario vuelve a guardar.
- `ARQUITECTURA.md` ya advierte de inyección de fórmulas en exportaciones y de límites de descompresión en importaciones.

## Pasos

1. **Servicio.** Crea `hub/services/exams.py` con `start_attempt(user, assessment)`, `save_answers(attempt, data)`, `finish_attempt(attempt)`, `grade(attempt)` y `close_expired(now=None)`. Las vistas solo traducen petición y respuesta. Conserva los códigos HTTP actuales (400, 409) y el formato JSON.
2. **Copia de preguntas.** `Attempt.snapshot` (`JSONField`, lista de objetos `{id, text, options, correct, explanation}` en el orden mostrado). Se llena al iniciar. La página de examen, la validación de respuestas, la nota y los resultados leen **solo** de `snapshot`. Las claves de `answers` siguen siendo el `id` de la pregunta como texto.
   Migración de datos: para cada intento existente, llena `snapshot` con las preguntas actuales de su evaluación. Reversible (vacía el campo).
3. **Un intento abierto.** Restricción única (`user`, `assessment`) con condición `finished=False`. La migración, antes de crearla, cierra y califica los intentos abiertos duplicados conservando abierto el más reciente. `start_attempt` usa una transacción y, ante `IntegrityError`, devuelve el intento abierto existente.
4. **Límite de intentos.** `Assessment.max_attempts` (entero positivo, por defecto 0 = sin límite). Si el usuario ya tiene ese número de intentos cerrados, `start` responde 403 con un mensaje claro y el catálogo muestra "Intentos agotados" en lugar del botón. El catálogo muestra los intentos usados y disponibles cuando hay límite.
5. **Vencidos.** Comando `close_expired` que cierra y califica todo intento abierto con `deadline` pasado e informa cuántos cerró. Las vistas `exam` y `results` también cierran el intento si está vencido al consultarlo.
6. **Excel.**
   - Exportación de reportes: toda celda de texto que empiece con `=`, `+`, `-`, `@`, tabulador o retorno de carro se escribe precedida de un apóstrofo.
   - Importación: antes de `load_workbook`, abre el archivo con `zipfile` y rechaza si la suma de tamaños descomprimidos supera 20 MB o hay más de 200 entradas. Conserva los límites y mensajes actuales.
7. **Pruebas.**
   - Editar el enunciado, cambiar la opción correcta y borrar una pregunta después de cerrar un intento: nota y detalle no cambian.
   - Lo mismo con un intento en curso: el examen sigue mostrando las preguntas originales y se califica con ellas.
   - La respuesta HTML del examen no contiene el texto de ninguna explicación ni el campo `correct` (ni dentro de bloques `<script>`).
   - Segundo `start` con intento abierto devuelve el mismo intento.
   - Concurrencia: `TransactionTestCase` con dos hilos iniciando a la vez produce un solo intento abierto; se omite en SQLite con `skipUnless(connection.vendor == 'postgresql')`.
   - `max_attempts`: permitido hasta el límite, 403 después; 0 no limita.
   - `close_expired` cierra solo vencidos y es idempotente.
   - Reporte con un usuario llamado `=cmd` exporta `'=cmd`.
   - Importación rechaza un XLSX cuyo contenido descomprimido excede el límite.
   - La migración sobre datos con dos intentos abiertos duplicados deja uno.

## Criterios de aceptación

- [ ] Ninguna función de vista ni plantilla de examen o resultados accede a `assessment.questions` para un intento ya iniciado.
- [ ] Las pruebas originales de exámenes pasan sin cambiar sus aserciones.
- [ ] La prueba de concurrencia pasa en el trabajo de PostgreSQL de la integración continua.
- [ ] Las migraciones se aplican sobre una copia de `demo.sqlite3` que tenga intentos, sin error.
- [ ] Prueba manual en modo demo: iniciar, responder, recargar, finalizar; el autoguardado y el temporizador funcionan igual que antes.

## Fuera de alcance

Preguntas aleatorias o por banco, tipos de pregunta nuevos, asignación por equipos, supervisión, cambios en el JavaScript del examen más allá de leer la nueva fuente de preguntas.
