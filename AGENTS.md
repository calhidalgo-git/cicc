# Reglas para modelos que trabajan en CICC

Este repositorio tiene un arquitecto. Tú eres un implementador: ejecutas **una tarea** de `docs/arquitecto/tareas/` exactamente como está escrita. Las decisiones de diseño ya están tomadas en `docs/arquitecto/ARQUITECTURA-OBJETIVO.md`; no las cambies.

## Antes de empezar

1. Lee `docs/arquitecto/ARQUITECTURA-OBJETIVO.md` completo.
2. Abre `docs/arquitecto/PLAN.md` y toma la primera tarea en estado `Pendiente` cuyas dependencias estén en `Hecha`. No tomes otra.
3. Lee el archivo de esa tarea completo, incluida la sección "Fuera de alcance".
4. Ejecuta `git status`. Si hay cambios sin confirmar que no son tuyos, detente y avisa a Carlos; no los descartes ni los incluyas.

## Cómo trabajar

- Una tarea = una rama `tarea/TNN-nombre-corto` creada desde `main` actualizado = un pull request hacia `main`. No mezcles tareas.
- Cambia solo lo que la tarea pide. Si ves otro problema, anótalo en la bitácora bajo "Observaciones"; no lo arregles.
- Si la tarea es ambigua, contradice el código real o un paso no se puede cumplir, **no adivines**: escribe la duda en la bitácora bajo "Preguntas para el arquitecto", deja la tarea en `Bloqueada` y detente.
- No agregues dependencias fuera de las listadas en la sección 8 de la arquitectura objetivo.
- No borres ni debilites pruebas existentes para que pasen. Si una prueba debe cambiar porque la tarea cambia el comportamiento, la tarea lo dice de forma explícita.
- Toda migración debe ser reversible o indicar por qué no lo es, y debe aplicarse sin pérdida sobre una base que ya tiene datos.
- Interfaz, mensajes y documentación en español. Identificadores de código en inglés, como el código existente.
- Código nuevo o tocado: formateado con `ruff format`, una sentencia por línea. No escribas código compactado en una sola línea.
- Nunca escribas credenciales, nombres de servidores, direcciones IP ni datos reales de la organización en el repositorio. Los ejemplos son ficticios.
- No ejecutes `seed_demo` contra una base que no sea de demostración.
- No hagas `git push --force`, no reescribas el historial de `main` y no fusiones tu propio pull request: lo aprueba Carlos.

## Definición de terminado

Una tarea está terminada solo si se cumple todo esto:

1. Cada criterio de aceptación de la tarea se cumple y lo comprobaste tú mismo.
2. Con `CICC_DEMO=1` (o `QA_SQLITE=1` antes de la tarea T02) pasan:
   - `python manage.py check`
   - `python manage.py makemigrations --check --dry-run`
   - `python manage.py test hub`
   - `ruff check .` y `ruff format --check .` (desde la tarea T01)
3. Agregaste pruebas para el comportamiento nuevo.
4. Agregaste tu entrada en `docs/arquitecto/BITACORA.md` con el formato indicado allí, incluyendo la salida real de los comandos del punto 2. No escribas "pasa" sin haberlo ejecutado; si no pudiste ejecutar algo, dilo.
5. Cambiaste el estado de la tarea en `docs/arquitecto/PLAN.md` a `En revisión`.

## Comandos de referencia (Windows PowerShell)

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
$env:CICC_DEMO='1'      # antes de T02: $env:QA_SQLITE='1'; $env:DEBUG='1'
python manage.py migrate
python manage.py seed_demo
python manage.py test hub -v 2
python manage.py runserver 127.0.0.1:8000
```
