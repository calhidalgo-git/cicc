# T12 — Una página con teoría para cada opción del menú

**Depende de:** T05. **Tamaño:** M. **Decisiones:** D3, D5, D6. **Pedida por:** Carlos, 22-11-2026.

Esta tarea va antes que T06 y T07, que quedan en espera.

## Objetivo

Que cada opción del menú (`NAV` en `hub/permissions.py`) tenga su página con un espacio de **teoría** guardado en la base de datos. La teoría se edita sin tocar código, desde el administrador o cargando archivos con un comando, y se ve arriba del contenido actual de la sección. Carlos dará el contenido después; por ahora cada página muestra «Contenido pendiente».

## Pasos

1. **Modelo.** `SectionPage` (una fila por `slug` del menú: título, introducción en HTML y en texto plano, origen del contenido, fecha de actualización y quién lo actualizó) y `SectionBlock` (página, título, cuerpo HTML, texto plano y posición; orden por posición). El HTML se sanea con `sanitize_html` de T05 al guardar; el texto plano sale del HTML y es lo que usa la búsqueda.
2. **Todas las páginas existen.** Una migración de datos crea una `SectionPage` vacía por cada entrada de `NAV`. El comando `load_pages` también crea las que falten.
3. **Mostrar la teoría.** `templates/pages/_section.html` dibuja la introducción y los bloques arriba del bloque de cada sección. Sin teoría, un aviso discreto «Contenido pendiente». Quien tiene `hub.change_sectionpage` ve «Editar contenido», que abre el administrador. La Búsqueda global encuentra la teoría y solo muestra secciones que la persona puede abrir.
4. **Edición sin código.**
   - Administrador: `SectionPage` con sus bloques en línea y ordenables por posición. Las páginas no se crean ni se borran desde ahí. Editar página y bloques exige `hub.change_sectionpage`, que reciben Editor y Administrador en `seed_demo`.
   - `load_pages` lee `hub/content/pages/<slug>.md` o `<slug>.html`: un `#` (o `<h1>`) opcional es el título, el texto anterior al primer `##` (o `<h2>`) es la introducción y cada `##` abre un bloque. No pisa páginas editadas en el administrador, salvo con `--force`. `seed_demo` lo invoca.
   - La carpeta incluye un `README.md` con el formato y `_ejemplo.md` con texto ficticio. Los archivos que empiezan con `_` no se cargan.
5. **Respaldo y restauración.** El respaldo JSON incluye las tablas nuevas. Al restaurar con `loaddata`, el HTML de páginas, bloques, rutas y lecciones se vuelve a sanear.
6. **Pruebas.** Cada entrada de `NAV` responde 200 para un rol con acceso; aviso en la página vacía y teoría en la página con contenido; saneado; `load_pages` idempotente y `--force`; búsqueda; permisos de edición; migración reversible.

## Criterios de aceptación

- [ ] Existe una `SectionPage` por cada entrada de `NAV` después de `migrate`, y `load_pages` no crea duplicados.
- [ ] Todas las secciones muestran «Contenido pendiente» o su teoría, sin perder lo que ya mostraban.
- [ ] «Editar contenido» solo aparece a quien tiene `hub.change_sectionpage`, y solo esa persona puede guardar en el administrador.
- [ ] La Búsqueda global encuentra una frase que solo está en un bloque de teoría.
- [ ] `<script>` y atributos de eventos desaparecen al guardar, al cargar desde archivo y al restaurar.
- [ ] Las migraciones se aplican sobre una copia de `demo.sqlite3` y se revierten sin error.
- [ ] Ninguna sección supera el límite de 12 consultas de T04.
- [ ] Las pruebas pasan en SQLite y PostgreSQL; `ruff check` y `ruff format --check` sin hallazgos.

## Fuera de alcance

T06 (roles y `bootstrap_roles`), T07 (evaluaciones), el diseño visual general, un editor enriquecido y el contenido real de la organización: Carlos lo dará después.
