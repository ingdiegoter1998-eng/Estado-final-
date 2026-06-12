from django import template
from datetime import date

register = template.Library()

@register.filter(name='add_class')
def add_class(value, css_class):
        try:
            return value.as_widget(attrs={"class": css_class})
        except AttributeError:
            # Si el valor no tiene el método `as_widget`, lo devolvemos sin cambios
            return value

@register.filter(name='dias_restantes_vencimiento')
def dias_restantes_vencimiento(fecha_vencimiento):
    """Calcula los días restantes hasta el vencimiento y devuelve un dict con días y clase CSS"""
    if not fecha_vencimiento:
        return None
    
    hoy = date.today()
    if isinstance(fecha_vencimiento, date):
        fecha = fecha_vencimiento
    else:
        fecha = fecha_vencimiento.date() if hasattr(fecha_vencimiento, 'date') else fecha_vencimiento
    
    dias = (fecha - hoy).days
    
    if dias < 0:
        return {'dias': 0, 'texto': 'vencido', 'clase': 'prestamo-dias-vencido'}
    elif dias <= 5:
        return {'dias': dias, 'texto': f'vence en {dias} días', 'clase': 'prestamo-dias-rojo'}
    elif dias <= 10:
        return {'dias': dias, 'texto': f'vence en {dias} días', 'clase': 'prestamo-dias-naranja'}
    elif dias <= 20:
        return {'dias': dias, 'texto': f'vence en {dias} días', 'clase': 'prestamo-dias-amarillo'}
    else:
        return {'dias': dias, 'texto': f'vence en {dias} días', 'clase': 'prestamo-dias-verde'}
