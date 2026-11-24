from django.core.management.base import BaseCommand

from hub.services.courses import load_courses, relink_legacy_resources


class Command(BaseCommand):
    help = (
        'Carga los cursos de hub/content/courses/ como rutas de aprendizaje. Crea las rutas y '
        'lecciones oficiales que falten, sin tocar lo existente. Con --force reescribe solo las '
        'lecciones con marca de lección oficial; una lección propia nunca se reescribe. '
        'Al crear un curso, o con --force, vincula los recursos que lo abrían antes de T05. '
        'Con --relink solo vincula esos recursos, si no abren ninguna ruta.'
    )

    def add_arguments(self, parser):
        mode = parser.add_mutually_exclusive_group()
        mode.add_argument(
            '--force',
            action='store_true',
            help=(
                'Reescribe también los cursos oficiales y sus lecciones con marca de lección '
                'oficial. Las lecciones propias no se tocan.'
            ),
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
        for course, position, title, occupant in summary['occupied']:
            if occupant is not None and occupant.official_key:
                who = f'otra lección oficial, «{occupant.title}», que se movió ahí'
                advice = 'Si quieres el orden original, vuelve a colocarla en el administrador'
            else:
                who = 'una lección propia' + (f', «{occupant.title}»' if occupant else '')
                advice = 'Si quieres la oficial, mueve o quita esa lección en el administrador'
            self.stdout.write(
                self.style.WARNING(
                    f'«{course}»: la posición {position}, de «{title}», la ocupa {who}. '
                    f'No se creó la lección oficial; el resto del curso sí se cargó. {advice} '
                    'y vuelve a ejecutar el comando.'
                )
            )
