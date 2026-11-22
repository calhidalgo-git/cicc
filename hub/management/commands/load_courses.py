from django.core.management.base import BaseCommand

from hub.services.courses import load_courses


class Command(BaseCommand):
    help = (
        'Carga los cursos de hub/content/courses/ como rutas de aprendizaje. Crea las rutas y '
        'lecciones que falten (por slug y posición) sin tocar lo existente, salvo con --force.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Reescribe también las rutas y lecciones existentes con el contenido incluido.',
        )

    def handle(self, *args, **options):
        summary = load_courses(force=options['force'])
        self.stdout.write(
            self.style.SUCCESS(
                f'Rutas creadas: {summary["paths"]}; lecciones creadas: {summary["lessons"]}; '
                f'reescritas: {summary["updated"]}'
            )
        )
