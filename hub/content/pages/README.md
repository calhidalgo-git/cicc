# Teoría de las páginas del menú

Cada archivo de esta carpeta es la teoría de una opción del menú. El nombre del archivo es la
clave (`slug`) de la sección: `dashboard.md`, `library.md`, `glossary.html`… La lista completa está
en `NAV` (`hub/permissions.py`). Usa un solo archivo por sección, `.md` o `.html`.

Para cargar los archivos en la base de datos:

```powershell
python manage.py load_pages          # no toca las páginas editadas en el administrador
python manage.py load_pages --force  # también las reemplaza con el archivo
```

Un archivo que no cambió desde la última carga no se vuelve a escribir. Los archivos que empiezan
con `_` (como `_ejemplo.md`) y este `README.md` no se cargan.

## Formato Markdown (`.md`)

```markdown
# Título visible de la teoría (opcional; si falta, se usa el nombre del menú)

Introducción: todo lo que va antes del primer encabezado `##`.

## Primer bloque

Párrafos, listas con `-` o `1.`, **negrita**, *cursiva*, `código`,
[enlaces](https://ejemplo.invalid) y subtítulos `###`.

## Segundo bloque

Cada `##` abre un bloque nuevo, en el mismo orden del archivo.
```

## Formato HTML (`.html`)

Igual, con `<h1>` para el título, el HTML anterior al primer `<h2>` como introducción y cada `<h2>`
como bloque. El HTML se limita a las etiquetas permitidas de los cursos (T05): se quitan scripts,
estilos, imágenes y atributos de eventos.

No escribas aquí datos reales de la organización que no deban estar en el repositorio.
