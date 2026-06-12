"""Consultas livianas para el historial consolidado (entradas + salidas)."""
from datetime import timedelta

from django.db.models import F, Q
from django.db.models.functions import Coalesce
from django.urls import reverse
from django.utils import timezone

from correspondencia.models import (
    ESTADOS_CORRESPONDENCIA,
    ESTADOS_SALIDA,
    Correspondencia,
    CorrespondenciaSalida,
)

_ESTADO_ENTRADA_DISPLAY = dict(ESTADOS_CORRESPONDENCIA)
_ESTADO_SALIDA_DISPLAY = dict(ESTADOS_SALIDA)

_ENTRADA_VALUES = (
    'id',
    'event_date',
    'numero_radicado',
    'asunto',
    'estado',
    'requiere_respuesta',
    'fecha_limite_respuesta_persist',
    'origen_radicacion',
    'oficina_destino__nombre',
    'serie__nombre',
    'subserie__nombre',
    'remitente__nombres',
    'remitente__apellidos',
    'usuario_destino_inicial__first_name',
    'usuario_destino_inicial__last_name',
    'usuario_destino_inicial__username',
)

_SALIDA_VALUES = (
    'id',
    'event_date',
    'numero_radicado_salida',
    'asunto',
    'estado',
    'respuesta_a_id',
    'oficina_nombre',
    'serie_nombre',
    'subserie_nombre',
    'redactor_first_name',
    'redactor_last_name',
    'redactor_username',
    'dest_nombres',
    'dest_apellidos',
)


def _nombre_persona(first_name, last_name, username):
    full = f'{first_name or ""} {last_name or ""}'.strip()
    return full or (username or '-')


def _nombre_contacto(nombres, apellidos):
    full = f'{nombres or ""} {apellidos or ""}'.strip()
    return full or '-'


def _calcular_dias_restantes_entrada(row):
    if not row.get('requiere_respuesta') or row.get('estado') == 'RESPONDIDA':
        return None
    fecha_limite = row.get('fecha_limite_respuesta_persist')
    if not fecha_limite:
        return None
    if timezone.is_naive(fecha_limite):
        fecha_limite = timezone.make_aware(fecha_limite)
    return (fecha_limite - timezone.now()).days


def _aplicar_filtros_entrada(qs, filtros):
    oficina = filtros.get('oficina')
    if oficina:
        qs = qs.filter(oficina_destino__nombre__icontains=oficina)
    serie = filtros.get('serie')
    if serie:
        qs = qs.filter(serie__nombre__icontains=serie)
    subserie = filtros.get('subserie')
    if subserie:
        qs = qs.filter(subserie__nombre__icontains=subserie)
    fecha_inicio = filtros.get('fecha_inicio')
    if fecha_inicio:
        qs = qs.filter(event_date__gte=fecha_inicio)
    fecha_fin = filtros.get('fecha_fin')
    if fecha_fin:
        qs = qs.filter(event_date__lt=fecha_fin + timedelta(days=1))
    search_term = filtros.get('search_term')
    if search_term:
        qs = qs.filter(
            Q(asunto__icontains=search_term)
            | Q(numero_radicado__icontains=search_term)
            | Q(remitente__nombres__icontains=search_term)
            | Q(remitente__apellidos__icontains=search_term)
            | Q(remitente__entidad_externa__nombre__icontains=search_term)
        )
    estado = filtros.get('estado_entrada')
    if estado:
        qs = qs.filter(estado=estado)
    remitente = filtros.get('remitente')
    if remitente:
        qs = qs.filter(
            Q(remitente__nombres__icontains=remitente)
            | Q(remitente__apellidos__icontains=remitente)
        )
    destinatario = filtros.get('destinatario')
    if destinatario:
        qs = qs.filter(
            Q(usuario_destino_inicial__first_name__icontains=destinatario)
            | Q(usuario_destino_inicial__last_name__icontains=destinatario)
            | Q(usuario_destino_inicial__username__icontains=destinatario)
        )
    return qs


