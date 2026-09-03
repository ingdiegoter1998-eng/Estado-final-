"""Regresión: _configure_dashboard_ventanilla_form_querysets debe poder llamarse
más de una vez sobre el mismo form en la misma request sin reventar.

Bug real (2026-09-03): al radicar correspondencia física desde el modal
'radicar' del dashboard de Ventanilla, si el formulario fallaba validación
(o una excepción al guardar), la vista volvía a invocar esta función sobre
el mismo `radicacion_form` al final de `dashboard_ventanilla`. La segunda
invocación combinaba con `|` un queryset nuevo (sin `.distinct()`) con el
queryset que la primera invocación ya había dejado marcado `.distinct()`
en `usuario_destino_rapido`, y Django lo rechaza con:
'Cannot combine a unique query with a non-unique query.' -> Error 500,
la página redirigía al error del servidor en vez de mostrar el modal con
los errores de validación.
"""
from django.http import QueryDict
from django.contrib.auth.models import User

from correspondencia.views import (
    _configure_dashboard_ventanilla_form_querysets,
    _dashboard_radicacion_form,
)


def test_configurar_querysets_es_seguro_llamar_dos_veces(db):
    usuario = User.objects.create_user('destino_rapido', password='x', is_active=True)

    post = QueryDict(f'radicar-usuario_destino_rapido={usuario.pk}', mutable=True)
    form = _dashboard_radicacion_form(post, prefix='radicar')

    # 1ra invocación: como en la rama `form_prefix == 'radicar'` de dashboard_ventanilla.
    _configure_dashboard_ventanilla_form_querysets(form, post=post, user=usuario)

    # 2da invocación sobre el MISMO form: como el fallthrough incondicional al
    # final de la vista cuando la radicación falla validación o lanza una
    # excepción. Antes del fix, esto lanzaba TypeError.
    _configure_dashboard_ventanilla_form_querysets(form, post=post, user=usuario)

    # El usuario elegido debe seguir disponible en el queryset final.
    assert usuario in form.fields['usuario_destino_rapido'].queryset
