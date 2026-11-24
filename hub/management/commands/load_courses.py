from django.core.management.base import BaseCommand

from hub.services.courses import load_courses, relink_legacy_resources


class Command(BaseCommand):
    help = (
        'Carga los cursos de hub/content/courses/ como rutas de aprendizaje. Crea las rutas y '
        'lecciones que falten (por slug y posición) sin tocar lo existente, salvo con --force. '
        'Al crear un curso, o con --force, vincula los recursos que lo abrían antes de T05. '
        'Con --relink solo vincula esos recursos, si no abren ninguna ruta.'
    )

    def add_arguments(self, parser):
        mode = parser.add_mutually_exclusive_group()
        mode.add_argument(
            '--force',
            action='store_true',
            help='Reescribe también las rutas y lecciones existentes con el contenido incluido.',
        )
        mode.add_argument(
            '--relink',
            action='store_true',
            help=(
                'Solo vincula con su curso los recursos históricos que no abren ninguna ruta. '
                'No crea ni reescribe rutas ni lecciones, y respeta los recursos que ya abren '
                'otra ruta. Sirve para las instalaciones que aplicaron la T05 anterior.'
            ),
        )

    def handle(self, *args, **options):
        if options['relink']:
            summary = relink_legacy_resources()
        else:
            summary = load_courses(force=options['force'])
        self.stdout.write(
            self.style.SUCCESS(
                f'Rutas creadas: {summary["paths"]}; lecciones creadas: {summary["lessons"]}; '
                f'reescritas: {summary["updated"]}; recursos vinculados: {summary["linked"]}'
            )
        )
        for title in summary['ambiguous']:
            self.stdout.write(
                self.style.WARNING(
                    f'Hay más de un recurso titulado «{title}»: no se vinculó ninguno. '
                    'Elige en el administrador cuál abre su curso.'
                )
            )
        for title in summary['protected']:
            self.stdout.write(
                self.style.WARNING(
                    f'«{title}» tiene lecciones oficiales fuera de su posición y quizá lecciones '
                    'propias antes de ellas: no se reescribió ni se creó ninguna lección. '
                    'Ordénalas en el administrador y vuelve a ejecutar el comando.'
                )
            )
