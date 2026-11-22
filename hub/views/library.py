"""Biblioteca, módulos, búsqueda, ficha de recurso y descargas."""

from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, render

from ..catalog import MODULES
from ..certification import TITLE as CERTIFICATION_TITLE
from ..models import Assessment, LearningPath, Lesson, Resource, ResourceVersion
from .common import ctx, log
from .learning import advanced_page, certification, fundamentals_page


def resource_list(request, section):
    """Biblioteca, videoteca, enlaces, módulos temáticos y búsqueda global."""
    resources = Resource.objects.filter(published=True)
    query = request.GET.get('q', '')
    area = request.GET.get('area', '')
    if query:
        resources = resources.filter(
            Q(title__icontains=query) | Q(description__icontains=query) | Q(area__icontains=query)
        )
    if area:
        resources = resources.filter(area=area)
    if section in MODULES:
        resources = resources.filter(kind=section)
    if section == 'videos':
        resources = resources.filter(kind='Video')
    if section == 'links':
        resources = resources.filter(kind='Enlace')
    # El número de versiones de cada tarjeta se cuenta en la misma consulta.
    resources = resources.annotate(version_count=Count('versions'))
    context = {
        'resources': resources,
        'module_section': section in MODULES,
        'query': query,
        'area': area,
        'show_search_results': section == 'search',
    }
    if section == 'library':
        context['subtitle'] = (
            'Explora, comparte y encuentra la respuesta para tu siguiente desafío.'
        )
    if section == 'search':
        searching = bool(query)
        context.update(
            search_lessons=Lesson.objects.filter(
                Q(title__icontains=query)
                | Q(body__icontains=query)
                | Q(path__title__icontains=query)
            ).select_related('path')
            if searching
            else Lesson.objects.none(),
            search_paths=LearningPath.objects.filter(
                Q(title__icontains=query) | Q(description__icontains=query)
            )
            if searching
            else LearningPath.objects.none(),
            search_assessments=Assessment.objects.filter(
                Q(title__icontains=query) | Q(area__icontains=query)
            )
            if searching
            else Assessment.objects.none(),
        )
    return 'pages/resources.html', context


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
