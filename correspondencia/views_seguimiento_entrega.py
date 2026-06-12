"""Panel de seguimiento de entregas y rebotes."""

from datetime import timedelta

from django.contrib.auth.decorators import login_required, user_passes_test

from correspondencia.permisos import usuario_puede_gestion_operativa
from django.db.models import Count, Q
from django.http import Http404
from django.shortcuts import get_object_or_404, render
from django.utils import timezone

from correspondencia.models import (
    CorrespondenciaSalida,
    OficinaProductora,
    PostmarkWebhookEvento,
    SalidaDestinatario,
)
from correspondencia.utils.evidencia_envio import (
    NIVEL_EVIDENCIA_COMPLETA,
    NIVEL_EVIDENCIA_ENVIADO,
    NIVEL_EVIDENCIA_FALLO,
    NIVEL_EVIDENCIA_PENDIENTE,
    NIVEL_EVIDENCIA_REBOTE,
    eventos_webhook_para_destinatario,
    fila_seguimiento_desde_destinatario,
    linea_tiempo_salida,
)


def _base_qs_destinatarios():
    return SalidaDestinatario.objects.select_related(
        'correspondencia_salida',
        'correspondencia_salida__oficina_emisora',
        'contacto',
        'contacto__entidad_externa',
    ).filter(
        correspondencia_salida__fecha_envio__isnull=False,
    ).exclude(estado='PENDIENTE')


def _aplicar_filtros(qs, request):
    oficina_id = request.GET.get('oficina')
    fecha_desde = request.GET.get('fecha_desde')
    fecha_hasta = request.GET.get('fecha_hasta')
    estado = request.GET.get('estado')
    q = (request.GET.get('q') or '').strip()

    if oficina_id and oficina_id.isdigit():
        qs = qs.filter(correspondencia_salida__oficina_emisora_id=int(oficina_id))
    if fecha_desde:
        qs = qs.filter(correspondencia_salida__fecha_envio__date__gte=fecha_desde)
    if fecha_hasta:
        qs = qs.filter(correspondencia_salida__fecha_envio__date__lte=fecha_hasta)
    if estado in {'ENVIADO', 'REBOTE', 'FALLO', 'PENDIENTE'}:
        qs = qs.filter(estado=estado)
    if q:
        qs = qs.filter(
            Q(correspondencia_salida__numero_radicado_salida__icontains=q)
            | Q(email_snapshot__icontains=q)
            | Q(nombre_snapshot__icontains=q)
            | Q(correspondencia_salida__asunto__icontains=q)
        )
    return qs


def _calcular_kpis(qs_filtrado, filas):
    total = len(filas)
    confirmadas = sum(1 for f in filas if f.nivel_evidencia == NIVEL_EVIDENCIA_COMPLETA)
    rebotes = sum(1 for f in filas if f.nivel_evidencia == NIVEL_EVIDENCIA_REBOTE)
    fallos = sum(1 for f in filas if f.nivel_evidencia in {NIVEL_EVIDENCIA_FALLO, NIVEL_EVIDENCIA_PENDIENTE})
    sin_confirmar = sum(1 for f in filas if f.nivel_evidencia == NIVEL_EVIDENCIA_ENVIADO)
    pct_confirmadas = round(100 * confirmadas / total, 1) if total else 0

    eventos_24h = PostmarkWebhookEvento.objects.filter(
        recibido_at__gte=timezone.now() - timedelta(hours=24),
    ).count()

    return {
        'total': total,
        'confirmadas': confirmadas,
        'rebotes': rebotes,
        'fallos': fallos,
        'sin_confirmar': sin_confirmar,
        'pct_confirmadas': pct_confirmadas,
        'eventos_24h': eventos_24h,
    }


@login_required
@user_passes_test(usuario_puede_gestion_operativa, login_url='correspondencia:dashboard_ventanilla')
def panel_seguimiento_entrega(request):
    """Tablero de rebotes, entregas confirmadas y trazabilidad Postmark."""
    qs = _aplicar_filtros(_base_qs_destinatarios(), request)
    nivel_filtro = request.GET.get('evidencia')

    destinatarios = list(qs.order_by('-correspondencia_salida__fecha_envio')[:500])
    filas = [fila_seguimiento_desde_destinatario(d) for d in destinatarios]

    if nivel_filtro:
        filas = [f for f in filas if f.nivel_evidencia == nivel_filtro]

    kpis = _calcular_kpis(qs, filas)

    rebotes_recientes = [f for f in filas if f.nivel_evidencia == NIVEL_EVIDENCIA_REBOTE][:15]

    context = {
        'titulo_pagina': 'Seguimiento de entrega y rebotes',
        'filas': filas,
        'kpis': kpis,
        'rebotes_recientes': rebotes_recientes,
        'oficinas': OficinaProductora.objects.all().order_by('nombre'),
        'niveles_evidencia': [
            (NIVEL_EVIDENCIA_COMPLETA, 'Entrega confirmada'),
            (NIVEL_EVIDENCIA_ENVIADO, 'Enviado sin confirmación'),
            (NIVEL_EVIDENCIA_REBOTE, 'Rebote'),
            (NIVEL_EVIDENCIA_FALLO, 'Fallo'),
        ],
    }
    return render(request, 'correspondencia/admin/panel_seguimiento_entrega.html', context)


@login_required
@user_passes_test(usuario_puede_gestion_operativa, login_url='correspondencia:dashboard_ventanilla')
def detalle_evidencia_envio(request, salida_id: int):
    """Detalle de trazabilidad por radicado de salida."""
    salida = get_object_or_404(
        CorrespondenciaSalida.objects.select_related(
            'oficina_emisora', 'usuario_aprobador', 'usuario_redactor'
        ),
        pk=salida_id,
    )
    destinatarios = list(
        salida.destinatarios.select_related('contacto', 'contacto__entidad_externa').order_by('id')
    )
    if not destinatarios:
        raise Http404('Sin destinatarios registrados.')

    filas = [fila_seguimiento_desde_destinatario(d) for d in destinatarios]
    timeline = linea_tiempo_salida(salida.id)
    webhooks = PostmarkWebhookEvento.objects.filter(
        postmark_message_id__in=[
            d.postmark_message_id for d in destinatarios if d.postmark_message_id
        ]
    ).order_by('-recibido_at')

    destinatario_focus = None
    dest_id = request.GET.get('destinatario')
    if dest_id and dest_id.isdigit():
        destinatario_focus = next(
            (d for d in destinatarios if d.id == int(dest_id)),
            None,
        )

    context = {
        'titulo_pagina': f'Evidencia {salida.numero_radicado_salida}',
        'salida': salida,
        'filas': filas,
        'destinatarios': destinatarios,
        'destinatario_focus': destinatario_focus,
        'webhooks_destino': (
            eventos_webhook_para_destinatario(destinatario_focus)
            if destinatario_focus else webhooks
        ),
        'timeline': timeline,
    }
    return render(request, 'correspondencia/admin/detalle_evidencia_envio.html', context)
