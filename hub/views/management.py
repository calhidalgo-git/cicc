"""Gestión: plantilla e importación de preguntas, reporte Excel y respaldo de contenido."""

import json

from django.contrib.auth.decorators import permission_required
from django.core import serializers
from django.db import transaction
from django.http import HttpResponse
from django.shortcuts import render
from django.views.decorators.http import require_POST

from ..models import (
    Assessment,
    Attempt,
    Audit,
    LearningPath,
    Lesson,
    Progress,
    Question,
    Resource,
    ResourceVersion,
)
from ..services.excel import (
    import_questions,
    report_workbook,
    template_workbook,
    workbook_response,
)
from .common import ctx, log


@permission_required('hub.add_question', raise_exception=True)
def excel_template(request):
    return workbook_response(template_workbook(), 'plantilla-preguntas.xlsx')


@permission_required('hub.add_question', raise_exception=True)
@require_POST
def import_excel(request):
    try:
        with transaction.atomic():
            count = import_questions(request.FILES['file'])
            log(request.user, f'Importación Excel: {count} preguntas')
        return render(
            request,
            'notice.html',
            ctx(request, 'questions', message=f'{count} preguntas importadas correctamente.'),
        )
    except Exception as e:
        return render(
            request,
            'notice.html',
            ctx(
                request,
                'questions',
                message='No se importó ninguna fila. Revisa formato, campos e ID de evaluación. '
                f'{str(e) if isinstance(e, ValueError) else "Archivo inválido"}',
            ),
            status=400,
        )


@permission_required('hub.view_audit', raise_exception=True)
def report(request):
    wb = report_workbook()
    log(request.user, 'Exportación reporte Excel')
    return workbook_response(wb, 'reporte-cicc.xlsx')


# Orden del respaldo: cada modelo va después de aquellos a los que apunta.
BACKUP_MODELS = [
    Resource,
    ResourceVersion,
    LearningPath,
    Lesson,
    Assessment,
    Question,
    Progress,
    Attempt,
    Audit,
]
# El avance, los intentos y la auditoría guardan a la persona por su nombre de usuario y no por su
# número interno, que puede ser otro en la instalación donde se restaura (tercera revisión de
# Codex, 23-11-2026). Si falta la cuenta, loaddata se detiene sin aplicar nada.
USER_MODELS = {Progress, Attempt, Audit}


def backup_json():
    """Respaldo de contenido en JSON, con el formato de ``dumpdata`` que lee ``loaddata``."""
    objects = []
    for model in BACKUP_MODELS:
        natural = model in USER_MODELS
        queryset = model.objects.all()
        if natural:
            queryset = queryset.select_related('user')
        objects.extend(
            json.loads(serializers.serialize('json', queryset, use_natural_foreign_keys=natural))
        )
    return json.dumps(objects, ensure_ascii=False)


@permission_required('hub.view_audit', raise_exception=True)
@require_POST
def backup(request):
    log(request.user, 'Exportación respaldo de contenido')
    response = HttpResponse(backup_json(), content_type='application/json')
    response['Content-Disposition'] = 'attachment; filename="cicc-content-backup.json"'
    return response
