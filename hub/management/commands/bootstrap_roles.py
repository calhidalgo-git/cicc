from django.core.management.base import BaseCommand, CommandError

from hub.services.roles import ROLE_NAMES, bootstrap_roles, check_migrated


class Command(BaseCommand):
    help = (
        'Crea o actualiza los grupos Participante, Editor, Evaluador y Administrador con sus '
        'permisos. No crea usuarios ni toca otros grupos. Seguro en producción. Si la base no '
        'tiene todas las migraciones, se detiene y pide ejecutar migrate.'
    )

    def handle(self, *args, **options):
        try:
            check_migrated()
            created = bootstrap_roles()
        except LookupError as error:
            raise CommandError(str(error)) from error
        updated = [name for name in ROLE_NAMES if name not in created]
        self.stdout.write(
            self.style.SUCCESS(
                f'Roles creados: {", ".join(created) or "ninguno"}; '
                f'actualizados: {", ".join(updated) or "ninguno"}.'
            )
        )
