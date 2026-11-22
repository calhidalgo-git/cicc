"""Rutas de aprendizaje, lecciones, progreso y redirecciones de los cursos anteriores."""

from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from ..models import LearningPath, Lesson, Progress
from .common import ctx

# Rutas /qa/... anteriores a T05 (D7): curso → slug de la ruta que lo sustituye.
LEGACY_COURSES = {
    'fundamentos': 'fundamentos-qa',
    'avanzado': 'qa-avanzado',
    'certificacion': 'certificacion-requerimiento',
}


def lesson_url(lesson):
    return f'/rutas/{lesson.path.slug}/{lesson.position}/'


def progress_of(user, path):
    lessons = list(path.lessons.all())
    done = set(
        Progress.objects.filter(user=user, lesson__path=path).values_list('lesson_id', flat=True)
    )
    return lessons, done


@login_required
def path_detail(request, slug):
    path = get_object_or_404(LearningPath, slug=slug)
    lessons, done = progress_of(request.user, path)
    completed = sum(lesson.pk in done for lesson in lessons)
    context = ctx(
        request,
        'paths',
        path=path,
        lessons=lessons,
        done=done,
        done_count=completed,
        pct=round(100 * completed / len(lessons)) if lessons else 0,
    )
    context['title'] = path.title
    return render(request, 'learning/path.html', context)


@login_required
def lesson_detail(request, slug, position):
    path = get_object_or_404(LearningPath, slug=slug)
    lessons, done = progress_of(request.user, path)
    index = next((i for i, lesson in enumerate(lessons) if lesson.position == position), None)
    if index is None:
        raise Http404
    lesson = lessons[index]
    context = ctx(
        request,
        'paths',
        path=path,
        lesson=lesson,
        lessons=lessons,
        number=index + 1,
        total=len(lessons),
        done=done,
        lesson_done=lesson.pk in done,
        prev_lesson=lessons[index - 1] if index > 0 else None,
        next_lesson=lessons[index + 1] if index + 1 < len(lessons) else None,
    )
    context['title'] = lesson.title
    return render(request, 'learning/lesson.html', context)


def legacy_cover(request, course):
    return redirect('path_detail', slug=LEGACY_COURSES[course], permanent=True)


def legacy_lesson(request, course, number):
    slug = LEGACY_COURSES[course]
    if not Lesson.objects.filter(path__slug=slug, position=number).exists():
        raise Http404
    return redirect('lesson_detail', slug=slug, position=number, permanent=True)


def qa_fundamentals(request):
    return legacy_cover(request, 'fundamentos')


def qa_advanced(request):
    return legacy_cover(request, 'avanzado')


def certification(request):
    return legacy_cover(request, 'certificacion')


def qa_week(request, week):
    return legacy_lesson(request, 'fundamentos', week)


def qa_advanced_week(request, week):
    return legacy_lesson(request, 'avanzado', week)


def certification_topic(request, topic):
    return legacy_lesson(request, 'certificacion', topic)


def paths(request, section):
    return 'pages/paths.html', {'paths': LearningPath.objects.prefetch_related('lessons')}


def lessons(request, section):
    return 'pages/lessons.html', {
        'lessons': Lesson.objects.select_related('path').order_by(
            'path__position', 'path_id', 'position'
        ),
        'done': list(
            Progress.objects.filter(user=request.user).values_list('lesson_id', flat=True)
        ),
    }


@login_required
@require_POST
def complete(request, pk):
    lesson = get_object_or_404(Lesson.objects.select_related('path'), pk=pk)
    Progress.objects.get_or_create(user=request.user, lesson=lesson)
    # Vuelve a la lección salvo que se indique otro destino del propio sitio.
    target = request.POST.get('next', '')
    if not url_has_allowed_host_and_scheme(
        target, allowed_hosts={request.get_host()}, require_https=request.is_secure()
    ):
        target = lesson_url(lesson)
    return redirect(target)
