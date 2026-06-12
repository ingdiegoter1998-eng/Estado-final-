"""Normalización de asuntos para correspondencia de salida (varchar 255 en SQL Server)."""

from __future__ import annotations

ASUNTO_SALIDA_MAX_LENGTH = 255


def primera_linea_asunto(texto: str) -> str:
    """Toma la primera línea del texto (evita mezclar cuerpo en asunto de respuesta)."""
    if not texto:
        return ''
    linea = str(texto).replace('\r\n', '\n').replace('\r', '\n').split('\n', 1)[0].strip()
    return linea


def normalizar_asunto_salida(asunto: str, max_length: int = ASUNTO_SALIDA_MAX_LENGTH) -> str:
    """Recorta al límite de CorrespondenciaSalida.asunto sin romper codificación."""
    linea = primera_linea_asunto(asunto)
    if len(linea) <= max_length:
        return linea
    return linea[:max_length]


def asunto_respuesta_desde_entrada(asunto_entrada: str, prefijo: str = 'RE: ') -> str:
    """Asunto sugerido para respuesta: primera línea + prefijo RE, máximo 255 caracteres."""
    base = primera_linea_asunto(asunto_entrada)
    if base.lower().startswith('re:'):
        combinado = base
    else:
        combinado = f'{prefijo}{base}'
    return normalizar_asunto_salida(combinado)
