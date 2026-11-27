"""Importa documentación en Markdown como rutas de aprendizaje (cursos) para personas nuevas.

El contenido real de la organización NO vive en el repositorio: se lee de una carpeta local y de
un manifiesto JSON que también queda fuera del repositorio. Ver ``docs/IMPORTAR-DOCUMENTACION.md``.

Protección del contenido:
- Las contraseñas y claves que aparecen como ``Clave: valor`` o en columnas PASSWORD/CLAVE de una
  tabla se sacan del texto, se guardan cifradas en ``Secret`` y en la lección queda la marca
  ``⟦secreto:<pk>⟧``. Solo quien tiene ``hub.view_secret`` puede verlas, y cada consulta se audita.
- Las imágenes se guardan cifradas en ``PrivateAsset`` y solo se sirven a usuarios autenticados.
"""

import hashlib
import json
import mimetypes
import re
from pathlib import Path

import markdown
from django.core.files.base import ContentFile
from django.db import transaction

from .crypto import encrypt, fingerprint

SECRET_TOKEN = '⟦secreto:{}⟧'
SECRET_TOKEN_RE = re.compile(r'⟦secreto:(\d+)⟧')

_FRONTMATTER_RE = re.compile(r'\A---\s*\n.*?\n---\s*\n', re.S)
_SOURCE_LINE_RE = re.compile(r'^>\s*Fuente original:.*$', re.M)
_MD_IMAGE_RE = re.compile(r'!\[([^\]]*)\]\(<?([^)>\s]+)>?(?:\s+"[^"]*")?\)')
_HTML_IMAGE_RE = re.compile(r'<img\b[^>]*?\bsrc="([^"]+)"[^>]*?/?>', re.I)
_FENCE_RE = re.compile(r'^\s*(```|~~~)')
_PANDOC_ESCAPE_RE = re.compile(r'\\([$"\'|@&%<~^=\\])')
# «Clave: valor», «password = valor», «pass: valor o otro»; admite negritas de Markdown.
_SECRET_RE = re.compile(
    r'(?i)\b(password|contraseña|contrasena|passwd|pass|pwd|clave)'
    r'(\s*\**\s*[:=]\s*\**\s*)'
    r'([^\s*|<>`]+)'
    r'(?:(\s+o\s+)([^\s*|<>`]+))?'
)
# «Clave cert10$2024», «contraseña a11111»: sin dos puntos, el valor debe mezclar letras y números.
_SPACED_SECRET_RE = re.compile(
    r'(?i)\b(password|contraseña|contrasena|clave|pwd)(\s+)'
    r'(?!(?:de|del|la|el|es|y|o|para|con)\b)'
    r'(?=[^\s|<>`]*\d)(?=[^\s|<>`]*[a-z])([^\s|<>`⟦]{4,})'
)
# La palabra sola en su línea («> Contraseña»): el valor está en la siguiente línea con texto.
_LONE_KEYWORD_RE = re.compile(r'(?i)^[\s>*_-]*(password|contraseña|contrasena|clave|pwd)[\s:*_]*$')
_SECRET_HEADER_RE = re.compile(r'(?i)^\s*(password|contraseña|contrasena|clave|pass|pwd)\s*$')
# Palabras que siguen a «Clave:» sin ser una clave («Clave: Solicitar a …»).
_NOT_SECRETS = {
    'solicitar',
    'solicitarla',
    'ver',
    'usar',
    'tu',
    'su',
    'el',
    'la',
    'de',
    'del',
    'actual',
    'nueva',
    'dinámica',
    'dinamica',
    'pedir',
}


class ImportErrorDocs(Exception):
    pass


def natural_key(path):
    return [int(part) if part.isdigit() else part.lower() for part in re.split(r'(\d+)', path.name)]


