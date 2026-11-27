"""Muestra las marcas ⟦secreto:N⟧ del contenido como un botón para revelar el dato protegido."""

from django import template
from django.urls import reverse
from django.utils.safestring import mark_safe

from hub.services.docs_import import SECRET_TOKEN_RE

register = template.Library()


@register.filter
def protect_secrets(html, user):
    """``html`` ya está saneado al guardar. Sustituye cada marca por su control según el rol."""
    allowed = getattr(user, 'has_perm', None) and user.has_perm('hub.view_secret')

    def replace(match):
        if not allowed:
            return (
                '<span class="secret-chip locked" title="Tu rol no permite verlo">'
                '🔒 dato protegido</span>'
            )
        url = reverse('reveal_secret', args=[int(match.group(1))])
        return (
            f'<button type="button" class="secret-chip" data-secret-url="{url}">'
            '🔒 mostrar dato protegido</button>'
        )

    return mark_safe(SECRET_TOKEN_RE.sub(replace, html or ''))
