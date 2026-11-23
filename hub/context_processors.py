from django.conf import settings

from .models import Assessment


def cicc(request):
    """Datos de configuración que necesitan todas las plantillas."""
    return {
        'cicc_demo': settings.CICC_DEMO,
        # Se evalúa solo si la plantilla lo usa (la insignia del menú en base.html).
        'nav_assessment_count': Assessment.objects.count,
    }
