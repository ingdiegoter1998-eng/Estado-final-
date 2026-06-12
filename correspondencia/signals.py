from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.db import transaction
from django.urls import reverse
from .models import CorreoEntrante, Correspondencia, Contacto, HistorialCorrespondencia, DistribucionInternaUsuario, Notificacion, ComunicacionInterna
import logging

logger = logging.getLogger(__name__)

# Constantes de confianza (ajustar según sea necesario)
CONFIANZA_MINIMA_CLASIFICACION = 0.8 # Ejemplo: Umbral de confianza para clasif. IA

@receiver(post_save, sender=CorreoEntrante)
def intentar_radicacion_automatica(sender, instance, created, **kwargs):
    """Señal que intenta radicar automáticamente un correo cuando se marca como procesado."""
    # Solo actuar si el correo está procesado, no está radicado, no requiere revisión, y no se está creando (para evitar loops si se guarda de nuevo)
    if instance.procesado and not instance.radicado_asociado and not instance.requiere_revision_manual and not created:
        logger.info(f"[AutoRad] Iniciando intento de radicación para CorreoEntrante ID: {instance.pk}")
        
        radicado_exitoso = False
        mensaje_error = ""

        try:
            with transaction.atomic(): # Asegurar atomicidad
                # --- 1. Manejo de Contacto --- 
                contacto = buscar_o_crear_contacto_auto(instance.remitente)
                if not contacto:
                    mensaje_error = "No se pudo determinar/crear el contacto."
                    raise ValueError(mensaje_error)
                logger.info(f"[AutoRad] Contacto determinado/creado: {contacto.id}")

                # --- 2. Validación de Clasificación --- 
                # Aquí iría la lógica para verificar la confianza de la IA si estuviera disponible
                # if instance.confianza_clasificacion < CONFIANZA_MINIMA_CLASIFICACION:
                #     mensaje_error = "Confianza de clasificación IA demasiado baja."
                #     raise ValueError(mensaje_error)
                
                # Validar que los campos clasificados no sean nulos (asumiendo que son obligatorios para radicar)
                if not instance.oficina_clasificada or not instance.serie_clasificada:
                    mensaje_error = "Falta Oficina o Serie clasificada por IA."
                    raise ValueError(mensaje_error)
                logger.info("[AutoRad] Clasificación IA validada.")

                # --- 3. Determinación de Respuesta y Tiempo (Lógica Placeholder) --- 
                # !! Lógica muy básica, necesita IA real o reglas más complejas !!
                requiere_respuesta = False
                tiempo_respuesta = None
                if "solicitud" in instance.asunto.lower() or "pregunta" in instance.asunto.lower() or "requiero" in instance.cuerpo_texto.lower():
                    requiere_respuesta = True
                    tiempo_respuesta = 'NORMAL' # Asumir normal por defecto
                logger.info(f"[AutoRad] Requiere respuesta: {requiere_respuesta}, Tiempo: {tiempo_respuesta}")

                # --- 4. Creación de Correspondencia --- 
                correspondencia = Correspondencia.objects.create(
                    # tipo_radicado se asume ENTRANTE por defecto
                    remitente=contacto,
                    asunto=instance.asunto,
                    serie=instance.serie_clasificada,
                    subserie=instance.subserie_clasificada, # Puede ser None si la IA no lo asignó
                    medio_recepcion='ELECTRONICO', # Asumir electrónico si viene de CorreoEntrante
                    requiere_respuesta=requiere_respuesta,
                    tiempo_respuesta=tiempo_respuesta,
                    oficina_destino=instance.oficina_clasificada,
                    estado='RADICADA' # Estado inicial después de radicar
                    # usuario_radicador podría ser None o un usuario sistema si se crea
                )
                logger.info(f"[AutoRad] Correspondencia {correspondencia.numero_radicado} creada.")

                # --- 5. Asociar Correo y Crear Historial --- 
                instance.radicado_asociado = correspondencia
                instance.save(update_fields=['radicado_asociado']) # Guardar solo el campo cambiado
                logger.info(f"[AutoRad] CorreoEntrante {instance.pk} asociado a Correspondencia {correspondencia.numero_radicado}.")

                HistorialCorrespondencia.objects.create(
                    correspondencia=correspondencia,
                    evento='RADICADA',
                    descripcion="Radicada automáticamente desde correo electrónico."
                    # usuario podría ser None o un usuario sistema
                )
                logger.info("[AutoRad] Historial 'RADICADA' creado.")

                radicado_exitoso = True

        except Exception as e:
            # Si algo falla, marcar para revisión manual
            logger.error(f"[AutoRad] Error al radicar CorreoEntrante {instance.pk}: {e}")
            instance.requiere_revision_manual = True
            instance.save(update_fields=['requiere_revision_manual'])
            # Podríamos enviar una notificación al administrador aquí
            
        if radicado_exitoso:
             logger.info(f"[AutoRad] Radicación automática exitosa para CorreoEntrante {instance.pk}.")
        else:
             logger.warning(f"[AutoRad] Radicación automática fallida para CorreoEntrante {instance.pk}. Marcado para revisión manual. Razón: {mensaje_error}")

