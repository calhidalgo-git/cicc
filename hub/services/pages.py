"""Teoría de cada opción del menú: lectura de hub/content/pages/, carga y consulta."""

import hashlib
import html
import re
from pathlib import Path

from django.db import transaction
from django.db.models import Q

PAGES_DIR = Path(__file__).resolve().parent.parent / 'content' / 'pages'
EXTENSIONS = ('.md', '.html')

_H1_HTML = re.compile(r'<h1[^>]*>(.*?)</h1>', re.IGNORECASE | re.DOTALL)
_H2_HTML = re.compile(r'<h2[^>]*>(.*?)</h2>', re.IGNORECASE | re.DOTALL)
_TAG = re.compile(r'<[^>]+>')
_ORDERED = re.compile(r'^\d+[.)]\s+')
_INLINE = [
    (re.compile(r'`([^`]+)`'), r'<code>\1</code>'),
    (re.compile(r'\*\*(.+?)\*\*'), r'<strong>\1</strong>'),
    (re.compile(r'(?<![\w*])\*(?!\s)(.+?)(?<!\s)\*(?![\w*])'), r'<em>\1</em>'),
    (re.compile(r'\[([^\]]+)\]\(((?:https?://|mailto:)[^)\s]+)\)'), r'<a href="\2">\1</a>'),
]


class PageFileError(ValueError):
    """Un archivo de hub/content/pages/ no se puede cargar."""


def menu_pages():
    """(slug, etiqueta) de cada opción del menú, en su orden."""
    from hub.permissions import NAV

    return [(slug, label) for slug, label, _ in NAV]


# --- Lectura de archivos -------------------------------------------------------------------


def _inline(text):
    text = html.escape(text, quote=False)
    for pattern, replacement in _INLINE:
        text = pattern.sub(replacement, text)
    return text


def markdown_to_html(text):
    """Markdown sencillo a HTML: párrafos, ###, listas con - o 1., negrita, cursiva, código y
    enlaces. El HTML escrito dentro del Markdown se muestra como texto."""
    out, paragraph, items, list_tag = [], [], [], None

    def flush_paragraph():
        if paragraph:
            out.append(f'<p>{_inline(" ".join(paragraph))}</p>')
            paragraph.clear()

    def flush_list():
        nonlocal list_tag
        if items:
            body = ''.join(f'<li>{_inline(item)}</li>' for item in items)
            out.append(f'<{list_tag}>{body}</{list_tag}>')
            items.clear()
        list_tag = None

    for raw in text.splitlines():
        line = raw.strip()
        bullet = line[2:] if line[:2] in ('- ', '* ') else None
        number = _ORDERED.match(line)
        if not line:
            flush_paragraph()
            flush_list()
        elif line.startswith('### ') or line.startswith('#### '):
            flush_paragraph()
            flush_list()
            level = 4 if line.startswith('#### ') else 3
            out.append(f'<h{level}>{_inline(line[level + 1 :].strip())}</h{level}>')
        elif bullet is not None or number:
            flush_paragraph()
            tag = 'ul' if bullet is not None else 'ol'
            if list_tag and list_tag != tag:
                flush_list()
            list_tag = tag
            items.append(bullet if bullet is not None else line[number.end() :])
        else:
            flush_list()
            paragraph.append(line)
    flush_paragraph()
    flush_list()
    return '\n'.join(out)


def _split_markdown(text):
    title, intro, blocks, current = '', [], [], None
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith('## '):
            current = {'title': stripped[3:].strip(), 'lines': []}
            blocks.append(current)
        elif stripped.startswith('# ') and not title and current is None and not any(intro):
            title = stripped[2:].strip()
        elif current is None:
            intro.append(line)
        else:
            current['lines'].append(line)
    return {
        'title': title,
        'intro_html': markdown_to_html('\n'.join(intro)),
        'blocks': [
            {'title': block['title'], 'body_html': markdown_to_html('\n'.join(block['lines']))}
            for block in blocks
        ],
    }


def _plain(fragment):
    return html.unescape(_TAG.sub('', fragment)).strip()


def _split_html(text):
    title = ''
    first = _H1_HTML.search(text)
    if first and not _H2_HTML.search(text[: first.start()]):
        title = _plain(first.group(1))
        text = text[: first.start()] + text[first.end() :]
    parts = _H2_HTML.split(text)
    # parts = [introducción, título 1, cuerpo 1, título 2, cuerpo 2, ...]
    return {
        'title': title,
        'intro_html': parts[0].strip(),
        'blocks': [
            {'title': _plain(parts[i]), 'body_html': parts[i + 1].strip()}
            for i in range(1, len(parts), 2)
        ],
    }


