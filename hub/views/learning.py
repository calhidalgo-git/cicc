"""Cursos con plantillas propias, rutas de aprendizaje, lecciones y progreso."""

from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from ..certification import TITLE as CERTIFICATION_TITLE
from ..certification import TOPICS as CERTIFICATION_TOPICS
from ..models import LearningPath, Lesson, Progress
from .common import ctx

QA_WEEKS = [
    'Semana 1 – Introducción al QA',
    'Semana 2 – Pruebas Manuales',
    'Semana 3 – Herramientas de QA',
    'Semana 4 – Automatización inicial',
    'Semana 5 – QA en metodologías ágiles y tradicionales',
    'Semana 6 – Tendencias y futuro del QA',
]
QA_ADVANCED_WEEKS = [
    'Semana 1 – Estrategias de pruebas avanzadas',
    'Semana 2 – Automatización intermedia',
    'Semana 3 – QA en CI/CD y DevOps',
    'Semana 4 – Testing basado en datos e IA',
    'Semana 5 – QA en metodologías híbridas',
    'Semana 6 – QA en pruebas de seguridad',
    'Semana 7 – QA en pruebas de rendimiento',
    'Semana 8 – QA en pruebas móviles',
    'Semana 9 – QA en pruebas de APIs y microservicios',
    'Semana 10 – QA en pruebas de accesibilidad y usabilidad',
    'Semana 11 – Soft skills y rol estratégico del QA',
]


def short_titles(weeks):
    return [title.split(' – ', 1)[-1] for title in weeks]


@login_required
def certification(request):
    context = ctx(
        request, 'library', certification_title=CERTIFICATION_TITLE, topics=CERTIFICATION_TOPICS
    )
    context['title'] = CERTIFICATION_TITLE
    return render(request, 'certification.html', context)


@login_required
def certification_topic(request, topic):
    if not 1 <= topic <= len(CERTIFICATION_TOPICS):
        raise Http404
    context = ctx(
        request,
        'library',
        certification_title=CERTIFICATION_TITLE,
        topics=CERTIFICATION_TOPICS,
        topic_title=CERTIFICATION_TOPICS[topic - 1],
        topic_number=topic,
        topic_template=f'certification_topics/topic_{topic}.html',
    )
    context['title'] = CERTIFICATION_TOPICS[topic - 1]
    return render(request, 'certification_topic.html', context)


def fundamentals_page(request):
    return render(
        request,
        'fundamentals.html',
        ctx(request, 'library', weeks=short_titles(QA_WEEKS)),
    )


def advanced_page(request):
    return render(
        request,
        'qa_advanced.html',
        ctx(request, 'library', weeks=short_titles(QA_ADVANCED_WEEKS)),
    )


@login_required
def qa_fundamentals(request):
    return fundamentals_page(request)


@login_required
def qa_advanced(request):
    return advanced_page(request)


@login_required
def qa_week(request, week):
    if not 1 <= week <= len(QA_WEEKS):
        raise Http404
    return render(
        request,
        'qa_week.html',
        ctx(
            request,
            'library',
            week=week,
            week_title=QA_WEEKS[week - 1],
            weeks=short_titles(QA_WEEKS),
            week_template=f'qa_weeks/week_{week}.html',
        ),
    )


@login_required
def qa_advanced_week(request, week):
    if not 1 <= week <= len(QA_ADVANCED_WEEKS):
        raise Http404
    return render(
        request,
        'qa_advanced_week.html',
        ctx(
            request,
            'library',
            week=week,
            week_title=QA_ADVANCED_WEEKS[week - 1],
            weeks=short_titles(QA_ADVANCED_WEEKS),
            week_template=f'qa_advanced_weeks/week_{week}.html',
        ),
    )


def paths(request, section):
    return 'pages/paths.html', {'paths': LearningPath.objects.all()}


def lessons(request, section):
    return 'pages/lessons.html', {
        'lessons': Lesson.objects.select_related('path'),
        'done': list(
            Progress.objects.filter(user=request.user).values_list('lesson_id', flat=True)
        ),
    }


@login_required
@require_POST
def complete(request, pk):
    lesson = get_object_or_404(Lesson, pk=pk)
    Progress.objects.get_or_create(user=request.user, lesson=lesson)
    return redirect('/p/lessons/#lesson-' + str(pk))
