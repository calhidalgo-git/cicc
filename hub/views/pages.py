"""Secciones /p/<sección>/: un despachador y una función por sección.

Cada función devuelve (plantilla, contexto) y consulta solo lo que usa su plantilla.
"""

from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import Group, User
from django.http import Http404, HttpResponse
from django.shortcuts import render

from ..catalog import MODULES
from ..models import Assessment, Audit, LearningPath, Progress, Question, Resource
from ..permissions import TITLES, allowed
from . import exams, learning, library
from .common import ctx


def dashboard(request, section):
    return 'pages/dashboard.html', {
        'resources': Resource.objects.filter(published=True),
        'resource_count': Resource.objects.count(),
        'progress_count': Progress.objects.filter(user=request.user).count(),
        'assessment_count': Assessment.objects.count(),
        'paths': LearningPath.objects.all(),
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
    return 'pages/users.html', {'users': User.objects.all()}


def roles(request, section):
    return 'pages/roles.html', {'roles': Group.objects.prefetch_related('permissions')}


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
