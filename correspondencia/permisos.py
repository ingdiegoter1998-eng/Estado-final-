"""Comprobaciones de permiso reutilizables en vistas y plantillas."""


def usuario_puede_gestion_operativa(user):
    """
    Admin/superuser y roles distintos de Ventanilla.
    Usuarios solo Ventanilla no ven panel de entrega/rebotes ni el calendario Django
    (/informes/calendario/). El calendario Next.js (/calendario) sí está en su sidebar.
    """
    if not user.is_authenticated:
        return False
    if getattr(user, 'is_superuser', False):
        return True
    if user.groups.filter(name='Admin').exists():
        return True
    if user.groups.filter(name='Ventanilla').exists():
        return False
    return True
