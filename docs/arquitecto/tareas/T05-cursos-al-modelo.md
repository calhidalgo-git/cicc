# T05 — Cursos al modelo de datos

**Depende de:** T04. **Tamaño:** L. **Decisiones:** D4, D5, D6, D7.

## Objetivo

Que Fundamentos QA, QA Avanzado y Certificación de un Requerimiento de Software sean rutas de aprendizaje en la base de datos, con progreso, búsqueda y edición desde el administrador, y eliminar toda lógica que dependa del título de un recurso.

## Contexto

- Hoy son 23 plantillas: `templates/qa_weeks/week_1..6.html`, `templates/qa_advanced_weeks/week_1..11.html` y `templates/certification_topics/topic_1..6.html`, más tres portadas (`fundamentals.html`, `qa_advanced.html`, `certification.html`). Los títulos están en `QA_WEEKS`, `QA_ADVANCED_WEEKS` y `hub/certification.py`.
- La vista `resource()` abre esos cursos cuando el título del recurso es "Guía de pruebas batch y JCL", "Checklist de pruebas de API REST" o "Introducción a DB2 para QA" (y variantes), y el dashboard muestra esos recursos con otro título.
- `LearningPath` y `Lesson` ya existen; `Lesson.body` es texto plano.

## Pasos

1. **Modelo y migraciones.**
   - `LearningPath`: `slug` (`SlugField`, único), `intro_html` (`TextField`, opcional), `position` (entero, por defecto 0); orden por `position`, `id`.
   - `Lesson`: `body_html` (`TextField`, opcional); restricción única (`path`, `position`).
   - Migración de datos: asigna `slug` a las rutas existentes con `slugify(title)`, resolviendo duplicados con sufijo. Antes de crear la restricción única, verifica que no haya posiciones repetidas; si las hay, renuméralas dentro de cada ruta conservando el orden.
2. **Saneado.** En `hub/services/courses.py`, `sanitize_html(html)` con `nh3` y esta lista: etiquetas `h2 h3 h4 p ul ol li strong em b i a table thead tbody tr th td blockquote code pre br hr span div`; atributos `class` en todas, `href` y `title` en `a`; esquemas de enlace `http`, `https`, `mailto`. `Lesson.save()` y `LearningPath.save()` sanean su campo HTML; `Lesson.save()` además escribe en `body` el texto plano del HTML cuando `body_html` no está vacío.
   **Antes de fijar la lista**, inventaría las etiquetas y atributos que usan realmente las 23 plantillas y las tres portadas. Si aparece algo fuera de la lista (por ejemplo `img`, `svg`, `style`, `iframe`), no lo agregues por tu cuenta: anótalo en "Preguntas para el arquitecto" y deja la tarea `Bloqueada`.
3. **Contenido inicial.** Mueve el contenido a `hub/content/courses/<slug>/`: `course.json` (slug, título, área `Transversal`, descripción, posición, lista de lecciones con posición, título y archivo), `intro.html` y `NN.html`. Slugs: `fundamentos-qa`, `qa-avanzado`, `certificacion-requerimiento`. Los títulos de las lecciones son los actuales, completos. La introducción sale del texto de la portada correspondiente. No reescribas, resumas ni corrijas el contenido.
4. **Comando `load_courses`.** Idempotente: crea la ruta y las lecciones que falten, identificando por `slug` y `position`; no modifica lo existente salvo con `--force`. `seed_demo` lo invoca.
5. **Vistas y URLs nuevas** en `hub/views/learning.py`:
   - `/rutas/<slug>/`: introducción, lista de lecciones con marca de completada y porcentaje de avance del usuario.
   - `/rutas/<slug>/<int:position>/`: contenido (HTML saneado si existe; si no, `body` con saltos de línea), botón de completar, anterior y siguiente.
   - `complete` acepta un `next` validado con `url_has_allowed_host_and_scheme`; por defecto vuelve a la lección.
   - `/p/paths/` y `/p/lessons/` enlazan a estas páginas.
   Reutiliza las clases CSS de las plantillas actuales para conservar la apariencia.
6. **Redirecciones permanentes (301):** `/qa/fundamentos/` → `/rutas/fundamentos-qa/`; `/qa/fundamentos/semana/N/` → `/rutas/fundamentos-qa/N/`; lo mismo para `/qa/avanzado/...` → `qa-avanzado` y `/qa/certificacion/tema/N/` → `certificacion-requerimiento`. Un número fuera de rango sigue respondiendo 404.
7. **Eliminar la dependencia de títulos.** `resource()` siempre muestra el recurso solicitado. El dashboard muestra los recursos con su título real y un bloque "Cursos" con las rutas ordenadas por `position`. Elimina `QA_WEEKS`, `QA_ADVANCED_WEEKS`, `hub/certification.py`, las vistas antiguas y las plantillas trasladadas.
8. **Búsqueda.** La búsqueda global sigue usando `Lesson.body`, `Lesson.title` y `LearningPath`; los resultados de lecciones enlazan a `/rutas/<slug>/<position>/`.
9. **Administrador.** `Lesson` como línea dentro de `LearningPath`, con `slug` prellenado desde el título.
10. **Pruebas.** Adapta las pruebas de `/qa/...` de T04 para esperar 301 y destino correcto. Agrega:
    - El texto de cada lección cargada (sin etiquetas, espacios normalizados) coincide con el de su plantilla original; compara contra los archivos de `hub/content/courses/`.
    - Conteos 6, 11 y 6; `load_courses` dos veces no duplica; una edición manual sobrevive a una segunda carga y se sobrescribe con `--force`.
    - Guardar `<script>alert(1)</script><p onclick="x">hola</p>` deja solo `<p>hola</p>`.
    - Completar una lección de curso crea `Progress` y sube el porcentaje.
    - La búsqueda global encuentra una frase que solo existe en una lección de curso.
    - `/resource/<pk>/` de "Guía de pruebas batch y JCL" muestra ese recurso.
    - Un `next` externo en `complete` se ignora.

## Criterios de aceptación

- [ ] `grep -rn "Guía de pruebas batch\|Checklist de pruebas\|Introducción a DB2" hub templates` solo encuentra `seed_demo.py` y pruebas.
- [ ] `templates/qa_weeks`, `templates/qa_advanced_weeks`, `templates/certification_topics`, `fundamentals.html`, `qa_advanced.html`, `qa_week.html`, `qa_advanced_week.html`, `certification.html` y `certification_topic.html` ya no existen.
- [ ] Las migraciones se aplican sobre una copia de `demo.sqlite3` con datos, sin error y sin perder rutas, lecciones ni progreso.
- [ ] Todas las pruebas del paso 10 pasan en SQLite y PostgreSQL.
- [ ] Comparación visual manual de una lección de cada curso contra `main`: mismo contenido y formato equivalente.

## Fuera de alcance

Redactar o corregir contenido, evaluaciones asociadas a cursos, editor enriquecido en el administrador, cambios de permisos.
