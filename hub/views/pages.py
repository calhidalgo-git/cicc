"""Secciones /p/<sección>/: dashboard, biblioteca, aprendizaje, evaluaciones y gestión."""

from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import Group, User
from django.db.models import Q
from django.http import Http404, HttpResponse
from django.shortcuts import render

from ..catalog import MODULES
from ..models import (
    Assessment,
    Attempt,
    Audit,
    LearningPath,
    Lesson,
    Progress,
    Question,
    Resource,
)
from ..permissions import TITLES, allowed
from .common import ctx


@login_required
def page(request, section='dashboard'):
    if section not in TITLES:
        raise Http404
    if not allowed(request.user, section):
        return HttpResponse('Acceso restringido por tu rol', status=403)
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
    return render(
        request,
        'page.html',
        ctx(
            request,
            section,
            resources=resources,
            module_section=section in MODULES,
            search_lessons=Lesson.objects.filter(
                Q(title__icontains=query)
                | Q(body__icontains=query)
                | Q(path__title__icontains=query)
            )
            if query and section == 'search'
            else Lesson.objects.none(),
            search_paths=LearningPath.objects.filter(
                Q(title__icontains=query) | Q(description__icontains=query)
            )
            if query and section == 'search'
            else LearningPath.objects.none(),
            search_assessments=Assessment.objects.filter(
                Q(title__icontains=query) | Q(area__icontains=query)
            )
            if query and section == 'search'
            else Assessment.objects.none(),
            chart_data=[
                Resource.objects.filter(area='Mainframe', published=True).count(),
                Resource.objects.filter(area='Distribuido', published=True).count(),
            ],
            query=query,
            area=area,
            paths=LearningPath.objects.all(),
            lessons=Lesson.objects.select_related('path'),
            done=list(
                Progress.objects.filter(user=request.user).values_list('lesson_id', flat=True)
            ),
            assessments=Assessment.objects.all(),
            attempts=Attempt.objects.filter(user=request.user, finished=True).select_related(
                'assessment'
            ),
            questions=Question.objects.select_related('assessment'),
            users=User.objects.all(),
            roles=Group.objects.prefetch_related('permissions'),
            audits=Audit.objects.select_related('user').order_by('-created')[:100],
            resource_count=Resource.objects.count(),
            progress_count=Progress.objects.filter(user=request.user).count(),
            assessment_count=Assessment.objects.count(),
        ),
    )
