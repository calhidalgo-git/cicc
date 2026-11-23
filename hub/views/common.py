"""Utilidades compartidas por las vistas."""

from ..models import Audit
from ..permissions import TITLES, visible_nav


def log(user, action):
    Audit.objects.create(user=user, action=action)


def ctx(request, section, **extra):
    return dict(
        nav=visible_nav(request.user),
        section=section,
        title=TITLES.get(section, 'Recurso'),
        **extra,
    )
