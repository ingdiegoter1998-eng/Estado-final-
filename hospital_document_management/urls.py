"""
URL configuration for hospital_document_management project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.contrib import admin
from django.urls import path, include
from documentos import views
from correspondencia.views import PasswordResetHTMLView
from documentos.views_errors import error_403, error_404, error_500
from django.shortcuts import redirect
from django.contrib.auth.views import (
    LoginView, LogoutView,
    PasswordResetDoneView,
    PasswordResetConfirmView, PasswordResetCompleteView,
)
from django.conf import settings
from django.conf.urls.static import static
from django.views.static import serve as static_serve
from django.urls import re_path

urlpatterns = [
    # Admin
    # path('jet/', include('jet.urls', 'jet')),  # Rutas de Django Jet
    path('admin/', admin.site.urls),

    # Rutas específicas desde 'documentos' si es necesario
    path('registros/', views.lista_registros, name='lista_registros'),
    path('registros/nuevo/', views.crear_registro, name='crear_registro'),
    path('registros/<int:pk>/editar/', views.editar_registro, name='editar_registro'),
    path('registros/<int:pk>/eliminar/', views.eliminar_registro, name='eliminar_registro'),

    # FUIDs
    path('registros/fuids/', views.lista_fuids, name='fuid_list'),
    path('registros/fuids/create/', views.FUIDCreateView.as_view(), name='fuid_form'),
    path('registros/fuids/detalle/<int:pk>/', views.detalle_fuid, name='detalle_fuid'),

    # Página de bienvenida
    path('registros/', include('documentos.urls')),  # Incluye las rutas de documentos
    path('registros/welcome/', views.welcome_view, name='welcome'),
    path('detalle-ficha/<int:consecutivo>/', views.detalle_ficha_paciente, name='detalle_ficha'),
    path('editar-ficha/<int:consecutivo>/', views.EditarFichaPaciente.as_view(), name='editar_ficha'),
    
    # Redirige la raíz del proyecto (/) a la página de registros
    path('registros/login/', LoginView.as_view(template_name='registration/login.html'), name='login'),
    path('registros/logout/', LogoutView.as_view(next_page='login'), name='logout'),

    # Recuperación de contraseña por email
    path('registros/password-reset/', PasswordResetHTMLView.as_view(), name='password_reset'),
    path('registros/password-reset/enviado/', PasswordResetDoneView.as_view(
        template_name='registration/password_reset_done.html',
    ), name='password_reset_done'),
    path('registros/password-reset/<uidb64>/<token>/', PasswordResetConfirmView.as_view(
        template_name='registration/password_reset_confirm.html',
        success_url='/registros/password-reset/completado/',
    ), name='password_reset_confirm'),
    path('registros/password-reset/completado/', PasswordResetCompleteView.as_view(
        template_name='registration/password_reset_complete.html',
    ), name='password_reset_complete'),

    # Incluir URLs de la app documentos (manteniendo la estructura existente)
    path('registros/', include('documentos.urls')),
    
    # === INCLUIR URLS DE CORRESPONDENCIA ===
    path('registros/correspondencia/', include('correspondencia.urls', namespace='correspondencia')),
    # === FIN ===

    path('', lambda request: redirect('welcome'), name='root_redirect'),

    path('accounts/', include('allauth.account.urls')),
]

# Servir media/static en desarrollo (DEBUG o runserver local sin nginx).
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
elif getattr(settings, "RUNSERVER_LOCAL", False):
    # static() de Django no registra rutas con DEBUG=False; servir desde STATIC_ROOT.
    urlpatterns += [
        re_path(
            r"^static/(?P<path>.*)$",
            static_serve,
            {"document_root": settings.STATIC_ROOT},
        ),
        re_path(
            r"^media/(?P<path>.*)$",
            static_serve,
            {"document_root": settings.MEDIA_ROOT},
        ),
    ]

# Manejadores de errores personalizados
handler403 = error_403
handler404 = error_404
handler500 = error_500

