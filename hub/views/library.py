"""Biblioteca, módulos, búsqueda, ficha de recurso y descargas."""

from django.contrib.auth.decorators import login_required
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, render

from ..certification import TITLE as CERTIFICATION_TITLE
from ..models import Resource, ResourceVersion
from .common import ctx, log
from .learning import advanced_page, certification, fundamentals_page


@login_required
def resource(request, pk):
    r = get_object_or_404(Resource, pk=pk, published=True)
    # Las comparaciones de títulos se quitan en T05 (cursos al modelo de datos).
    if r.title in (
        'Introducción a DB2 para QA',
        'Certificacion en la Sección',
        'Certificación en la Sección',
        CERTIFICATION_TITLE,
    ):
        return certification(request)
    if r.title in ('Guía de pruebas batch y JCL', 'Fundamentos QA'):
        return fundamentals_page(request)
    if r.title in (
        'Checklist de pruebas de API REST',
        'Checklist de pruebas API REST',
        'QA Avanzado y Especialización',
    ):
        return advanced_page(request)
    return render(request, 'resource.html', ctx(request, 'library', resource=r))


@login_required
def download(request, pk):
    v = get_object_or_404(ResourceVersion, pk=pk, resource__published=True)
    if not v.file:
        raise Http404
    log(request.user, f'Descarga recurso {v.resource_id} versión {v.number}')
    return FileResponse(v.file.open('rb'), as_attachment=True)
