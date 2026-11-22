"""Secciones /p/<sección>/: un despachador y una función por sección.

Cada función devuelve (plantilla, contexto) y consulta solo lo que usa su plantilla.
"""

from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import Group, User
from django.db.models import Count, F, Prefetch, Q
from django.http import Http404, HttpResponse
from django.shortcuts import render

from ..catalog import MODULES
from ..models import (
    Assessment,
    Attempt,
    Audit,
    LearningPath,
    Progress,
    Question,
    Resource,
)
from ..permissions import TITLES, allowed
from . import exams, learning, library
from .common import ctx


def dashboard(request, section):
    published = Resource.objects.filter(published=True)
    # Total de recursos (publicados o no, como antes) y áreas de especialización con recursos
    # publicados, sin Transversal, en una sola consulta.
    totals = Resource.objects.aggregate(
        total=Count('pk'),
        areas=Count('area', distinct=True, filter=Q(published=True) & ~Q(area='Transversal')),
    )
    paths = list(
        LearningPath.objects.annotate(lesson_count=Count('lessons')).order_by('position', 'id')
    )
    assessments = list(
        Assessment.objects.annotate(question_count=Count('questions')).order_by('pk')
    )
    passed = set(
        Attempt.objects.filter(
            user=request.user, finished=True, score__gte=F('assessment__pass_score')
        ).values_list('assessment_id', flat=True)
    )
    # El próximo desafío es la primera evaluación que la persona no ha aprobado (o la primera).
    recommended = next(
        (a for a in assessments if a.pk not in passed), assessments[0] if assessments else None
    )
    return 'pages/dashboard.html', {
        'resources': published.select_related('learning_path'),
        'resource_count': totals['total'],
        'progress_count': Progress.objects.filter(user=request.user).count(),
        'assessment_count': len(assessments),
        # Toda lección pertenece a una ruta: el total sale de las rutas ya cargadas.
        'lesson_count': sum(path.lesson_count for path in paths),
        # Áreas de especialización: las distintas de Transversal que tienen recursos publicados.
        'area_count': totals['areas'],
        'recommended': recommended,
        'paths': paths,
        # La insignia del menú usa el mismo número, sin otra consulta.
        'nav_assessment_count': len(assessments),
    }


def questions(request, section):
    return 'pages/questions.html', {'questions': Question.objects.select_related('assessment')}


def reports(request, section):
    return 'pages/reports.html', {
        'resource_count': Resource.objects.count(),
        'assessment_count': Assessment.objects.count(),
        'users': User.objects.all(),
        'chart_data': [
            Resource.objects.filter(area='Mainframe', published=True).count(),
            Resource.objects.filter(area='Distribuido', published=True).count(),
        ],
    }


def users(request, section):
    # Los grupos se precargan en el mismo orden que usaba groups.first (por pk).
    groups = Prefetch('groups', queryset=Group.objects.order_by('pk'))
    return 'pages/users.html', {'users': User.objects.prefetch_related(groups)}


def roles(request, section):
    return 'pages/roles.html', {
        'roles': Group.objects.prefetch_related('permissions__content_type')
    }


def audit(request, section):
    return 'pages/audit.html', {
        'audits': Audit.objects.select_related('user').order_by('-created')[:100]
    }


def static_section(request, section):
    """Secciones sin datos propios: mapa de componentes, configuración y respaldos."""
    return f'pages/{section}.html', {}


SECTIONS = {
    'dashboard': dashboard,
    'library': library.resource_list,
    'videos': library.resource_list,
    'links': library.resource_list,
    **dict.fromkeys(MODULES, library.resource_list),
    'search': library.resource_list,
    'components': static_section,
    'paths': learning.paths,
    'lessons': learning.lessons,
    'assessments': exams.assessments,
    'results': exams.attempt_history,
    'questions': questions,
    'reports': reports,
    'users': users,
    'roles': roles,
    'settings': static_section,
    'audit': audit,
    'backups': static_section,
}


@login_required
def page(request, section='dashboard'):
    if section not in TITLES:
        raise Http404
    if not allowed(request.user, section):
        return HttpResponse('Acceso restringido por tu rol', status=403)
    template, extra = SECTIONS[section](request, section)
    # base.html muestra en el buscador global la consulta de la URL, en cualquier sección.
    extra.setdefault('query', request.GET.get('q', ''))
    return render(request, template, ctx(request, section, **extra))