def _aplicar_filtros_salida(qs, filtros):
    oficina = filtros.get('oficina')
    if oficina:
        qs = qs.filter(respuesta_a__oficina_destino__nombre__icontains=oficina)
    serie = filtros.get('serie')
    if serie:
        qs = qs.filter(respuesta_a__serie__nombre__icontains=serie)
    subserie = filtros.get('subserie')
    if subserie:
        qs = qs.filter(respuesta_a__subserie__nombre__icontains=subserie)
    fecha_inicio = filtros.get('fecha_inicio')
    if fecha_inicio:
        qs = qs.filter(event_date__gte=fecha_inicio)
    fecha_fin = filtros.get('fecha_fin')
    if fecha_fin:
        qs = qs.filter(event_date__lt=fecha_fin + timedelta(days=1))
    search_term = filtros.get('search_term')
    if search_term:
        qs = qs.filter(
            Q(asunto__icontains=search_term)
            | Q(numero_radicado_salida__icontains=search_term)
            | Q(destinatario_contacto__nombres__icontains=search_term)
            | Q(destinatario_contacto__apellidos__icontains=search_term)
            | Q(destinatario_contacto__entidad_externa__nombre__icontains=search_term)
        )
    estado = filtros.get('estado_salida')
    if estado:
        qs = qs.filter(estado=estado)
    remitente = filtros.get('remitente')
    if remitente:
        qs = qs.filter(
            Q(usuario_redactor__first_name__icontains=remitente)
            | Q(usuario_redactor__last_name__icontains=remitente)
            | Q(usuario_redactor__username__icontains=remitente)
        )
    destinatario = filtros.get('destinatario')
    if destinatario:
        qs = qs.filter(
            Q(destinatario_contacto__nombres__icontains=destinatario)
            | Q(destinatario_contacto__apellidos__icontains=destinatario)
        )
    return qs


def _entrada_a_item(row):
    estado_key = row['estado']
    return {
        'id': row['id'],
        'tipo': 'Entrada',
        'fecha': row['event_date'],
        'radicado': row['numero_radicado'],
        'asunto': row['asunto'],
        'oficina': row.get('oficina_destino__nombre') or 'N/A',
        'serie': row.get('serie__nombre'),
        'subserie': row.get('subserie__nombre'),
        'estado_display': _ESTADO_ENTRADA_DISPLAY.get(estado_key, estado_key),
        'estado_key': estado_key,
        'dias_restantes': _calcular_dias_restantes_entrada(row),
        'requiere_respuesta': row.get('requiere_respuesta', False),
        'respuesta_a_id': None,
        'remitente_nombre': _nombre_contacto(
            row.get('remitente__nombres'),
            row.get('remitente__apellidos'),
        ),
        'destinatario_nombre': _nombre_persona(
            row.get('usuario_destino_inicial__first_name'),
            row.get('usuario_destino_inicial__last_name'),
            row.get('usuario_destino_inicial__username'),
        ),
        'origen_radicacion': 'RAPIDA' if row.get('origen_radicacion') == 'RAPIDA' else 'MANUAL',
    }


def _salida_a_item(row):
    estado_key = row['estado']
    return {
        'id': row['id'],
        'tipo': 'Salida',
        'fecha': row['event_date'],
        'radicado': row['numero_radicado_salida'],
        'asunto': row['asunto'],
        'oficina': row.get('oficina_nombre') or 'N/A',
        'serie': row.get('serie_nombre'),
        'subserie': row.get('subserie_nombre'),
        'estado_display': _ESTADO_SALIDA_DISPLAY.get(estado_key, estado_key),
        'estado_key': estado_key,
        'dias_restantes': None,
        'requiere_respuesta': False,
        'respuesta_a_id': row.get('respuesta_a_id'),
        'remitente_nombre': _nombre_persona(
            row.get('redactor_first_name'),
            row.get('redactor_last_name'),
            row.get('redactor_username'),
        ),
        'destinatario_nombre': _nombre_contacto(
            row.get('dest_nombres'),
            row.get('dest_apellidos'),
        ),
        'origen_radicacion': 'MANUAL',
    }


