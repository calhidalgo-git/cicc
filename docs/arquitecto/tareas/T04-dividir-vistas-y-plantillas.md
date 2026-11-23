# T04 — Dividir vistas y plantillas

**Depende de:** T03. **Tamaño:** L. **Decisiones:** D1, D7, D15.

## Objetivo

Sustituir la vista única `page()` y la plantilla única `page.html` por una vista y una plantilla por sección, **sin cambiar URLs ni lo que ve el usuario** (salvo los valores fijos indicados en el paso 6).

## Contexto

`page()` en `hub/views.py` construye, para cualquier sección, un contexto con unas 15 consultas (usuarios, auditoría, preguntas, intentos…). `templates/page.html` decide qué dibujar con una cadena de `{% if section == ... %}`. `config/urls.py` tiene todas las rutas en una línea. Las pruebas importan `NAV` desde `hub.views`.

## Pasos

1. **Red de seguridad primero.** Antes de mover nada, agrega pruebas que pasen con el código actual:
   - Cada ruta `/qa/...` (índices, las 6 semanas, las 11 semanas avanzadas y los 6 temas) responde 200 autenticado y redirige a login sin sesión; un número fuera de rango responde 404.
   - Para cada sección de `NAV`, un texto distintivo que hoy aparece en esa sección (elige uno por sección mirando `page.html`).
   Haz commit de estas pruebas por separado.
2. Crea `hub/urls.py` con todas las rutas de la app, una por línea, con los mismos patrones y nombres. `config/urls.py` queda con `admin/` y `include('hub.urls')`.
3. Crea `hub/permissions.py` con `NAV`, `GATES` y una función `visible_nav(user)`. `hub/views/__init__.py` debe seguir exportando `NAV`.
4. Convierte `hub/views.py` en el paquete `hub/views/` con los módulos de la sección 5 de la arquitectura objetivo. Mueve las funciones de Excel (`workbook_response`, plantilla, importación, reporte) a `hub/services/excel.py`, dejando en las vistas solo petición y respuesta. Es un traslado: no cambies su lógica.
5. Reemplaza `page()` por un despachador que, para `/p/<section>/`, valide sección y permiso (igual que hoy: 404 y 403) y llame a una función de sección. **Cada función consulta solo lo que su plantilla usa.**
6. Divide `page.html` en `templates/pages/<sección>.html` (las secciones que comparten diseño pueden compartir una plantilla, por ejemplo biblioteca, videoteca, enlaces y los módulos). Extrae fragmentos repetidos a `templates/partials/`. Escribe las plantillas con sangría. Al hacerlo, reemplaza estos valores fijos por datos reales:
   - `base.html`: la insignia `02` junto a Evaluaciones → número real de evaluaciones.
   - Dashboard: "12 lecciones" → total real de lecciones; "Áreas de especialización 02" → número de áreas distintas con recursos publicados; el bloque "Tu próximo desafío" → la primera evaluación que el usuario no ha aprobado (o la primera existente), con su duración y número de preguntas reales; si no hay evaluaciones, un estado vacío.
   - `base.html`: `user.groups.first.name|default:'Administrador'` → `default:'Sin rol'`.
   **No toques** las comparaciones de títulos de recursos del dashboard ni de `resource()`: son de T05.
7. Mueve las pruebas a un paquete `hub/tests/` (`test_core.py`, `test_cicc.py`, `test_config.py`, `test_pages.py`) sin cambiar su contenido más allá de las importaciones.
8. Agrega una prueba que recorra todas las secciones como `admin` y falle si alguna ejecuta más de 12 consultas (`CaptureQueriesContext`). Si una sección necesita más de forma justificada, optimiza con `select_related`, `prefetch_related` o `annotate` antes de pedir una excepción.

## Criterios de aceptación

- [ ] `hub/views.py` y `templates/page.html` ya no existen.
- [ ] Todas las pruebas anteriores a la tarea pasan sin modificar sus aserciones.
- [ ] Ninguna sección supera 12 consultas; el dashboard de un participante no consulta usuarios, grupos, auditoría ni preguntas.
- [ ] Las mismas URLs responden los mismos códigos (200, 302, 403, 404) que antes, para `ana`, `diego`, `lucia` y `admin`.
- [ ] No queda ninguno de los valores fijos del paso 6.
- [ ] Revisión visual manual en modo demo de dashboard, biblioteca, un módulo, búsqueda, lecciones, evaluaciones, un examen, resultados, banco, reportes y auditoría, a 1440 px y 390 px; anota en la bitácora cualquier diferencia visual respecto a `main`.

## Fuera de alcance

Modelos y migraciones, lógica de exámenes, permisos, contenido de cursos, cambios de diseño o de CSS más allá de lo necesario para conservar la apariencia.
