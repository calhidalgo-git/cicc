"""Evaluaciones: inicio, examen, guardado, calificación y resultados."""

import json
from datetime import timedelta

from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from ..models import Assessment, Attempt
from .common import ctx, log


@login_required
@require_POST
def start(request, pk):
    a = get_object_or_404(Assessment, pk=pk)
    if not a.questions.exists():
        return HttpResponse('Evaluación sin preguntas', status=400)
    active = Attempt.objects.filter(user=request.user, assessment=a, finished=False).first()
    if not active:
        active = Attempt.objects.create(
            user=request.user, assessment=a, deadline=timezone.now() + timedelta(minutes=a.minutes)
        )
        log(request.user, f'Inicio evaluación {a.pk}')
    return redirect('exam', pk=active.pk)


@login_required
def exam(request, pk):
    a = get_object_or_404(Attempt, pk=pk, user=request.user)
    if a.finished:
        return redirect('results', pk=a.pk)
    return render(
        request,
        'exam.html',
        ctx(
            request,
            'assessments',
            attempt=a,
            exam_questions=a.assessment.questions.all(),
            deadline=a.deadline.isoformat(),
        ),
    )


def grade(a):
    questions = list(a.assessment.questions.all())
    a.score = (
        round(
            100 * sum(a.answers.get(str(q.pk)) == q.correct for q in questions) / len(questions), 1
        )
        if questions
        else 0
    )
    a.finished = True
    a.save()


@login_required
@require_POST
@transaction.atomic
def save(request, pk):
    a = get_object_or_404(Attempt.objects.select_for_update(), pk=pk, user=request.user)
    if a.finished:
        return JsonResponse({'error': 'Intento cerrado'}, status=409)
    if timezone.now() >= a.deadline:
        grade(a)
        return JsonResponse({'expired': True}, status=409)
    try:
        data = json.loads(request.body)
        qs = {str(q.pk): q for q in a.assessment.questions.all()}
        if not isinstance(data, dict) or any(
            k not in qs or type(v) is not int or not 0 <= v < len(qs[k].options)
            for k, v in data.items()
        ):
            raise ValueError
    except (ValueError, TypeError):
        return JsonResponse({'error': 'Respuestas inválidas'}, status=400)
    a.answers = data
    a.save()
    return JsonResponse({'saved': True, 'at': timezone.now().isoformat()})


@login_required
@require_POST
@transaction.atomic
def finish(request, pk):
    a = get_object_or_404(Attempt.objects.select_for_update(), pk=pk, user=request.user)
    if not a.finished:
        grade(a)
        log(request.user, f'Finaliza evaluación {a.pk}: {a.score}%')
    return redirect('results', pk=a.pk)


@login_required
def results(request, pk):
    a = get_object_or_404(Attempt, pk=pk, user=request.user, finished=True)
    rows = [
        (q, a.answers.get(str(q.pk)), q.options[q.correct]) for q in a.assessment.questions.all()
    ]
    return render(request, 'result.html', ctx(request, 'results', attempt=a, rows=rows))