class Importer:
    def __init__(self, source, protect=()):
        # Valores exactos que siempre se cifran (lista «protect» del manifiesto), los más largos
        # primero para que un valor no tape a otro que lo contiene.
        self.always = sorted({value for value in protect if value}, key=len, reverse=True)
        self.source = Path(source).resolve()
        if not self.source.is_dir():
            raise ImportErrorDocs(f'No existe la carpeta de documentos: {self.source}')
        self.summary = {
            'paths': 0,
            'paths_updated': 0,
            'lessons': 0,
            'lessons_updated': 0,
            'skipped': 0,
            'secrets': 0,
            'assets': 0,
            'missing_images': [],
        }

    # --- Adjuntos y secretos -------------------------------------------------------------

    def store_asset(self, path):
        from hub.models import PrivateAsset

        data = path.read_bytes()
        key = hashlib.sha256(data).hexdigest()
        if not PrivateAsset.objects.filter(key=key).exists():
            asset = PrivateAsset(
                key=key,
                content_type=mimetypes.guess_type(path.name)[0] or 'application/octet-stream',
                size=len(data),
            )
            asset.file.save(f'{key}.bin', ContentFile(encrypt(data)), save=False)
            asset.save()
            self.summary['assets'] += 1
        return key

    def protect(self, value, context):
        from hub.models import Secret

        secret, created = Secret.objects.get_or_create(
            fingerprint=fingerprint(value),
            defaults={'ciphertext': encrypt(value.encode('utf-8')), 'context': context[:200]},
        )
        if created:
            self.summary['secrets'] += 1
        return SECRET_TOKEN.format(secret.pk)

    # --- Conversión ----------------------------------------------------------------------

    def resolve_image(self, md_path, src, alt):
        target = (md_path.parent / src.replace('%20', ' ')).resolve()
        if self.source not in target.parents or not target.is_file():
            self.summary['missing_images'].append(f'{md_path.name}: {src}')
            return '<em>[imagen no disponible]</em>'
        key = self.store_asset(target)
        alt = alt.replace('"', '').strip() or 'Imagen del procedimiento'
        return f'<img src="/privado/{key}/" alt="{alt}" />'

    def mask_secrets(self, line, context):
        for value in self.always:
            if value in line:
                line = line.replace(value, self.protect(value, context))

        def spaced(match):
            return match.group(1) + match.group(2) + self.protect(match.group(3), context)

        def replace(match):
            value = match.group(3)
            if value.lower().strip('.,;:') in _NOT_SECRETS or len(value) < 3:
                return match.group(0)
            out = match.group(1) + match.group(2) + self.protect(value, context)
            if match.group(5):
                out += match.group(4) + self.protect(match.group(5), context)
            return out

        line = _SECRET_RE.sub(replace, line)
        return _SPACED_SECRET_RE.sub(spaced, line)

    def mask_lone_value(self, line, context):
        """Línea siguiente a «Contraseña» sola: si es un único valor, se cifra."""
        match = re.match(r'^([\s>*_]*)([^\s⟦]+?)([\s*_]*)$', line)
        if not match or len(match.group(2)) < 3:
            return line
        return match.group(1) + self.protect(match.group(2), context) + match.group(3)

    def mask_tabbed(self, line, columns, context):
        """Tabla separada por tabuladores (texto plano) con columna CONTRASEÑA o CLAVE."""
        if '\t' not in line:
            return line, None
        cells = line.split('\t')
        if columns is None:
            found = {i for i, cell in enumerate(cells) if _SECRET_HEADER_RE.match(cell)}
            if not found:
                return line, None
            # Sin celdas vacías el encabezado cuenta sus columnas como los datos.
            return line, {sum(1 for c in cells[:i] if c.strip()) for i in found}
        values = [i for i, cell in enumerate(cells) if cell.strip()]
        for column in columns:
            if column < len(values):
                index = values[column]
                cells[index] = self.protect(cells[index].strip(), context)
        return '\t'.join(cells), columns

    def prepare(self, md_path, text, context):
        """Markdown de pandoc listo para convertir: sin metadatos, imágenes cifradas, claves
        protegidas y escapes de pandoc resueltos fuera de los bloques de código."""
        text = _FRONTMATTER_RE.sub('', text)
        text = _SOURCE_LINE_RE.sub('', text)
        title = ''
        lines = text.splitlines()
        for index, line in enumerate(lines):
            if line.startswith('# '):
                title = line[2:].strip()
                del lines[index]
                break
            if line.strip():
                break
        out = []
        in_fence = False
        secret_columns = None
        tab_columns = None
        pending_value = False
        for line in lines:
            if pending_value and line.strip(' >\t'):
                pending_value = False
                if not _FENCE_RE.match(line):
                    out.append(self.mask_lone_value(line, context))
                    continue
            if _LONE_KEYWORD_RE.match(line):
                pending_value = True
                out.append(line)
                continue
            line, tab_columns = self.mask_tabbed(line, tab_columns, context)
            if _FENCE_RE.match(line):
                in_fence = not in_fence
                out.append(line)
                continue
            if not in_fence:
                line = _PANDOC_ESCAPE_RE.sub(r'\1', line)
                line = _MD_IMAGE_RE.sub(
                    lambda m: self.resolve_image(md_path, m.group(2), m.group(1)), line
                )
                line = _HTML_IMAGE_RE.sub(
                    lambda m: (
                        m.group(0)
                        if m.group(1).startswith('/privado/')
                        else self.resolve_image(md_path, m.group(1), '')
                    ),
                    line,
                )
                line, secret_columns = self.mask_table(line, secret_columns, context)
            out.append(self.mask_secrets(line, context))
        return title, '\n'.join(out)

    def mask_table(self, line, columns, context):
        """En una tabla con columna PASSWORD/CLAVE, cifra el contenido de esa columna."""
        stripped = line.strip()
        if not stripped.startswith('|'):
            return line, None
        cells = stripped.strip('|').split('|')
        if columns is None:
            found = {i for i, cell in enumerate(cells) if _SECRET_HEADER_RE.match(cell)}
            return line, found or None
        if all(set(cell.strip()) <= set('-: ') for cell in cells):
            return line, columns
        for i in columns:
            if i < len(cells) and cells[i].strip():
                cells[i] = ' ' + self.protect(cells[i].strip(), context) + ' '
        return '|' + '|'.join(cells) + '|', columns

    def convert(self, md_path, context):
        text = md_path.read_text(encoding='utf-8-sig')
        title, prepared = self.prepare(md_path, text, context)
        html = markdown.markdown(prepared, extensions=['tables', 'fenced_code', 'sane_lists'])
        # Las lecciones usan h2 a h4: el título de la lección ya es el h1 de la página.
        html = re.sub(r'<(/?)h1\b', r'<\1h2', html)
        html = re.sub(r'<(/?)h[56]\b', r'<\1h4', html)
        return pretty_title(title or md_path.stem), html

    # --- Cursos --------------------------------------------------------------------------

    def course_files(self, course, exclude):
        files = []
        for item in course['items']:
            target = (self.source / item).resolve()
            if self.source != target and self.source not in target.parents:
                raise ImportErrorDocs(f'{item}: queda fuera de la carpeta de documentos.')
            if target.is_dir():
                files.extend(sorted(target.glob('*.md'), key=natural_key))
            elif target.is_file():
                files.append(target)
            else:
                raise ImportErrorDocs(f'{item}: no existe en {self.source}')
        # Un archivo nombrado antes que su carpeta va primero y no se repite.
        unique = list(dict.fromkeys(files))
        return [f for f in unique if f.relative_to(self.source).as_posix() not in exclude]

    def import_course(self, course, exclude, update):
        from hub.models import LearningPath, Lesson

        fields = {
            'title': course['title'],
            'area': course.get('area', 'Transversal'),
            'description': course.get('description', ''),
            'position': course.get('position', 100),
            'intro_html': markdown.markdown(course.get('intro', '')),
        }
        path = LearningPath.objects.filter(slug=course['slug']).first()
        if path is None:
            path = LearningPath.objects.create(slug=course['slug'], **fields)
            self.summary['paths'] += 1
        elif update:
            for name, value in fields.items():
                setattr(path, name, value)
            path.save()
            self.summary['paths_updated'] += 1
        existing = {lesson.position: lesson for lesson in path.lessons.all()}
        for position, md_path in enumerate(self.course_files(course, exclude), 1):
            lesson = existing.get(position)
            if lesson is not None and not update:
                self.summary['skipped'] += 1
                continue
            title, html = self.convert(md_path, f'{course["title"]} · {md_path.stem}')
            if lesson is None:
                Lesson.objects.create(
                    path=path, position=position, title=title[:200], body_html=html
                )
                self.summary['lessons'] += 1
            else:
                lesson.title = title[:200]
                lesson.body_html = html
                lesson.save()
                self.summary['lessons_updated'] += 1


