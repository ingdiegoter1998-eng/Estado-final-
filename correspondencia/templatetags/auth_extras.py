from django import template
from django.contrib.auth.models import Group

from correspondencia.permisos import usuario_puede_gestion_operativa

register = template.Library()

@register.filter(name='has_group')
def has_group(user, group_name):
    """Verifica si un usuario pertenece a un grupo específico."""
    try:
        group = Group.objects.get(name=group_name)
    except Group.DoesNotExist:
        return False
    return group in user.groups.all()


@register.filter(name='puede_gestion_operativa')
def puede_gestion_operativa(user):
    return usuario_puede_gestion_operativa(user)


@register.filter(name='oneline')
def oneline(value):
    """Elimina saltos de línea y retornos de carro, reemplazándolos por un espacio."""
    if not value:
        return value
    import re
    # Reemplazar \r\n, \n, \r con un espacio y colapsar múltiples espacios en uno
    result = re.sub(r'[\r\n]+', ' ', str(value))
    result = re.sub(r'\s+', ' ', result)
    return result.strip() 