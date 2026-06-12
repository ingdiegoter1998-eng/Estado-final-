from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import redirect
from django.contrib import messages

from .models import CorrespondenciaSalida, HistorialSalida
from .aprobacion_envio import aprobar_y_enviar_una_respuesta
import traceback


@login_required
@user_passes_test(lambda u: u.groups.filter(name='Ventanilla').exists(), login_url='correspondencia:welcome')
def aprobar_todas_respuestas(request):
    """Aprueba masivamente todas las respuestas pendientes de aprobación."""
    if request.method != 'POST':
        messages.error(request, 'Método no permitido.')
        return redirect('correspondencia:bandeja_respuestas_pendientes')

    respuestas_pendientes = CorrespondenciaSalida.objects.filter(
        estado__in=['PENDIENTE_APROBACION', 'ERROR_ENVIO']
    ).prefetch_related('destinatarios', 'adjuntos')

    total_aprobadas = 0
    total_errores = 0

    for respuesta in respuestas_pendientes:
        try:
            enviados, total = aprobar_y_enviar_una_respuesta(respuesta, request.user)
            if total > 0 and enviados == total:
                total_aprobadas += 1
            elif enviados > 0:
                total_errores += 1
                messages.warning(
                    request,
                    f'Envío parcial en {respuesta.numero_radicado_salida}: {enviados}/{total} destinatarios OK.'
                )
            else:
                total_errores += 1
                messages.warning(request, f'No se pudo enviar: {respuesta.numero_radicado_salida}')
        except Exception as e:
            total_errores += 1
            try:
                respuesta.estado = 'ERROR_ENVIO'
                respuesta.save(update_fields=['estado'])
                HistorialSalida.objects.create(
                    correspondencia_salida=respuesta,
                    tipo_evento='ENVIO_FALLIDO',
                    usuario=request.user,
                    descripcion=f"Error: {e}\n{traceback.format_exc()}"
                )
            except Exception:
                pass
            messages.warning(request, f'Error al procesar {respuesta.numero_radicado_salida}: {str(e)}')

    if total_aprobadas > 0:
        messages.success(request, f'✓ Se aprobaron y enviaron {total_aprobadas} respuestas exitosamente.')

    if total_errores > 0:
        messages.error(request, f'✗ Hubo {total_errores} errores al procesar algunas respuestas.')

    return redirect('correspondencia:bandeja_respuestas_pendientes')
