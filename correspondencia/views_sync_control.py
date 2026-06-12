from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models import Max
from django.utils import timezone
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from celery import current_app

from .email_sync_control import dumps_payload, loads_payload
from .models import CorreoEntrante, EjecucionControlCorreos, EstadoSincronizacionCorreos
from .tasks import ejecutar_operacion_control_correos


STALE_PENDING_MINUTES = 20
STALE_RUNNING_MINUTES = 20


def _can_access_sync_control(user):
    return user.is_superuser or user.groups.filter(name='Ventanilla').exists()


def _redirect_sync_control(*, run_id=None):
    """Redirección fija al panel (sin usar Referer ni path arbitrario)."""
    url = reverse('correspondencia:control_sincronizacion_correos')
    if run_id is not None:
        return redirect(f'{url}?run={run_id}')
    return redirect(url)


def _serialize_run(run):
    data = {
        'obj': run,
        'parametros_data': loads_payload(run.parametros, {}),
        'resumen_data': loads_payload(run.resumen, {}),
    }
    return data


def _sanear_ejecuciones_atascadas():
    ahora = timezone.now()
    stale_pending_before = ahora - timezone.timedelta(minutes=STALE_PENDING_MINUTES)
    stale_running_before = ahora - timezone.timedelta(minutes=STALE_RUNNING_MINUTES)

    pendientes = EjecucionControlCorreos.objects.filter(
        estado='PENDING',
        creado_en__lt=stale_pending_before,
    )
    for ejecucion in pendientes:
        ejecucion.estado = 'FAIL'
        ejecucion.error = 'Marcada como fallida automáticamente por permanecer en PENDING demasiado tiempo.'
        ejecucion.finalizado_en = ahora
        ejecucion.save(update_fields=['estado', 'error', 'finalizado_en'])

    corriendo = EjecucionControlCorreos.objects.filter(
        estado='RUNNING',
        iniciado_en__lt=stale_running_before,
    )
    for ejecucion in corriendo:
        ejecucion.estado = 'FAIL'
        ejecucion.error = 'Marcada como fallida automáticamente por permanecer en RUNNING más allá del tiempo esperado.'
        ejecucion.finalizado_en = ahora
        ejecucion.save(update_fields=['estado', 'error', 'finalizado_en'])


def _cancelar_ejecucion(run):
    if run.task_id:
        try:
            current_app.control.revoke(run.task_id, terminate=True)
        except Exception:
            pass

    run.estado = 'FAIL'
    run.error = 'Cancelada manualmente desde el panel de control.'
    run.finalizado_en = timezone.now()
    run.save(update_fields=['estado', 'error', 'finalizado_en'])