def buscar_o_crear_contacto_auto(email_remitente):
    """Lógica (simplificada) para encontrar o crear un contacto basado en email."""
    try:
        # Intenta encontrar por email exacto (ignorar mayúsculas/minúsculas)
        contacto = Contacto.objects.get(correo_electronico__iexact=email_remitente)
        return contacto
    except Contacto.DoesNotExist:
        # Si no existe, crear uno muy básico
        # !! Esta lógica debería mejorarse extrayendo más info del correo si es posible !!
        try:
            nombre_entidad = f"Entidad de {email_remitente}" # Nombre muy genérico
            contacto = Contacto.objects.create(
                correo_electronico=email_remitente,
                entidad=nombre_entidad
                # nombres y apellidos quedarían nulos por ahora
            )
            logger.info(f"[AutoRad] Contacto creado automáticamente para {email_remitente}")
            return contacto
        except Exception as e:
            logger.error(f"[AutoRad] Error al crear contacto para {email_remitente}: {e}")
            return None # Falló la creación
    except Contacto.MultipleObjectsReturned:
        # Si hay varios contactos con el mismo email (debería evitarse con constraint)
        logger.warning(f"[AutoRad] Múltiples contactos encontrados para {email_remitente}. Se requiere intervención manual.")
        return None # Requiere intervención manual


@receiver(post_save, sender=DistribucionInternaUsuario)
def crear_notificacion_asignacion(sender, instance, created, **kwargs):
    """
    Crea una notificación cuando se asigna correspondencia a un usuario.
    Se ejecuta al crear una nueva distribución interna.
    """
    if created:
        try:
            correspondencia = instance.correspondencia
            usuario = instance.usuario_asignado
            titulo = "Nueva asignación"
            mensaje = "Se te asignó una notificación"
            
            # Determinar URL de destino
            url = reverse('correspondencia:detalle_correspondencia', kwargs={'pk': correspondencia.pk})
            
            # Crear la notificación
            Notificacion.objects.create(
                usuario=usuario,
                tipo='asignacion',
                titulo=titulo,
                mensaje=mensaje,
                correspondencia=correspondencia,
                url=url
            )
            
            logger.info(f"Notificación creada para usuario {usuario.username} - Correspondencia {correspondencia.numero_radicado}")
            
        except Exception as e:
            logger.error(f"Error al crear notificación de asignación: {str(e)}")


@receiver(post_save, sender=Correspondencia)
def notificar_correspondencia_compartida(sender, instance, created, **kwargs):
    """
    Notifica cuando se comparte correspondencia con múltiples usuarios.
    Se ejecuta cuando hay más de una distribución interna (correspondencia compartida).
    """
    if not created:  # Solo para actualizaciones
        try:
            # Contar distribuciones internas
            total_distribuciones = instance.distribuciones_internas.count()
            
            # Si hay más de 1, es correspondencia compartida
            if total_distribuciones > 1:
                # Obtener la última distribución (la más reciente)
                ultima_distribucion = instance.distribuciones_internas.order_by('-fecha_asignacion').first()
                
                # Verificar si ya existe notificación para esta distribución
                # (evitar crear duplicados)
                if ultima_distribucion:
                    existe = Notificacion.objects.filter(
                        usuario=ultima_distribucion.usuario_asignado,
                        correspondencia=instance,
                        tipo='compartido'
                    ).exists()
                    
                    if not existe:
                        compartido_por = ultima_distribucion.asignado_por
                        compartidor_nombre = compartido_por.get_full_name() or compartido_por.username if compartido_por else "un usuario"
                        
                        Notificacion.objects.create(
                            usuario=ultima_distribucion.usuario_asignado,
                            tipo='compartido',
                            titulo=f"Correspondencia compartida por {compartidor_nombre}",
                            mensaje=f"Se compartió contigo la correspondencia {instance.numero_radicado}. Asunto: {instance.asunto[:100]}",
                            correspondencia=instance,
                            url=reverse('correspondencia:detalle_correspondencia', kwargs={'pk': instance.pk})
                        )
                        
                        logger.info(f"Notificación de compartido creada para {ultima_distribucion.usuario_asignado.username}")
        
        except Exception as e:
            logger.error(f"Error al notificar correspondencia compartida: {str(e)}")


# Signal para ComunicacionInterna - Forzar estado PENDIENTE_APROBACION al crear
@receiver(pre_save, sender=ComunicacionInterna)
def establecer_estado_comunicacion_interna(sender, instance, **kwargs):
    """
    Signal que asegura que las comunicaciones internas creadas vía formulario
    se establezcan con estado PENDIENTE_APROBACION en lugar de BORRADOR.
    
    EXCEPTO: Si se especifica un estado distinto (APROBADA, DISTRIBUIDA, etc),
    se respeta el estado establecido por la vista (ej: líderes creando pre-aprobadas).
    """
    # Solo aplica si el objeto se está creando (pk es None) y el estado es BORRADOR
    # Si ya tiene otro estado especificado (por ej: APROBADA, DISTRIBUIDA), lo respetamos
    if instance.pk is None and instance.estado == 'BORRADOR':
        instance.estado = 'PENDIENTE_APROBACION'
        logger.info(f"[ComunicacionInterna] Comunicación nueva ajustada a PENDIENTE_APROBACION") 