"""T04, paso 6: el dashboard y el menú muestran datos reales en lugar de valores fijos."""

from django.contrib.auth.models import User
from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone

from ..models import Assessment, Attempt, Lesson, Question, Resource

PASSWORD = 'DemoQA!2026'


class RealValues(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command('seed_demo')

    def setUp(self):
        self.client.login(username='ana', password=PASSWORD)

    def dashboard(self):
        response = self.client.get('/p/dashboard/')
        self.assertEqual(response.status_code, 200)
        return response

    def test_menu_badge_counts_the_assessments(self):
        Assessment.objects.create(title='Otra evaluación', area='Mainframe')
        total = Assessment.objects.count()
        self.assertContains(self.dashboard(), f'Evaluaciones<b>{total:02d}</b>')

    def test_lessons_and_areas_are_counted(self):
        response = self.dashboard()
        self.assertContains(response, f'{Lesson.objects.count()} lecciones · A tu ritmo')
        self.assertNotContains(response, '12 lecciones · A tu ritmo')
        self.assertEqual(response.context['area_count'], 2)
        Resource.objects.filter(area='Distribuido').update(published=False)
        self.assertEqual(self.dashboard().context['area_count'], 1)

    def test_next_challenge_is_the_first_assessment_not_passed(self):
        first, second = Assessment.objects.order_by('pk')[:2]
        response = self.dashboard()
        self.assertEqual(response.context['recommended'], first)
        self.assertContains(response, f'◷ {first.minutes} minutos')
        self.assertContains(response, f'◇ {first.questions.count()} pregunta')
        now = timezone.now()
        Attempt.objects.create(
            user=User.objects.get(username='ana'),
            assessment=first,
            deadline=now,
            finished=True,
            score=first.pass_score,
        )
        self.assertEqual(self.dashboard().context['recommended'], second)

    def test_without_assessments_shows_an_empty_state(self):
        Question.objects.all().delete()
        Attempt.objects.all().delete()
        Assessment.objects.all().delete()
        response = self.dashboard()
        self.assertIsNone(response.context['recommended'])
        self.assertContains(response, 'Todavía no hay evaluaciones')

    def test_user_without_group_shows_no_role(self):
        User.objects.create_user('sinrol', password=PASSWORD)
        self.client.logout()
        self.client.login(username='sinrol', password=PASSWORD)
        response = self.dashboard()
        self.assertContains(response, '<small>Sin rol</small>')
        self.assertNotContains(response, '<small>Administrador</small>')

    def test_no_fixed_values_remain(self):
        html = self.dashboard().content.decode()
        self.assertNotIn('Fundamentos QA<br>Mainframe', html)
        self.assertNotIn('Demuestra tus conocimientos en procesos batch', html)
