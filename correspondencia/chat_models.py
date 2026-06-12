"""
Modelos para el sistema de chat de soporte interno.
Permite a usuarios reportar errores / consultas y a admins responder.
"""
import os
import uuid
from django.conf import settings
from django.db import models


def chat_adjunto_path(instance, filename):
    ext = os.path.splitext(filename)[1].lower()
    safe_name = f"{uuid.uuid4().hex}{ext}"
    return f"chat_adjuntos/{instance.mensaje.conversacion_id}/{safe_name}"


class ChatConversation(models.Model):
    """Hilo de conversación abierto por un usuario."""

    ESTADO_CHOICES = [
        ('abierta', 'Abierta'),
        ('cerrada', 'Cerrada'),
    ]
    PRIORIDAD_CHOICES = [
        ('normal', 'Normal'),
        ('urgente', 'Urgente'),
    ]

    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='chat_conversaciones',
    )
    asunto = models.CharField(max_length=200)
    estado = models.CharField(
        max_length=10, choices=ESTADO_CHOICES, default='abierta', db_index=True,
    )
    prioridad = models.CharField(
        max_length=10, choices=PRIORIDAD_CHOICES, default='normal',
    )
    creado = models.DateTimeField(auto_now_add=True)
    actualizado = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Conversación de chat'
        verbose_name_plural = 'Conversaciones de chat'
        ordering = ['-actualizado']

    def __str__(self):
        return f'[{self.id}] {self.asunto} — {self.usuario}'


class ChatMessage(models.Model):
    """Mensaje individual dentro de una conversación."""

    conversacion = models.ForeignKey(
        ChatConversation,
        on_delete=models.CASCADE,
        related_name='mensajes',
    )
    autor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='chat_mensajes',
    )
    texto = models.TextField()
    es_admin = models.BooleanField(
        default=False,
        help_text='True si el mensaje fue enviado por un admin/superusuario.',
    )
    leido = models.BooleanField(default=False)
    creado = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Mensaje de chat'
        verbose_name_plural = 'Mensajes de chat'
        ordering = ['creado']

    def __str__(self):
        quien = 'Admin' if self.es_admin else 'Usuario'
        return f'{quien}: {self.texto[:50]}'


class ChatAdjunto(models.Model):
    """Imagen o captura adjunta a un mensaje de chat."""

    mensaje = models.ForeignKey(
        ChatMessage,
        on_delete=models.CASCADE,
        related_name='adjuntos',
    )
    archivo = models.ImageField(upload_to=chat_adjunto_path)
    nombre_original = models.CharField(max_length=255)
    creado = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Adjunto de chat'
        verbose_name_plural = 'Adjuntos de chat'

    def __str__(self):
        return self.nombre_original
