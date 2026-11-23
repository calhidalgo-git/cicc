"""Libros Excel: plantilla de preguntas, importación y reporte de intentos.

Traslado desde hub/views.py (T04): la lógica es la misma; las vistas solo traducen petición y
respuesta.
"""

from io import BytesIO

from django.db import transaction
from django.http import HttpResponse
from openpyxl import Workbook, load_workbook

from ..models import Assessment, Attempt, Question

HEADERS = (
    'evaluacion_id',
    'pregunta',
    'opcion_a',
    'opcion_b',
    'opcion_c',
    'correcta_0_2',
    'explicacion',
)


def workbook_response(wb, name):
    out = BytesIO()
    wb.save(out)
    response = HttpResponse(
        out.getvalue(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    )
    response['Content-Disposition'] = f'attachment; filename="{name}"'
    return response


def template_workbook():
    wb = Workbook()
    ws = wb.active
    ws.append(list(HEADERS))
    # La fila de ejemplo usa una evaluación que existe: los IDs no siempre empiezan en 1.
    first = Assessment.objects.order_by('pk').values_list('pk', flat=True).first()
    ws.append(
        [
            first or 1,
            '¿Qué valida un smoke test?',
            'Flujo crítico',
            'Color del logo',
            'Todos los casos',
            0,
            'Verifica viabilidad básica.',
        ]
    )
    return wb


def import_questions(upload):
    """Valida e importa todas las filas o ninguna. Devuelve cuántas preguntas se importaron.

    Lanza ValueError con un mensaje para la persona, u otra excepción si el archivo no es válido.
    """
    if upload.size > 2 * 1024 * 1024:
        raise ValueError('Máximo 2 MB')
    wb = load_workbook(upload, read_only=True, data_only=True)
    rows = list(wb.active.iter_rows(values_only=True))
    if len(rows) > 501:
        raise ValueError('Máximo 500 preguntas')
    if tuple(rows[0]) != HEADERS:
        raise ValueError('Encabezados incorrectos; usa la plantilla')
    with transaction.atomic():
        for n, row in enumerate(rows[1:], 2):
            if (
                len(row) != 7
                or not all(row[i] is not None for i in range(7))
                or type(row[5]) is not int
                or row[5] not in range(3)
            ):
                raise ValueError(f'Fila {n}: datos inválidos')
            assessment = Assessment.objects.get(pk=int(row[0]))
            Question.objects.create(
                assessment=assessment,
                text=str(row[1]),
                options=list(map(str, row[2:5])),
                correct=row[5],
                explanation=str(row[6]),
            )
    return len(rows) - 1


def report_workbook():
    wb = Workbook()
    ws = wb.active
    ws.append(['Usuario', 'Evaluación', 'Área', 'Puntaje', 'Estado'])
    for a in Attempt.objects.filter(finished=True).select_related('user', 'assessment'):
        ws.append(
            [
                a.user.username,
                a.assessment.title,
                a.assessment.area,
                a.score,
                'Aprobado' if a.score >= a.assessment.pass_score else 'Por reforzar',
            ]
        )
    return wb