@login_required
@user_passes_test(_can_access_sync_control, login_url='correspondencia:welcome')
def control_sincronizacion_correos(request):
    _sanear_ejecuciones_atascadas()

    initial_since = request.GET.get('since', '')
    initial_until = request.GET.get('until', '')
    operaciones_imap = {'VERIFY', 'RECOVER', 'IMAP_TEST', 'SYNC_NOW'}

    if request.method == 'POST':
        action = request.POST.get('action', '').strip()
        admin_action = request.POST.get('admin_action', '').strip()

        if admin_action in {'cancel_run', 'delete_run'}:
            run_id = request.POST.get('run_id')
            run = get_object_or_404(EjecucionControlCorreos.objects.select_related('ejecutado_por'), pk=run_id)

            if admin_action == 'cancel_run':
                if run.estado not in {'PENDING', 'RUNNING'}:
                    messages.warning(request, 'Solo se pueden cancelar ejecuciones pendientes o en curso.')
                else:
                    _cancelar_ejecucion(run)
                    messages.success(request, 'La ejecución fue cancelada desde el panel.')
                return _redirect_sync_control(run_id=run.pk)

            if admin_action == 'delete_run':
                run_pk = run.pk
                run.delete()
                messages.success(request, 'La ejecución fue eliminada del historial.')
                selected_run = request.GET.get('run')
                if selected_run and str(selected_run) == str(run_pk):
                    return _redirect_sync_control()
                return _redirect_sync_control()

        try:
            days = max(1, int(request.POST.get('days') or 1))
        except ValueError:
            days = 1
        since = (request.POST.get('since') or '').strip()
        until = (request.POST.get('until') or '').strip()

        allowed_actions = {
            'VERIFY': 'Verificación de cobertura encolada.',
            'RECOVER': 'Recuperación de faltantes encolada.',
            'DUPLICATES': 'Verificación de duplicados encolada.',
            'DIAGNOSE': 'Diagnóstico operativo encolado.',
            'IMAP_TEST': 'Prueba IMAP encolada.',
            'SYNC_NOW': 'Sincronización inmediata encolada.',
        }

        if action not in allowed_actions:
            messages.error(request, 'La acción solicitada no es válida.')
            return redirect('correspondencia:control_sincronizacion_correos')

        ejecucion_activa = EjecucionControlCorreos.objects.filter(
            tipo_operacion=action,
            estado__in=['PENDING', 'RUNNING'],
        ).order_by('-creado_en').first()
        if ejecucion_activa:
            messages.warning(
                request,
                f'Ya existe una ejecución activa para {action}. Revisa su estado antes de volver a encolarla.'
            )
            return _redirect_sync_control(run_id=ejecucion_activa.pk)

        if action in operaciones_imap:
            otra_operacion_imap = EjecucionControlCorreos.objects.filter(
                tipo_operacion__in=operaciones_imap,
                estado__in=['PENDING', 'RUNNING'],
            ).order_by('-creado_en').first()
            if otra_operacion_imap:
                messages.warning(
                    request,
                    'Ya hay una operación intensiva de correo en curso. Espera a que termine antes de lanzar otra.'
                )
                return _redirect_sync_control(run_id=otra_operacion_imap.pk)

        parametros = {'days': days}
        if since:
            parametros['since'] = since
        if until:
            parametros['until'] = until
        if action in {'DIAGNOSE', 'IMAP_TEST', 'SYNC_NOW'}:
            parametros = {}

        ejecucion = EjecucionControlCorreos.objects.create(
            tipo_operacion=action,
            ejecutado_por=request.user,
            parametros=dumps_payload(parametros),
        )

        try:
            async_result = ejecutar_operacion_control_correos.delay(ejecucion.pk)
            ejecucion.task_id = async_result.id
            ejecucion.save(update_fields=['task_id'])
            messages.success(request, allowed_actions[action])
        except Exception as exc:
            ejecucion.estado = 'FAIL'
            ejecucion.error = str(exc)
            ejecucion.save(update_fields=['estado', 'error'])
            messages.error(request, f'No fue posible encolar la operación: {exc}')

        return _redirect_sync_control(run_id=ejecucion.pk)

    sync_state = EstadoSincronizacionCorreos.objects.filter(fuente='GMAIL_IMAP').first()
    ultimo_fetch = CorreoEntrante.objects.aggregate(ultima=Max('fecha_lectura_imap'))['ultima']
    ultimo_correo_bd = CorreoEntrante.objects.order_by('-fecha_lectura_imap').first()
    recientes_qs = EjecucionControlCorreos.objects.select_related('ejecutado_por')[:15]
    recientes = [_serialize_run(run) for run in recientes_qs]

    selected_run = None
    selected_run_id = request.GET.get('run')
    if selected_run_id:
        try:
            selected_run = _serialize_run(
                get_object_or_404(EjecucionControlCorreos.objects.select_related('ejecutado_por'), pk=selected_run_id)
            )
        except Exception:
            selected_run = recientes[0] if recientes else None
    elif recientes:
        selected_run = recientes[0]

    context = {
        'titulo_pagina': 'Control de Sincronización de Correos',
        'sync_state': sync_state,
        'ultimo_fetch': ultimo_fetch,
        'ultimo_correo_bd': ultimo_correo_bd,
        'recientes': recientes,
        'selected_run': selected_run,
        'ejecuciones_activas': EjecucionControlCorreos.objects.filter(estado__in=['PENDING', 'RUNNING']).count(),
        'ultima_verificacion': EjecucionControlCorreos.objects.filter(tipo_operacion='VERIFY').first(),
        'ultimo_diagnostico': EjecucionControlCorreos.objects.filter(tipo_operacion='DIAGNOSE').first(),
        'initial_since': initial_since,
        'initial_until': initial_until,
    }
    return render(request, 'correspondencia/admin/control_sincronizacion_correos.html', context)