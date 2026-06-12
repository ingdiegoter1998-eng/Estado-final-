import json

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_GET, require_POST

from .models import AsistenteChunk, AsistenteConversacion, AsistenteDocumento, AsistenteMensaje
from .services_chatbot import ChatbotOrchestrator, GeminiFlashService


def build_chatbot_ui_context(user) -> dict:
    return {
        'chatbot_conversations': AsistenteConversacion.objects.filter(usuario=user)[:12],
        'chatbot_documents_count': AsistenteDocumento.objects.filter(activo=True).count(),
        'chatbot_chunks_count': AsistenteChunk.objects.count(),
        'gemini_configured': GeminiFlashService().is_configured(),
    }


def _serialize_conversation(conversation: AsistenteConversacion) -> dict:
    last_message = conversation.mensajes.order_by('-creado_en').first()
    return {
        'id': conversation.id,
        'title': conversation.titulo,
        'updated_at': conversation.actualizado_en.isoformat(),
        'last_message_preview': (last_message.contenido[:120] if last_message else ''),
        'messages_count': conversation.mensajes.count(),
    }


def _serialize_message(message: AsistenteMensaje) -> dict:
    return {
        'id': message.id,
        'role': message.rol,
        'content': message.contenido,
        'citations': message.citas,
        'metadata': message.metadata,
        'created_at': message.creado_en.isoformat(),
    }


def _get_user_conversation(user, conversation_id: int) -> AsistenteConversacion:
    return get_object_or_404(AsistenteConversacion, id=conversation_id, usuario=user)


def _ensure_chatbot_superuser(request) -> None:
    """Chatbot is now available to all authenticated users."""
    return


@login_required
def asistente_chatbot(request):
    _ensure_chatbot_superuser(request)
    context = {
        'titulo_pagina': 'Asistente documental',
    }
    return render(request, 'correspondencia/usuario/asistente_chatbot.html', context)


@login_required
@require_GET
def chatbot_conversations_api(request):
    _ensure_chatbot_superuser(request)
    conversations = AsistenteConversacion.objects.filter(usuario=request.user)
    return JsonResponse({'results': [_serialize_conversation(item) for item in conversations]})


@login_required
@require_POST
def chatbot_create_conversation_api(request):
    _ensure_chatbot_superuser(request)
    conversation = AsistenteConversacion.objects.create(usuario=request.user)
    return JsonResponse({'conversation': _serialize_conversation(conversation)}, status=201)


@login_required
@require_GET
def chatbot_messages_api(request, conversation_id: int):
    _ensure_chatbot_superuser(request)
    conversation = _get_user_conversation(request.user, conversation_id)
    messages = conversation.mensajes.all()
    return JsonResponse({
        'conversation': _serialize_conversation(conversation),
        'messages': [_serialize_message(item) for item in messages],
    })


@login_required
@require_POST
def chatbot_ask_api(request, conversation_id: int):
    _ensure_chatbot_superuser(request)
    conversation = _get_user_conversation(request.user, conversation_id)
    payload = json.loads(request.body.decode('utf-8') or '{}')
    question = (payload.get('question') or '').strip()
    if not question:
        return JsonResponse({'error': 'La pregunta es obligatoria.'}, status=400)

    if not AsistenteDocumento.objects.filter(activo=True).exists():
        return JsonResponse({
            'error': 'No hay documentos indexados para el asistente. Ejecuta la indexación inicial antes de usar el chat.'
        }, status=400)

    user_message = AsistenteMensaje.objects.create(
        conversacion=conversation,
        rol=AsistenteMensaje.Rol.USER,
        contenido=question,
    )

    if conversation.titulo == 'Nueva conversación':
        conversation.titulo = question[:80]

    try:
        orchestrator = ChatbotOrchestrator()
        answer = orchestrator.answer(conversation, question)
    except RuntimeError as exc:
        return JsonResponse({'error': str(exc)}, status=503)
    except Exception as exc:
        return JsonResponse({
            'error': 'No fue posible obtener una respuesta del asistente en este momento. Intenta nuevamente.'
        }, status=503)

    assistant_message = AsistenteMensaje.objects.create(
        conversacion=conversation,
        rol=AsistenteMensaje.Rol.ASSISTANT,
        contenido=answer['content'],
        citas=answer['citations'],
        metadata=answer['metadata'],
    )
    conversation.ultima_pregunta_at = user_message.creado_en
    conversation.save(update_fields=['titulo', 'ultima_pregunta_at', 'actualizado_en'])

    return JsonResponse({
        'conversation': _serialize_conversation(conversation),
        'user_message': _serialize_message(user_message),
        'assistant_message': _serialize_message(assistant_message),
    })