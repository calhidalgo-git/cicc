"""Adjuntos cifrados y datos protegidos del contenido importado."""

from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_POST

from ..models import PrivateAsset, Secret
from .common import log


@login_required
def private_asset(request, key):
    asset = get_object_or_404(PrivateAsset, key=key)
    response = HttpResponse(asset.read(), content_type=asset.content_type)
    response['Cache-Control'] = 'private, max-age=3600'
    response['Content-Disposition'] = 'inline'
    return response


@login_required
@require_POST
def reveal_secret(request, pk):
    if not request.user.has_perm('hub.view_secret'):
        return JsonResponse({'error': 'Tu rol no permite ver datos protegidos.'}, status=403)
    secret = get_object_or_404(Secret, pk=pk)
    log(request.user, f'Consulta dato protegido {secret.pk} ({secret.context})'[:200])
    response = JsonResponse({'value': secret.reveal()})
    response['Cache-Control'] = 'no-store'
    return response