def parse_page_file(path):
    """Título, introducción y bloques de un archivo .md o .html."""
    # utf-8-sig: admite la firma que añaden algunos editores de Windows (séptima revisión de
    # Codex, 24-11-2026); sin ella, el «#» del título quedaba dentro de la introducción.
    text = Path(path).read_text(encoding='utf-8-sig')
    content = _split_markdown(text) if Path(path).suffix == '.md' else _split_html(text)
    for block in content['blocks']:
        if not block['title']:
            raise PageFileError(f'{Path(path).name}: hay un bloque sin título.')
    content['hash'] = hashlib.sha256(text.encode('utf-8')).hexdigest()
    return content


def page_files(directory=None):
    """{slug: archivo} de la carpeta. Se ignoran README.md y los archivos que empiezan con _."""
    directory = Path(directory or PAGES_DIR)
    files = {}
    for path in sorted(directory.iterdir()) if directory.is_dir() else []:
        if path.suffix not in EXTENSIONS or path.name.startswith('_') or path.stem == 'README':
            continue
        if path.stem in files:
            raise PageFileError(f'Hay dos archivos para la sección «{path.stem}»: usa solo uno.')
        files[path.stem] = path
    return files


# --- Carga ---------------------------------------------------------------------------------


def ensure_pages():
    """Crea una página vacía por cada opción del menú que todavía no la tenga."""
    from hub.models import SectionPage

    existing = set(SectionPage.objects.values_list('slug', flat=True))
    missing = [
        SectionPage(slug=slug, title=label) for slug, label in menu_pages() if slug not in existing
    ]
    for page in missing:
        page.save()
    return len(missing)


@transaction.atomic
def load_pages(force=False, directory=None):
    """Crea las páginas que falten y carga la teoría de los archivos.

    Una página editada en el administrador no se toca, salvo con ``force``. Un archivo sin
    cambios desde la última carga tampoco se vuelve a escribir.
    """
    from hub.models import SectionBlock, SectionPage

    summary = {'created': ensure_pages(), 'loaded': 0, 'kept': [], 'unknown': []}
    labels = dict(menu_pages())
    pages = {page.slug: page for page in SectionPage.objects.all()}
    for slug, path in page_files(directory).items():
        if slug not in labels:
            summary['unknown'].append(path.name)
            continue
        page = pages[slug]
        content = parse_page_file(path)
        if not force:
            if page.origin == 'admin':
                summary['kept'].append(slug)
                continue
            if page.origin == 'file' and page.source_hash == content['hash']:
                continue
        page.title = content['title'] or labels[slug]
        page.intro_html = content['intro_html']
        page.origin = 'file'
        page.source_hash = content['hash']
        page.updated_by = None
        page.save()
        page.blocks.all().delete()
        for position, block in enumerate(content['blocks'], 1):
            SectionBlock.objects.create(
                page=page, position=position, title=block['title'], body_html=block['body_html']
            )
        summary['loaded'] += 1
    return summary


# --- Consulta ------------------------------------------------------------------------------


def section_theory(slug):
    """Página y bloques de una sección en una sola consulta; ``None`` si no existe la fila."""
    from hub.models import SectionPage

    rows = list(
        SectionPage.objects.filter(slug=slug)
        .values(
            'pk',
            'title',
            'intro_html',
            'updated',
            'blocks__title',
            'blocks__body_html',
            'blocks__position',
            'blocks__id',
        )
        .order_by('blocks__position', 'blocks__id')
    )
    if not rows:
        return None
    first = rows[0]
    blocks = [
        {'title': row['blocks__title'], 'body_html': row['blocks__body_html']}
        for row in rows
        if row['blocks__id'] is not None
    ]
    return {
        'pk': first['pk'],
        'title': first['title'],
        'intro_html': first['intro_html'],
        'updated': first['updated'],
        'blocks': blocks,
        'empty': not first['intro_html'] and not blocks,
    }


def search_theory(query, slugs):
    """Páginas con teoría que contiene ``query``, solo entre las secciones ``slugs``."""
    from hub.models import SectionPage

    return (
        SectionPage.objects.filter(slug__in=slugs)
        .filter(
            Q(title__icontains=query)
            | Q(intro__icontains=query)
            | Q(blocks__title__icontains=query)
            | Q(blocks__body__icontains=query)
        )
        .exclude(intro='', blocks__isnull=True)
        .distinct()
        .order_by('id')
    )
