"""
Vistas para el módulo de Correspondencia Urgente.

Este módulo contiene todas las vistas necesarias para gestionar
correspondencia que requiere respuesta INMEDIATA medida en horas laborales.

Características:
- Radicación desde correo entrante (solo Ventanilla)
- Buzón de urgencias por oficina
- Tomar y responder urgencias
- Notificaciones automáticas
- API endpoints para AJAX
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.contrib import messages
from django.utils import timezone
from django.db.models import Q, Count
from django.db import transaction

from .models import (
    CorrespondenciaUrgencia,
    CorreoEntrante,
    Notificacion,
    AdjuntoUrgencia,
    Contacto,
    GrupoAgenda,
    CorrespondenciaSalida,
    SalidaDestinatario,
    AdjuntoSalida,
    HistorialSalida,
)
from django.contrib.auth.models import User
from .forms import UrgenciaRadicacionForm, UrgenciaRespuestaForm
from .utils.asunto_salida import normalizar_asunto_salida
from documentos.models import OficinaProductora


def es_ventanilla(user):
    """Check si usuario pertenece a grupo Ventanilla"""
    return user.groups.filter(name='Ventanilla').exists()


@login_required
@user_passes_test(es_ventanilla)
def radicar_urgencia_view(request, correo_id):
    """
    Vista para radicar urgencia desde detalle de correo.
    Solo accesible por grupo Ventanilla.
    """
    correo = get_object_or_404(CorreoEntrante, pk=correo_id)
    
    # Verificar que el correo no esté ya radicado
    if correo.radicado_asociado or correo.urgencia_asociada:
        messages.error(request, 'Este correo ya fue radicado anteriormente.')
        return redirect('correspondencia:detalle_correo_entrante', correo_id=correo.id)
    
    if request.method == 'POST':
        form = UrgenciaRadicacionForm(request.POST)
        if form.is_valid():
            with transaction.atomic():
                # Crear urgencia
                urgencia = form.save(commit=False)
                urgencia.correo_entrante = correo
                urgencia.usuario_radica = request.user
                urgencia.save()
                
                # CRÍTICO: Vincular la urgencia al correo para que no se pueda radicar de nuevo
                correo.urgencia_asociada = urgencia
                correo.procesado = True
                correo.save(update_fields=['urgencia_asociada', 'procesado'])
                
                # Crear notificaciones para toda la oficina
                _crear_notificaciones_urgencia(urgencia)
            
            messages.success(
                request,
                f'Urgencia radicada exitosamente: {urgencia.radicado}',
                extra_tags='urgencia'
            )
            return redirect('correspondencia:urgencia_detalle', pk=urgencia.pk)
    else:
        form = UrgenciaRadicacionForm()
    
    context = {
        'form': form,
        'correo': correo,
    }
    return render(request, 'correspondencia/urgencia/radicar_urgencia.html', context)


@login_required
def buzon_urgencias(request):
    """
    Buzón de urgencias del usuario.
    Muestra urgencias de las oficinas a las que pertenece.
    """
    usuario = request.user
    
    # Obtener oficina del usuario a través de PerfilUsuario
    try:
        oficina_usuario_id = usuario.perfil.oficina_id
    except AttributeError:
        oficina_usuario_id = None
    
    if not oficina_usuario_id:
        messages.warning(request, 'No tiene una oficina asignada')
        return redirect('correspondencia:dashboard_usuario')
    
    urgencias_activas = CorrespondenciaUrgencia.objects.filter(
        oficina_destino_id=oficina_usuario_id,
        estado__in=['PENDIENTE', 'EN_PROCESO', 'VENCIDA']
    ).select_related(
        'correo_entrante',
        'serie',
        'subserie',
        'oficina_destino',
        'usuario_radica',
        'usuario_asignado'
    ).order_by('-prioridad', 'fecha_limite')
    
    # Actualizar estados vencidos
    for urgencia in urgencias_activas:
        urgencia.actualizar_horas_transcurridas()
        urgencia.marcar_vencida()

    urgencias_pendientes = CorrespondenciaUrgencia.objects.filter(
        oficina_destino_id=oficina_usuario_id,
        estado='PENDIENTE'
    ).select_related(
        'correo_entrante', 'serie', 'subserie', 'oficina_destino', 'usuario_radica', 'usuario_asignado'
    ).order_by('-prioridad', 'fecha_limite')

    urgencias_proceso = CorrespondenciaUrgencia.objects.filter(
        oficina_destino_id=oficina_usuario_id,
        estado='EN_PROCESO'
    ).select_related(
        'correo_entrante', 'serie', 'subserie', 'oficina_destino', 'usuario_radica', 'usuario_asignado'
    ).order_by('-prioridad', 'fecha_limite')

    urgencias_vencidas = CorrespondenciaUrgencia.objects.filter(
        oficina_destino_id=oficina_usuario_id,
        estado='VENCIDA'
    ).select_related(
        'correo_entrante', 'serie', 'subserie', 'oficina_destino', 'usuario_radica', 'usuario_asignado'
    ).order_by('-fecha_limite')
    
    # Urgencias respondidas recientes
    urgencias_respondidas = CorrespondenciaUrgencia.objects.filter(
        oficina_destino_id=oficina_usuario_id,
        estado='RESPONDIDA'
    ).select_related(
        'correo_entrante',
        'usuario_responde'
    ).order_by('-fecha_respuesta')[:20]
    
    # Notificaciones de urgencias no leídas
    notificaciones_urgencias = Notificacion.objects.filter(
        usuario=usuario,
        tipo='urgencia',
        leida=False
    ).order_by('-fecha_creacion')[:10]
    
    # Métricas
    total_pendientes = urgencias_pendientes.count()
    total_proceso = urgencias_proceso.count()
    total_respondidas = urgencias_respondidas.count()
    total_criticas = urgencias_activas.filter(prioridad='CRITICA').count()
    total_vencidas = urgencias_vencidas.count()
    
    context = {
        'urgencias_pendientes': urgencias_pendientes,
        'urgencias_proceso': urgencias_proceso,
        'urgencias_respondidas': urgencias_respondidas,
        'urgencias_vencidas': urgencias_vencidas,
        'notificaciones_urgencias': notificaciones_urgencias,
        'total_pendientes': total_pendientes,
        'total_proceso': total_proceso,
        'total_respondidas': total_respondidas,
        'total_criticas': total_criticas,
        'total_vencidas': total_vencidas,
        'now': timezone.now(),
    }
    
    return render(request, 'correspondencia/urgencias/buzon_urgencias.html', context)


@login_required
def urgencia_detalle(request, pk):
    """Detalle de una urgencia específica"""
    urgencia = get_object_or_404(
        CorrespondenciaUrgencia.objects.select_related(
            'correo_entrante',
            'serie',
            'subserie',
            'oficina_destino',
            'usuario_radica',
            'usuario_asignado',
            'usuario_responde'
        ),
        pk=pk
    )
    
    # Verificar permisos
    try:
        oficina_usuario_id = request.user.perfil.oficina_id
    except AttributeError:
        oficina_usuario_id = None
    
    puede_ver = (
        request.user == urgencia.usuario_radica or
        urgencia.oficina_destino.id == oficina_usuario_id
    )
    
    if not puede_ver:
        messages.error(request, 'No tiene permisos para ver esta urgencia')
        return redirect('correspondencia:dashboard_usuario')
    
    # Actualizar métricas
    urgencia.actualizar_horas_transcurridas()
    urgencia.marcar_vencida()
    
    # Marcar notificaciones como leídas
    Notificacion.objects.filter(
        usuario=request.user,
        tipo='urgencia',
        leida=False
    ).update(leida=True, fecha_lectura=timezone.now())
    
    # Adjuntos del correo original
    adjuntos_correo = urgencia.correo_entrante.adjuntos.all() if hasattr(urgencia.correo_entrante, 'adjuntos') else []
    
    # Adjuntos de respuesta
    adjuntos_respuesta = urgencia.adjuntos_respuesta.all()
    
    # Obtener oficina del usuario para búsquedas
    oficina_usuario = getattr(request.user.perfil, 'oficina', None) if hasattr(request.user, 'perfil') else None
    
    context = {
        'urgencia': urgencia,
        'adjuntos_correo': adjuntos_correo,
        'adjuntos_respuesta': adjuntos_respuesta,
        'puede_responder': urgencia.estado in ['PENDIENTE', 'EN_PROCESO'],
        'puede_tomar': urgencia.estado == 'PENDIENTE',
        'correspondencia': urgencia,  # Alias para compatibilidad con modal de correspondencia
        'modal_id': 'modalResponderUrgencia',
        'oficina_usuario': oficina_usuario,
    }
    
    return render(request, 'correspondencia/urgencias/detalle_urgencia.html', context)


@login_required
@require_http_methods(["POST"])
def tomar_urgencia(request, pk):
    """Un usuario toma una urgencia para trabajarla"""
    urgencia = get_object_or_404(CorrespondenciaUrgencia, pk=pk)
    is_ajax = request.headers.get('x-requested-with') == 'XMLHttpRequest'
    
    # Verificar permisos
    try:
        puede_tomar = request.user.perfil.oficina == urgencia.oficina_destino
    except AttributeError:
        puede_tomar = False
    
    if not puede_tomar:
        if is_ajax:
            return JsonResponse({
                'success': False,
                'error': 'No pertenece a la oficina destino'
            }, status=403)
        messages.error(request, 'No pertenece a la oficina destino')
        return redirect('correspondencia:urgencia_detalle', pk=pk)
    
    if urgencia.tomar(request.user):
        if is_ajax:
            return JsonResponse({
                'success': True,
                'message': f'{request.user.get_full_name()} está trabajando en esta urgencia'
            })
        messages.success(request, 'Ahora estás trabajando en esta urgencia')
        return redirect('correspondencia:urgencia_detalle', pk=pk)
    else:
        if is_ajax:
            return JsonResponse({
                'success': False,
                'error': 'La urgencia ya fue tomada o está respondida'
            }, status=400)
        messages.warning(request, 'La urgencia ya fue tomada o está respondida')
        return redirect('correspondencia:urgencia_detalle', pk=pk)


@login_required
@require_http_methods(["POST"])
def responder_urgencia(request, pk):
    """Responder una urgencia con destinatarios completos (usa lógica del modal de correspondencia)"""
    urgencia = get_object_or_404(CorrespondenciaUrgencia, pk=pk)
    
    # Verificar permisos
    try:
        puede_responder = request.user.perfil.oficina == urgencia.oficina_destino
    except AttributeError:
        puede_responder = False
    
    if not puede_responder:
        messages.error(request, 'No tiene permisos para responder esta urgencia')
        return redirect('correspondencia:urgencia_detalle', pk=pk)
    
    if urgencia.estado not in ['PENDIENTE', 'EN_PROCESO']:
        messages.warning(request, 'Esta urgencia ya fue respondida o está vencida')
        return redirect('correspondencia:urgencia_detalle', pk=pk)
    
    # Obtener datos del formulario (igual que responder_correspondencia_ajax)
    asunto = normalizar_asunto_salida(request.POST.get('asunto') or '')
    cuerpo = request.POST.get('cuerpo')
    destinatarios_contacto_ids = request.POST.getlist('destinatarios_contacto')
    destinatarios_email = [e.strip() for e in request.POST.getlist('destinatarios_email') if e.strip()]
    categoria_contacto_id = (request.POST.get('categoria_contacto_id') or '').strip()
    adjuntos_files = request.FILES.getlist('adjuntos')
    
    # Validar tamaño total de adjuntos (25MB)
    total_adjuntos_bytes = sum(getattr(f, 'size', 0) for f in adjuntos_files)
    SIZE_LIMIT_BYTES = 25 * 1024 * 1024
    if total_adjuntos_bytes > SIZE_LIMIT_BYTES:
        messages.error(request, 'El tamaño total de adjuntos supera 25MB.')
        return redirect('correspondencia:urgencia_detalle', pk=pk)
    
    # Validar destinatarios
    total_destinatarios = len(destinatarios_contacto_ids) + len(destinatarios_email)
    
    # Validar que no se mezclen categoría con destinatarios manuales
    if categoria_contacto_id and (destinatarios_contacto_ids or destinatarios_email):
        messages.error(request, 'No puede seleccionar una categoría y destinatarios manuales al mismo tiempo.')
        return redirect('correspondencia:urgencia_detalle', pk=pk)
    
    # Validar que haya al menos un destinatario
    if not categoria_contacto_id and total_destinatarios == 0:
        messages.error(request, 'Debe seleccionar al menos un destinatario o una categoría.')
        return redirect('correspondencia:urgencia_detalle', pk=pk)
    
    if not all([asunto, cuerpo]):
        messages.error(request, 'Los campos asunto y cuerpo son obligatorios.')
        return redirect('correspondencia:urgencia_detalle', pk=pk)
    
    # Obtener oficina del usuario
    perfil_usuario = getattr(request.user, 'perfil', None)
    oficina_usuario = getattr(perfil_usuario, 'oficina', None)
    
    # Procesar destinatarios según el tipo seleccionado
    contactos = []
    if categoria_contacto_id:
        # Obtener contactos de la categoría (grupo de agenda)
        try:
            grupo = GrupoAgenda.objects.get(
                id=categoria_contacto_id,
                oficina_propietaria=oficina_usuario,
                activo=True
            )
            contactos = list(grupo.contactos.filter(
                correo_electronico__isnull=False
            ).exclude(correo_electronico=''))
        except GrupoAgenda.DoesNotExist:
            messages.error(request, 'La categoría seleccionada no existe o no pertenece a su oficina.')
            return redirect('correspondencia:urgencia_detalle', pk=pk)
    else:
        # Procesar destinatarios manuales
        contactos = list(Contacto.objects.filter(id__in=destinatarios_contacto_ids))
    
    # Normalización y deduplicación por email
    contactos_by_email = {(c.correo_electronico or '').strip().lower(): c for c in contactos if c.correo_electronico}
    manual_validos = [em.strip().lower() for em in destinatarios_email]
    
    # Unir y deduplicar
    emails_unicos = set(list(contactos_by_email.keys()) + manual_validos)

    from correspondencia.utils.blocked_recipients import validar_emails_destinatario_permitidos
    ok_destinatarios, error_destinatarios = validar_emails_destinatario_permitidos(emails_unicos)
    if not ok_destinatarios:
        messages.error(request, error_destinatarios)
        return redirect('correspondencia:urgencia_detalle', pk=pk)
    
    # Límite 50 destinatarios tras deduplicación
    if len(emails_unicos) > 50:
        messages.error(request, f'No se permiten más de 50 destinatarios (tras normalización).')
        return redirect('correspondencia:urgencia_detalle', pk=pk)
    
    # Validar que haya al menos un destinatario válido
    if not emails_unicos:
        messages.error(request, 'Debe seleccionar al menos un destinatario válido.')
        return redirect('correspondencia:urgencia_detalle', pk=pk)
    
    try:
        with transaction.atomic():
            # 1. Crear la correspondencia de SALIDA (igual que respuesta normal)
            respuesta_salida = CorrespondenciaSalida.objects.create(
                respuesta_a_urgencia=urgencia,  # Nueva relación con urgencia
                usuario_redactor=request.user,
                asunto=asunto,
                cuerpo=cuerpo,
                destinatario_contacto=contactos[0] if contactos else None,
                estado='PENDIENTE_APROBACION'  # Va directo a aprobación
            )
            
            # 2. Trazabilidad de modalidad de envío
            total_dest = len(emails_unicos)
            if categoria_contacto_id:
                respuesta_salida.envio_tipo = 'GRUPO'
                try:
                    respuesta_salida.envio_grupo = GrupoAgenda.objects.get(id=categoria_contacto_id)
                except GrupoAgenda.DoesNotExist:
                    respuesta_salida.envio_grupo = None
                respuesta_salida.envio_total_destinatarios = total_dest
                respuesta_salida.envio_detalle_snapshot = f"{total_dest} contactos (deduplicados)"
            else:
                if total_dest <= 1:
                    respuesta_salida.envio_tipo = 'INDIVIDUAL'
                else:
                    respuesta_salida.envio_tipo = 'MULTIPLE_SELECTIVO'
                respuesta_salida.envio_total_destinatarios = total_dest
                respuesta_salida.envio_detalle_snapshot = f"{total_dest} destinatarios (deduplicados)"
            respuesta_salida.save(update_fields=['envio_tipo', 'envio_grupo', 'envio_total_destinatarios', 'envio_detalle_snapshot'])
            
            # 3. Crear destinatarios desde emails_unicos
            destinatarios_a_crear = []
            for em in emails_unicos:
                c = contactos_by_email.get(em)
                destinatarios_a_crear.append(SalidaDestinatario(
                    correspondencia_salida=respuesta_salida,
                    contacto=c,
                    email_snapshot=em,
                    nombre_snapshot=(c.nombre_completo if c else em),
                    estado='PENDIENTE'
                ))
            
            if destinatarios_a_crear:
                SalidaDestinatario.objects.bulk_create(destinatarios_a_crear)
            
            # 4. Procesar archivos adjuntos
            adjuntos_a_crear = []
            for archivo in adjuntos_files:
                adjuntos_a_crear.append(AdjuntoSalida(
                    correspondencia_salida=respuesta_salida,
                    archivo=archivo,
                    nombre_original=archivo.name
                ))
            
            if adjuntos_a_crear:
                AdjuntoSalida.objects.bulk_create(adjuntos_a_crear)
            
            # 5. Crear historial de envío a aprobación
            HistorialSalida.objects.create(
                correspondencia_salida=respuesta_salida,
                tipo_evento='ENVIO_APROBACION',
                usuario=request.user,
                descripcion=f'Respuesta a urgencia {urgencia.radicado} enviada para aprobación.'
            )
            
            # 6. Marcar la urgencia como respondida
            urgencia.responder(
                usuario=request.user,
                texto_respuesta=f"Respuesta enviada a aprobación: {respuesta_salida.numero_radicado_salida}"
            )
            
            # 7. Notificar a quien radicó la urgencia
            Notificacion.objects.create(
                usuario=urgencia.usuario_radica,
                tipo='urgencia',
                titulo=f'Urgencia {urgencia.radicado} respondida',
                mensaje=f'{request.user.get_full_name()} respondió la urgencia. Radicado salida: {respuesta_salida.numero_radicado_salida}',
                url=f'/registros/correspondencia/urgencias/{urgencia.pk}/'
            )
            
            messages.success(
                request, 
                f'Respuesta creada exitosamente. Radicado de salida: {respuesta_salida.numero_radicado_salida}. '
                f'Se enviará a {len(emails_unicos)} destinatario(s) tras aprobación.'
            )
            
    except Exception as e:
        messages.error(request, f'Error al responder urgencia: {str(e)}')
    
    return redirect('correspondencia:urgencia_detalle', pk=pk)


# === API ENDPOINTS ===

@login_required
@require_http_methods(["POST"])
def api_radicar_urgencia(request):
    """API AJAX para radicar urgencia"""
    import json
    
    try:
        data = json.loads(request.body)
        correo_id = data.get('correo_id')
        
        if not es_ventanilla(request.user):
            return JsonResponse({
                'success': False,
                'error': 'No tiene permisos para radicar urgencias'
            }, status=403)
        
        correo = get_object_or_404(CorreoEntrante, pk=correo_id)
        
        with transaction.atomic():
            urgencia = CorrespondenciaUrgencia.objects.create(
                correo_entrante=correo,
                usuario_radica=request.user,
                serie_id=data.get('serie_id'),
                subserie_id=data.get('subserie_id'),
                oficina_destino_id=data.get('oficina_destino_id'),
                horas_limite=data.get('horas_limite', 24),
                prioridad=data.get('prioridad', 'ALTA'),
                motivo_urgencia=data.get('motivo_urgencia', ''),
                observaciones=data.get('observaciones', '')
            )
            
            correo.procesado = True
            correo.urgencia_asociada = urgencia
            correo.save()
            
            _crear_notificaciones_urgencia(urgencia)
        
        return JsonResponse({
            'success': True,
            'radicado': urgencia.radicado,
            'urgencia_id': urgencia.pk,
            'url': f'/correspondencia/urgencias/{urgencia.pk}/'
        })
    
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)


@login_required
def api_notificaciones_urgencias(request):
    """API para obtener notificaciones de urgencias"""
    notificaciones = Notificacion.objects.filter(
        usuario=request.user,
        tipo='urgencia',
        leida=False
    ).order_by('-fecha_creacion')[:20]
    
    data = [{
        'id': n.id,
        'titulo': n.titulo,
        'mensaje': n.mensaje,
        'fecha': n.fecha_creacion.isoformat(),
        'url': n.url
    } for n in notificaciones]
    
    return JsonResponse({
        'success': True,
        'notificaciones': data,
        'total': len(data)
    })


# === FUNCIONES AUXILIARES ===

def _crear_notificaciones_urgencia(urgencia):
    """
    Crea notificaciones para todos los usuarios de la oficina destino.
    Excluye a quien radicó.
    """
    # En esta implementación, la oficina del usuario está en PerfilUsuario
    usuarios_oficina = (
        User.objects.filter(perfil__oficina=urgencia.oficina_destino, is_active=True)
        .exclude(id=urgencia.usuario_radica.id)
        .distinct()
    )
    
    notificaciones = []
    for usuario in usuarios_oficina:
        notificaciones.append(Notificacion(
            usuario=usuario,
            tipo='urgencia',
            titulo=f'Nueva Urgencia: {urgencia.radicado}',
            mensaje=f'{urgencia.prioridad} - {urgencia.correo_entrante.asunto[:100]}',
            url=f'/correspondencia/urgencias/{urgencia.pk}/'
        ))
    
    Notificacion.objects.bulk_create(notificaciones)
