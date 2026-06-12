"""Redirecciones internas seguras (evita open redirect vía Referer)."""

from django.shortcuts import redirect
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme


def _is_safe_referer(request, referer: str) -> bool:
    if not referer:
        return False
    return url_has_allowed_host_and_scheme(
        url=referer,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    )


def safe_back_url(request, *, fallback: str = '/registros/correspondencia/') -> str:
    """URL segura para enlaces «volver» en plantillas (solo mismo host)."""
    referer = request.META.get('HTTP_REFERER', '')
    if _is_safe_referer(request, referer):
        return referer
    return fallback


def safe_redirect_back(
    request,
    *,
    fallback: str | None = None,
    fallback_name: str | None = None,
):
    """Redirige al Referer solo si es del mismo sitio; si no, usa fallback interno."""
    referer = request.META.get('HTTP_REFERER', '')
    if _is_safe_referer(request, referer):
        return redirect(referer)
    if fallback_name:
        return redirect(fallback_name)
    return redirect(fallback or '/')
