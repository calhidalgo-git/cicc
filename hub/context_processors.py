from django.conf import settings


def cicc(request):
    """Datos de configuración que necesitan todas las plantillas."""
    return {'cicc_demo': settings.CICC_DEMO}
