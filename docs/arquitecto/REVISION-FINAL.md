# Lista de revisión final (la usa el arquitecto)

El implementador de T11 **no** marca estas casillas; solo confirma que el proyecto está listo para revisarse.

## Repositorio
- [ ] `git ls-files` no contiene `.sqlite3`, `.env`, `private_storage/`, `logs/`, `staticfiles/` ni `.venv/`.
- [ ] `ruff check .` y `ruff format --check .` sin hallazgos.
- [ ] La integración continua está en verde en `main` con SQLite y PostgreSQL.
- [ ] Cada tarea tiene entrada en la bitácora con salida real de comandos.

## Configuración y seguridad
- [ ] Sin variables de entorno, `manage.py check` falla con un mensaje claro (no arranca inseguro).
- [ ] `manage.py check --deploy` sin advertencias no justificadas con la configuración de producción.
- [ ] No queda ninguna referencia a Vercel ni contraseñas demo utilizables en producción.
- [ ] `seed_demo` se niega a correr sin `CICC_DEMO=1`.
- [ ] Bloqueo de login y cambio de contraseña funcionan.
- [ ] Un participante recibe 403 en reportes, auditoría, respaldo, usuarios, roles, configuración y banco.

## Contenido
- [ ] `grep` de títulos de recursos en `hub/` y `templates/` no encuentra lógica condicionada por título.
- [ ] Los tres cursos existen como rutas con 6, 11 y 6 lecciones; su texto coincide con las plantillas originales.
- [ ] Las URLs `/qa/...` antiguas redirigen con 301.
- [ ] La búsqueda global encuentra texto de una lección de curso.
- [ ] Completar una lección de curso suma al progreso.
- [ ] HTML malicioso guardado en una lección sale saneado.

## Evaluaciones
- [ ] Editar o borrar una pregunta no cambia nota ni detalle de un intento cerrado.
- [ ] Dos inicios simultáneos producen un solo intento abierto (probado en PostgreSQL).
- [ ] `max_attempts` se respeta.
- [ ] `close_expired` cierra y califica vencidos.
- [ ] La página de examen no contiene respuestas correctas.

## Operación
- [ ] Instalación limpia siguiendo solo `docs/DESPLIEGUE.md` llega a un login funcional.
- [ ] `/healthz` responde 200 y 503 según el estado de la base.
- [ ] Respaldo y restauración probados de extremo a extremo; evidencia en la bitácora.
- [ ] Los estáticos se sirven con `DEBUG=0`.

## Documentación
- [ ] `README.md`, `ARQUITECTURA.md`, `DISEÑO.md` y `VALIDACION.md` describen el sistema real.
- [ ] Las preguntas abiertas de la arquitectura objetivo están respondidas o registradas como pendientes.