def pretty_title(value):
    value = value.replace('_', ' ').strip()
    return re.sub(r'\s+', ' ', value)


def read_manifest(path):
    path = Path(path)
    try:
        data = json.loads(path.read_text(encoding='utf-8-sig'))
    except (OSError, json.JSONDecodeError) as error:
        raise ImportErrorDocs(f'No se pudo leer el manifiesto {path}: {error}') from error
    slugs = [course.get('slug') for course in data.get('courses', [])]
    if not slugs or any(not slug for slug in slugs) or len(set(slugs)) != len(slugs):
        raise ImportErrorDocs('El manifiesto necesita cursos con «slug» único.')
    return data


@transaction.atomic
def import_docs(manifest_path, source=None, update=False):
    """Crea las rutas y lecciones que falten; con ``update`` reescribe también las existentes."""
    from hub.services.courses import official_slugs

    manifest = read_manifest(manifest_path)
    source = source or manifest.get('source')
    if not source:
        raise ImportErrorDocs('Indica la carpeta de documentos con --source o «source».')
    reserved = official_slugs() & {course['slug'] for course in manifest['courses']}
    if reserved:
        raise ImportErrorDocs(f'Slugs reservados para cursos oficiales: {", ".join(reserved)}')
    importer = Importer(source, manifest.get('protect', []))
    exclude = set(manifest.get('exclude', []))
    for course in manifest['courses']:
        importer.import_course(course, exclude, update)
    return importer.summary
