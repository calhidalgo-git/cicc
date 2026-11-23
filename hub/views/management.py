"""Gestión: plantilla e importación de preguntas, reporte Excel y respaldo de contenido."""

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


@permission_required('hub.view_audit', raise_exception=True)
@require_POST
def backup(request):
    log(request.user, 'Exportación respaldo de contenido')
    objects = []
    for model in [
        Resource,
        ResourceVersion,
        LearningPath,
        Lesson,
        Assessment,
        Question,
        Progress,
        Attempt,
        Audit,
    ]:
        objects.extend(model.objects.all())
    response = HttpResponse(serializers.serialize('json', objects), content_type='application/json')
    response['Content-Disposition'] = 'attachment; filename="cicc-content-backup.json"'
    return response
