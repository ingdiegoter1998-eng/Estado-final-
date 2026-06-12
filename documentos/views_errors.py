from django.shortcuts import render
from django.http import HttpResponseForbidden, HttpResponseNotFound, HttpResponseServerError

def error_403(request, exception=None):
    """Página de error 403 - Acceso Denegado"""
    return render(request, '403.html', status=403)

def error_404(request, exception=None):
    """Página de error 404 - Página No Encontrada"""
    return render(request, '404.html', status=404)

def error_500(request):
    """Página de error 500 - Error del Servidor"""
    return render(request, '500.html', status=500)
