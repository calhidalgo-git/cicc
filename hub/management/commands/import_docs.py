from django.core.management.base import BaseCommand, CommandError

from hub.services.crypto import DataKeyError
from hub.services.docs_import import ImportErrorDocs, import_docs


class Command(BaseCommand):
    help = (
        'Importa documentación Markdown como rutas de aprendizaje según un manifiesto JSON. '
        'Las claves y las imágenes se guardan cifradas con CICC_DATA_KEY. Sin --update no toca '
        'las lecciones que ya existen. El manifiesto y los documentos van fuera del repositorio.'
    )

    def add_arguments(self, parser):
        parser.add_argument('manifest', help='Ruta del manifiesto JSON.')
        parser.add_argument(
            '--source', help='Carpeta de documentos (si no, «source» del manifiesto).'
        )
        parser.add_argument(
            '--update', action='store_true', help='Reescribe también rutas y lecciones existentes.'
        )

    def handle(self, *args, **options):
        try:
            summary = import_docs(options['manifest'], options['source'], options['update'])
        except (ImportErrorDocs, DataKeyError) as error:
            raise CommandError(str(error)) from error
        self.stdout.write(
            self.style.SUCCESS(
                f'Rutas creadas: {summary["paths"]}; actualizadas: {summary["paths_updated"]}. '
                f'Lecciones creadas: {summary["lessons"]}; actualizadas: '
                f'{summary["lessons_updated"]}; sin tocar: {summary["skipped"]}. '
                f'Datos protegidos nuevos: {summary["secrets"]}; imágenes cifradas nuevas: '
                f'{summary["assets"]}.'
            )
        )
        for missing in summary['missing_images']:
            self.stdout.write(self.style.WARNING(f'Imagen no encontrada: {missing}'))
