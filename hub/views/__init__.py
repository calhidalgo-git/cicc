"""Vistas de CICC agrupadas por área. Se reexportan aquí para hub.urls y para las pruebas."""

from ..permissions import NAV
from .exams import exam, finish, results, save, start
from .learning import (
    certification,
    certification_topic,
    complete,
    lesson_detail,
    path_detail,
    qa_advanced,
    qa_advanced_week,
    qa_fundamentals,
    qa_week,
)
from .library import download, resource
from .management import backup, excel_template, import_excel, report
from .pages import page

__all__ = [
    'NAV',
    'backup',
    'certification',
    'certification_topic',
    'complete',
    'download',
    'exam',
    'excel_template',
    'finish',
    'import_excel',
    'lesson_detail',
    'page',
    'path_detail',
    'qa_advanced',
    'qa_advanced_week',
    'qa_fundamentals',
    'qa_week',
    'report',
    'resource',
    'results',
    'save',
    'start',
]
