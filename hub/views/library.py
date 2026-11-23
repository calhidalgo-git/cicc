"""Biblioteca, módulos, búsqueda, ficha de recurso y descargas."""

from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, render

from ..catalog import MODULES
from ..models import Assessment, LearningPath, Lesson, Resource, ResourceVersion
from ..permissions import TITLES, allowed
from ..services.pages import search_theory
from .common import ctx, log
from .learning import render_path


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
            # Teoría de las secciones del menú que la persona puede abrir (T12).
            search_pages=search_theory(query, [s for s in TITLES if allowed(request.user, s)])
            if searching
            else [],
            search_assessments=Assessment.objects.filter(
                Q(title__icontains=query) | Q(area__icontains=query)
            )
            if searching
            else Assessment.objects.none(),
        )
    return 'pages/resources.html', context


@login_required
def resource(request, pk):
    r = get_object_or_404(Resource.objects.select_related('learning_path'), pk=pk, published=True)
    if r.learning_path_id:
        # Como antes de T05: el recurso muestra la portada de su curso en la misma dirección.
        return render_path(request, r.learning_path)
    return render(request, 'resource.html', ctx(request, 'library', resource=r))


@login_required
def download(request, pk):
    v = get_object_or_404(ResourceVersion, pk=pk, resource__published=True)
    if not v.file:
        raise Http404
    log(request.user, f'Descarga recurso {v.resource_id} versión {v.number}')
    return FileResponse(v.file.open('rb'), as_attachment=True)