def hydrate_historial_urls(items):
    """Resuelve detail_url solo para la página visible (evita miles de reverse())."""
    for item in items:
        if item['tipo'] == 'Entrada':
            item['detail_url'] = reverse(
                'correspondencia:detalle_correspondencia',
                kwargs={'pk': item['id']},
            )
        elif item.get('respuesta_a_id'):
            item['detail_url'] = reverse(
                'correspondencia:detalle_correspondencia',
                kwargs={'pk': item['respuesta_a_id']},
            )
        else:
            item['detail_url'] = reverse(
                'correspondencia:detalle_respuesta_salida',
                kwargs={'respuesta_id': item['id']},
            )
    return items


def _filtrar_vencimiento(items, estado_vencimiento):
    if not estado_vencimiento:
        return items

    def coincide(item):
        dias = item.get('dias_restantes')
        estado = item.get('estado_key')
        requiere = item.get('requiere_respuesta', False)

        if estado_vencimiento == 'VENCIDO':
            return dias is not None and dias < 0
        if estado_vencimiento == 'HOY':
            return dias is not None and dias == 0
        if estado_vencimiento == 'PROXIMO':
            return dias is not None and 1 <= dias <= 2
        if estado_vencimiento == 'POR_VENCER':
            return dias is not None and 3 <= dias <= 5
        if estado_vencimiento == 'A_TIEMPO':
            return dias is not None and dias > 5
        if estado_vencimiento == 'RESPONDIDA':
            return estado == 'RESPONDIDA'
        if estado_vencimiento == 'NO_REQUIERE':
            return not requiere or item['tipo'] == 'Salida'
        return True

    return [item for item in items if coincide(item)]


def fetch_historial_combinado(filtros):
    """
    Devuelve lista de dicts ordenada por fecha (desc) sin cargar modelos completos.
    filtros: dict con keys oficina, serie, subserie, tipo, estado_entrada, estado_salida,
             fecha_inicio, fecha_fin, search_term, remitente, destinatario, estado_vencimiento.
    """
    tipo = filtros.get('tipo')
    historial = []

    if tipo != 'Salida':
        entradas_qs = Correspondencia.objects.annotate(
            event_date=F('fecha_radicacion'),
        )
        entradas_qs = _aplicar_filtros_entrada(entradas_qs, filtros)
        historial.extend(
            _entrada_a_item(row)
            for row in entradas_qs.values(*_ENTRADA_VALUES)
        )

    if tipo != 'Entrada':
        salidas_qs = CorrespondenciaSalida.objects.annotate(
            event_date=Coalesce('fecha_envio', 'fecha_aprobacion', 'fecha_creacion'),
            oficina_nombre=F('respuesta_a__oficina_destino__nombre'),
            serie_nombre=F('respuesta_a__serie__nombre'),
            subserie_nombre=F('respuesta_a__subserie__nombre'),
            redactor_first_name=F('usuario_redactor__first_name'),
            redactor_last_name=F('usuario_redactor__last_name'),
            redactor_username=F('usuario_redactor__username'),
            dest_nombres=F('destinatario_contacto__nombres'),
            dest_apellidos=F('destinatario_contacto__apellidos'),
        )
        salidas_qs = _aplicar_filtros_salida(salidas_qs, filtros)
        historial.extend(
            _salida_a_item(row)
            for row in salidas_qs.values(*_SALIDA_VALUES)
        )

    historial = _filtrar_vencimiento(historial, filtros.get('estado_vencimiento'))
    historial.sort(key=lambda item: item['fecha'], reverse=True)
    return historial
