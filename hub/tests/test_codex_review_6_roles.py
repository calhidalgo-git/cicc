"""T06: sexta revisión de Codex (24-11-2026). El aviso al proteger una lección, en español."""

from .test_codex_review_5_roles import LessonsWithProgressAreProtected as Base


class ProtectedLessonMessage(Base):
    def test_the_message_names_the_person_and_the_lesson(self):
        response = self.client.post(
            f'/admin/hub/learningpath/{self.path.pk}/change/', self.form_data({self.first})
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'avance')
        self.assertContains(response, 'alumna completó «A»')
        self.assertNotContains(response, 'Progress object')
        self.assertNotContains(response, 'progress Progress')


del Base
