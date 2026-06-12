from django import template

from correspondencia.utils.asunto_salida import asunto_respuesta_desde_entrada

register = template.Library()


@register.filter
def asunto_respuesta_prefill(asunto_entrada):
    """Valor por defecto del modal de respuesta (varchar 255)."""
    return asunto_respuesta_desde_entrada(asunto_entrada or '')
