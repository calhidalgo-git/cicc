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
    SectionBlock,
    SectionPage,
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


@permission_required('hub.view_reports', raise_exception=True)
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
    SectionPage,
    SectionBlock,
    Assessment,
    Question,
    Progress,
    Attempt,
    Audit,
]
# Las secciones se guardan por su slug y no por su número interno, que cambia si se revierte y se
# vuelve a aplicar la migración 0009 o en otra instalación (revisión de Codex, 22-11-2026). Sus
# bloques apuntan a la sección por el slug, y su autor por el nombre de usuario.
NATURAL_KEY_MODELS = {SectionPage, SectionBlock}
# El avance, los intentos y la auditoría guardan a la persona por su nombre de usuario y no por su
# número interno, que puede ser otro en la instalación donde se restaura (tercera revisión de
# Codex, 23-11-2026). Si falta la cuenta, loaddata se detiene sin aplicar nada.
USER_MODELS = {Progress, Attempt, Audit}
# Lo que se carga junto con cada fila para escribir esas claves sin una consulta por fila
# (tercera revisión de Codex, 23-11-2026).
RELATED = {
    SectionPage: ('updated_by',),
    SectionBlock: ('page',),
    Progress: ('user',),
    Attempt: ('user',),
    Audit: ('user',),
}


def backup_json():
    """Respaldo de contenido en JSON, con el formato de ``dumpdata`` que lee ``loaddata``.

    Cada modelo va por número interno. Tras revertir y volver a migrar, las rutas locales reciben
    las direcciones en ese orden; restaurarlas en el mismo orden libera cada dirección antes de
    que otra ruta la recupere (cuarta revisión de Codex, 24-11-2026).
    """
    objects = []
    for model in BACKUP_MODELS:
        queryset = model.objects.order_by('pk')
        if model in RELATED:
            queryset = queryset.select_related(*RELATED[model])
        objects.extend(
            json.loads(
                serializers.serialize(
                    'json',
                    queryset,
                    use_natural_foreign_keys=model in NATURAL_KEY_MODELS | USER_MODELS,
                    use_natural_primary_keys=model in NATURAL_KEY_MODELS,
                )
            )
        )
    return json.dumps(objects, ensure_ascii=False)


@permission_required('hub.export_backup', raise_exception=True)
@require_POST
def backup(request):
    log(request.user, 'Exportación respaldo de contenido')
    response = HttpResponse(backup_json(), content_type='application/json')
    response['Content-Disposition'] = 'attachment; filename="cicc-content-backup.json"'
    return response
