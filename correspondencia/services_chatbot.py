from __future__ import annotations

import json
import os
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import requests
from django.conf import settings
from django.db.models import Q

from .models import AsistenteChunk, AsistenteConversacion, AsistenteDocumento, AsistenteMensaje


TOKEN_RE = re.compile(r"[a-zA-Z0-9áéíóúñü]{3,}", re.IGNORECASE)
STOPWORDS = {
    'que', 'como', 'para', 'por', 'una', 'uno', 'unos', 'unas', 'soy', 'eres', 'ser',
    'quiero', 'puedo', 'puedes', 'capaz', 'hacer', 'ayuda', 'favor', 'con', 'del',
    'las', 'los', 'este', 'esta', 'esto', 'ese', 'esa', 'hola', 'buenas',
}
QUERY_SYNONYMS = {
    'enviar': ['respuesta', 'salida', 'correo'],
    'mandar': ['respuesta', 'salida', 'correo'],
    'correspondencia': ['radicar', 'respuesta', 'ventanilla'],
    'correo': ['radicar', 'respuesta', 'ventanilla'],
    'soporte': ['ayuda', 'flujo', 'proceso'],
}
GREETING_TOKENS = {
    'hola', 'holi', 'buenas', 'saludos', 'hello', 'hi', 'hey',
    'buenos', 'dias', 'buenas', 'tardes', 'noches',
}
DEFAULT_DOC_PATHS = [
    'README.md',
    'analisis',
    'documentacion',
    'cambios',
    'manual tecnico',
    'guias',
]
ALLOWED_EXTENSIONS = {'.md', '.txt'}
RETRYABLE_HTTP_STATUS = {502, 503, 504}
DEFAULT_TRANSIENT_ERROR_MESSAGE = (
    'El asistente no está disponible en este momento por una falla temporal del servicio de IA. '
    'Intenta nuevamente en unos segundos.'
)
TRUNCATED_RESPONSE_MESSAGE = (
    'Encontré contexto útil, pero la respuesta quedó incompleta por límite de longitud. '
    'Hazme una pregunta más específica y te respondo por partes.'
)
TRUNCATED_RESPONSE_SUFFIX = 'Si necesitas más detalle, pídemelo en una pregunta más específica y te respondo por partes.'
SENTENCE_END_RE = re.compile(r'[.!?]["”]?$', re.UNICODE)


def tokenize(text: str) -> list[str]:
    tokens: list[str] = []
    seen: set[str] = set()
    for match in TOKEN_RE.findall((text or '').lower()):
        if match in STOPWORDS:
            continue
        if match not in seen:
            tokens.append(match)
            seen.add(match)
    return tokens


def build_search_text(*parts: str) -> str:
    combined = ' '.join(part for part in parts if part)
    return ' '.join(tokenize(combined))


def expand_query_tokens(tokens: list[str]) -> list[str]:
    expanded: list[str] = []
    seen: set[str] = set()
    for token in tokens:
        if token not in seen:
            expanded.append(token)
            seen.add(token)
        for synonym in QUERY_SYNONYMS.get(token, []):
            if synonym not in seen:
                expanded.append(synonym)
                seen.add(synonym)
    return expanded


def is_greeting(text: str) -> bool:
    raw_tokens = {m.lower() for m in TOKEN_RE.findall(text or '')}
    if not raw_tokens:
        return False
    return bool(raw_tokens & GREETING_TOKENS)


def is_send_correspondence_intent(text: str) -> bool:
    tokens = set(tokenize(text))
    if 'correspondencia' not in tokens and 'correo' not in tokens and 'radicado' not in tokens:
        return False
    return bool(tokens & {'enviar', 'mandar', 'respuesta', 'salida', 'radicar'})


def get_configured_doc_paths() -> list[str]:
    raw_paths = os.getenv('CHATBOT_DOC_PATHS', '')
    if raw_paths:
        try:
            parsed = json.loads(raw_paths)
            if isinstance(parsed, list):
                return [str(item) for item in parsed if str(item).strip()]
        except json.JSONDecodeError:
            pass
    return DEFAULT_DOC_PATHS


def iter_source_files(custom_paths: Iterable[str] | None = None) -> list[Path]:
    files: list[Path] = []
    base_dir = Path(settings.BASE_DIR)
    selected_paths = list(custom_paths or get_configured_doc_paths())

    for item in selected_paths:
        path = Path(item)
        resolved = path if path.is_absolute() else base_dir / path
        if resolved.is_file() and resolved.suffix.lower() in ALLOWED_EXTENSIONS:
            files.append(resolved)
            continue
        if resolved.is_dir():
            for file_path in sorted(resolved.rglob('*')):
                if file_path.is_file() and file_path.suffix.lower() in ALLOWED_EXTENSIONS:
                    files.append(file_path)
    return files


CODE_FENCE_RE = re.compile(r'```[\s\S]*?```', re.MULTILINE)
MIN_CHUNK_CHARS = 40


def split_document(text: str, max_chars: int = 1400) -> list[dict]:
    # Strip code blocks before splitting — they pollute headings and chunks
    cleaned = CODE_FENCE_RE.sub('', text)
    blocks = re.split(r'\n\s*\n', cleaned)
    chunks: list[dict] = []
    current_heading = ''
    buffer = ''

    def flush_buffer() -> None:
        nonlocal buffer
        content = buffer.strip()
        # Discard separators (---, ===) and very short fragments
        if content and len(content) >= MIN_CHUNK_CHARS and not re.fullmatch(r'[-=*_\s]{1,40}', content):
            chunks.append({
                'heading': current_heading,
                'content': content,
            })
        buffer = ''

    for raw_block in blocks:
        block = raw_block.strip()
        if not block:
            continue

        # Skip pure separator lines
        if re.fullmatch(r'[-=*_\s]{1,40}', block):
            continue

        if block.startswith('#'):
            flush_buffer()
            current_heading = block.lstrip('#').strip()
            continue

        candidate = f"{buffer}\n\n{block}".strip() if buffer else block
        if len(candidate) > max_chars and buffer:
            flush_buffer()
            buffer = block
        else:
            buffer = candidate

    flush_buffer()
    return chunks


@dataclass
class RetrievedChunk:
    chunk_id: int
    document_path: str
    title: str
    heading: str
    content: str
    score: float


class DocumentRetrievalService:
    def retrieve(self, question: str, limit: int = 6) -> list[RetrievedChunk]:
        tokens = expand_query_tokens(tokenize(question))
        qs = AsistenteChunk.objects.filter(documento__activo=True).select_related('documento')

        token_query = Q()
        for token in tokens[:8]:
            token_query |= Q(search_text__icontains=token)
            token_query |= Q(contenido__icontains=token)
            token_query |= Q(heading__icontains=token)
            token_query |= Q(documento__titulo__icontains=token)
            token_query |= Q(documento__ruta_relativa__icontains=token)

        if token_query:
            candidates = list(qs.filter(token_query)[:80])
        else:
            candidates = list(qs[:40])

        if not candidates:
            return []

        scored: list[RetrievedChunk] = []
        joined_question = (question or '').lower()
        token_set = set(tokens)

        for candidate in candidates:
            haystack_tokens = set(tokenize(candidate.contenido))
            overlap = len(token_set & haystack_tokens)
            if overlap == 0 and token_set:
                continue

            title_bonus = 0.8 if any(token in candidate.documento.titulo.lower() for token in tokens[:5]) else 0
            path_bonus = 0.6 if any(token in candidate.documento.ruta_relativa.lower() for token in tokens[:5]) else 0
            phrase_bonus = 1.2 if joined_question and joined_question in candidate.contenido.lower() else 0
            heading_bonus = 0.4 if candidate.heading and any(token in candidate.heading.lower() for token in tokens[:5]) else 0

            # Penalize very short chunks, reward substantive ones
            content_len = len(candidate.contenido)
            if content_len < MIN_CHUNK_CHARS:
                continue
            length_factor = min(content_len / 300, 1.5)  # up to 1.5x for chunks >= 450 chars

            # Coverage: what fraction of query tokens appear in the chunk
            coverage = overlap / max(len(token_set), 1)
            coverage_bonus = coverage * 2.0

            score = overlap * 1.7 + title_bonus + path_bonus + phrase_bonus + heading_bonus + coverage_bonus
            score *= length_factor

            scored.append(
                RetrievedChunk(
                    chunk_id=candidate.id,
                    document_path=candidate.documento.ruta_relativa,
                    title=candidate.documento.titulo,
                    heading=candidate.heading,
                    content=candidate.contenido,
                    score=score,
                )
            )

        scored.sort(key=lambda item: item.score, reverse=True)

        selected: list[RetrievedChunk] = []
        per_document: dict[str, int] = {}
        for item in scored:
            count = per_document.get(item.document_path, 0)
            if count >= 2:
                continue
            selected.append(item)
            per_document[item.document_path] = count + 1
            if len(selected) >= limit:
                break
        return selected


class GeminiFlashService:
    def __init__(self) -> None:
        self.api_key = os.getenv('GEMINI_API_KEY', '').strip()
        self.model = os.getenv('GEMINI_CHAT_MODEL', 'gemini-3-flash-preview').strip()
        self.max_output_tokens = int(os.getenv('GEMINI_CHAT_MAX_OUTPUT_TOKENS', '2048').strip() or '2048')
        self.max_retries = max(int(os.getenv('GEMINI_CHAT_MAX_RETRIES', '2').strip() or '2'), 0)
        self.retry_backoff_seconds = max(float(os.getenv('GEMINI_CHAT_RETRY_BACKOFF_SECONDS', '1').strip() or '1'), 0.0)

    def is_configured(self) -> bool:
        return bool(self.api_key)

    def _build_context_block(self, context_chunks: list[RetrievedChunk]) -> str:
        max_chunk_chars = 850
        max_context_chars = 4200
        sections: list[str] = []
        total_chars = 0

        for chunk in context_chunks:
            content = chunk.content.strip()
            if len(content) > max_chunk_chars:
                content = content[:max_chunk_chars].rsplit(' ', 1)[0].rstrip('.,;:') + '...'

            section = (
                f"[Fuente: {chunk.document_path}]\nTítulo: {chunk.title}\n"
                f"Sección: {chunk.heading or 'General'}\n{content}"
            )

            if total_chars >= max_context_chars:
                break

            remaining = max_context_chars - total_chars
            if len(section) > remaining:
                section = section[:remaining].rsplit(' ', 1)[0].rstrip('.,;:') + '...'

            sections.append(section)
            total_chars += len(section) + 2

        return '\n\n'.join(sections)

    def _is_retryable_exception(self, exc: requests.RequestException) -> bool:
        if isinstance(exc, (requests.Timeout, requests.ConnectionError)):
            return True
        if isinstance(exc, requests.HTTPError):
            return getattr(exc.response, 'status_code', None) in RETRYABLE_HTTP_STATUS
        return False

    def _normalize_truncated_text(self, text: str) -> str:
        cleaned = (text or '').strip()
        if not cleaned:
            return TRUNCATED_RESPONSE_MESSAGE

        lines = [line.strip() for line in cleaned.splitlines() if line.strip()]
        complete_lines = [line for line in lines if SENTENCE_END_RE.search(line)]

        if complete_lines:
            cleaned = '\n'.join(complete_lines).strip()
        else:
            last_punctuation = max(cleaned.rfind('.'), cleaned.rfind('!'), cleaned.rfind('?'))
            if last_punctuation > 0:
                cleaned = cleaned[: last_punctuation + 1].strip()
            else:
                cleaned = ''

        if not cleaned:
            return TRUNCATED_RESPONSE_MESSAGE

        return f'{cleaned}\n\n{TRUNCATED_RESPONSE_SUFFIX}'

    def generate(self, conversation: AsistenteConversacion, question: str, context_chunks: list[RetrievedChunk]) -> dict:
        if not self.is_configured():
            raise RuntimeError('GEMINI_API_KEY no está configurada.')

        history_messages = list(conversation.mensajes.order_by('-creado_en')[:6])
        history_messages.reverse()

        history_payload = []
        for message in history_messages:
            if message.rol not in {AsistenteMensaje.Rol.USER, AsistenteMensaje.Rol.ASSISTANT}:
                continue
            role = 'model' if message.rol == AsistenteMensaje.Rol.ASSISTANT else 'user'
            history_payload.append({
                'role': role,
                'parts': [{'text': message.contenido[:1400]}],
            })

        context_block = self._build_context_block(context_chunks)

        prompt = (
            'Pregunta del usuario:\n'
            f'{question.strip()}\n\n'
            'Información de referencia (solo para ti, NO la muestres al usuario):\n'
            f'{context_block or "Sin contexto disponible."}\n\n'
            'Instrucciones:\n'
            '- Responde en español claro, sencillo y operativo.\n'
            '- Transforma la información técnica en pasos prácticos que el usuario pueda seguir en el sistema.\n'
            '- Responde SOLO con lo que el contexto de referencia respalde. Si el contexto no cubre la pregunta, dilo amablemente.\n'
            '- Si no tienes respaldo suficiente, detente ahí. No des consejos genéricos, supuestos ni recomendaciones especulativas.\n'
            '- No inventes políticas, datos, pantallas ni procedimientos que no estén en el contexto.\n'
            '- NO menciones nombres de archivos, rutas, ni secciones del contexto.\n'
            '- NO incluyas sección de Fuentes.\n'
            '- NO uses Markdown.\n'
            '- NO uses negritas, asteriscos, encabezados ni listas con viñetas tipo *.\n'
            '- Si necesitas enumerar pasos, usa formato simple como 1. Paso uno, 2. Paso dos.\n'
            '- Sé conciso: responde en máximo 4-6 oraciones o pasos. Si el tema es complejo, ofrece ampliar.\n'
        )

        history_payload.append({
            'role': 'user',
            'parts': [{'text': prompt}],
        })

        url = f'https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent?key={self.api_key}'
        request_payload = {
            'systemInstruction': {
                'parts': [{
                    'text': (
                        'Eres un asistente amigable del sistema de correspondencia del Hospital del Sarare E.S.E. '
                        'Tu público son usuarios operativos (secretarias, auxiliares, jefes de oficina), NO desarrolladores.\n\n'
                        'CÓMO RESPONDER:\n'
                        '- Responde como si hablaras con alguien que usa el sistema día a día.\n'
                        '- Sé directo: primero la respuesta, luego los pasos si hacen falta.\n'
                        '- Usa lenguaje sencillo: "ve a tal pantalla", "haz clic en tal botón", "busca en la bandeja".\n'
                        '- Si el contexto habla de algo técnico (serializers, configuraciones, modelos), extrae solo lo útil para el usuario final.\n'
                        '- Sé conciso: máximo 4-6 oraciones o pasos. Si el tema necesita más detalle, ofrece ampliar.\n\n'
                        'REGLAS ESTRICTAS:\n'
                        '- NUNCA muestres nombres de archivos, rutas de código, nombres de templates, serializers, modelos Django ni detalles técnicos.\n'
                        '- NUNCA menciones Markdown, JSON, APIs, endpoints, ni nombres de archivos .md o .py.\n'
                        '- NO incluyas sección de Fuentes ni menciones rutas de documentos.\n'
                        '- NO uses Markdown ni formato enriquecido.\n'
                        '- NO uses texto entre ** **, ni viñetas con *, ni encabezados visuales.\n'
                        '- Si enumeras pasos, usa solo texto plano con 1., 2., 3.\n'
                        '- Si no tienes contexto suficiente para responder, dilo amablemente y detente ahí. NO inventes ni completes con consejos genéricos.'
                    )
                }]
            },
            'contents': history_payload,
            'generationConfig': {
                'temperature': 0.2,
                'maxOutputTokens': self.max_output_tokens,
            },
        }

        payload = None
        for attempt in range(self.max_retries + 1):
            try:
                response = requests.post(url, json=request_payload, timeout=45)
                response.raise_for_status()
                payload = response.json()
                break
            except requests.RequestException as exc:
                if self._is_retryable_exception(exc) and attempt < self.max_retries:
                    time.sleep(self.retry_backoff_seconds * (attempt + 1))
                    continue
                if self._is_retryable_exception(exc):
                    raise RuntimeError(DEFAULT_TRANSIENT_ERROR_MESSAGE) from exc
                raise

        if payload is None:
            raise RuntimeError(DEFAULT_TRANSIENT_ERROR_MESSAGE)

        candidate = (payload.get('candidates') or [{}])[0]
        parts = candidate.get('content', {}).get('parts', [])
        finish_reason = candidate.get('finishReason')
        text = '\n'.join(part.get('text', '') for part in parts if part.get('text')).strip()
        usage = payload.get('usageMetadata', {})

        if finish_reason == 'MAX_TOKENS':
            text = self._normalize_truncated_text(text)

        return {
            'text': text or 'No fue posible generar una respuesta en este momento.',
            'model': self.model,
            'finish_reason': finish_reason,
            'usage': usage,
        }


class ChatbotOrchestrator:
    def __init__(self, retrieval_service: DocumentRetrievalService | None = None, llm_service: GeminiFlashService | None = None) -> None:
        self.retrieval_service = retrieval_service or DocumentRetrievalService()
        self.llm_service = llm_service or GeminiFlashService()

    def answer(self, conversation: AsistenteConversacion, question: str) -> dict:
        if is_send_correspondence_intent(question):
            return {
                'content': (
                    'Si lo que necesitas es enviar una correspondencia, hay dos caminos dentro del sistema:\n\n'
                    '1. Si vas a responder un radicado entrante: abre la correspondencia recibida, entra al detalle y usa el botón "Responder radicado". '
                    'Se abrirá el modal "Responder Correspondencia", donde debes llenar asunto, cuerpo y destinatarios.\n\n'
                    '2. Si vas a crear una salida nueva desde cero: entra al dashboard de usuario y abre el modal de correspondencia de salida desde el sidebar o desde el dashboard.\n\n'
                    'Si me dices cuál de los dos casos tienes, te guío paso a paso: \n'
                    '- responder un radicado existente\n'
                    '- crear una salida nueva\n'
                    '- enviar con adjuntos\n'
                    '- enviar por Drive porque pesa demasiado'
                ),
                'citations': [
                    {
                        'document_path': 'correspondencia/templates/correspondencia/usuario/detalle_correspondencia.html',
                        'title': 'detalle_correspondencia.html',
                        'heading': 'Responder radicado',
                        'chunk_id': 0,
                    },
                    {
                        'document_path': 'correspondencia/templates/correspondencia/partials/modals/modal_responder_correspondencia.html',
                        'title': 'modal_responder_correspondencia.html',
                        'heading': 'Responder Correspondencia',
                        'chunk_id': 0,
                    },
                    {
                        'document_path': 'correspondencia/templates/correspondencia/bases/base_correspondencia_usuario.html',
                        'title': 'base_correspondencia_usuario.html',
                        'heading': 'Modal de correspondencia salida',
                        'chunk_id': 0,
                    },
                ],
                'metadata': {
                    'model': 'fallback-local',
                    'usage': {},
                    'retrieved_chunks': 0,
                },
            }

        context_chunks = self.retrieval_service.retrieve(question)
        if not context_chunks:
            if is_greeting(question):
                return {
                    'content': (
                        'Hola. Ya tengo documentación indexada y puedo ayudarte con dudas operativas '
                        'del sistema. Pregúntame por un flujo, un módulo, una pantalla o un proceso específico.'
                    ),
                    'citations': [],
                    'metadata': {
                        'model': 'fallback-local',
                        'usage': {},
                        'retrieved_chunks': 0,
                    },
                }

            return {
                'content': (
                    'No encontré contexto documental relacionado con esa consulta dentro del índice actual. '
                    'Prueba con una pregunta más específica sobre un proceso, módulo o pantalla del sistema.'
                ),
                'citations': [],
                'metadata': {
                    'model': 'fallback-local',
                    'usage': {},
                    'retrieved_chunks': 0,
                },
            }

        llm_response = self.llm_service.generate(conversation, question, context_chunks)
        citations = [
            {
                'document_path': chunk.document_path,
                'title': chunk.title,
                'heading': chunk.heading,
                'chunk_id': chunk.chunk_id,
            }
            for chunk in context_chunks
        ]

        return {
            'content': llm_response['text'],
            'citations': citations,
            'metadata': {
                'model': llm_response['model'],
                'finish_reason': llm_response.get('finish_reason'),
                'usage': llm_response['usage'],
                'retrieved_chunks': len(context_chunks),
            },
        }


def index_documents(custom_paths: Iterable[str] | None = None, clear_existing: bool = False) -> dict:
    files = iter_source_files(custom_paths)
    if clear_existing:
        AsistenteChunk.objects.all().delete()
        AsistenteDocumento.objects.all().delete()

    indexed = 0
    skipped = 0
    for file_path in files:
        raw_text = file_path.read_text(encoding='utf-8', errors='ignore')
        normalized_text = raw_text.replace('\x00', ' ').strip()
        if not normalized_text:
            continue

        checksum = __import__('hashlib').sha256(normalized_text.encode('utf-8')).hexdigest()
        try:
            relative_path = str(file_path.relative_to(settings.BASE_DIR))
        except ValueError:
            relative_path = str(file_path)

        title = next((line.lstrip('#').strip() for line in normalized_text.splitlines() if line.strip().startswith('#')), file_path.stem)

        document, created = AsistenteDocumento.objects.get_or_create(
            ruta_relativa=relative_path,
            defaults={
                'titulo': title[:255],
                'checksum': checksum,
                'tipo_fuente': 'archivo',
                'metadata': {'extension': file_path.suffix.lower()},
                'activo': True,
            },
        )

        if not created and document.checksum == checksum and document.chunks.exists():
            skipped += 1
            if not document.activo:
                document.activo = True
                document.save(update_fields=['activo', 'indexado_en'])
            continue

        document.titulo = title[:255]
        document.checksum = checksum
        document.tipo_fuente = 'archivo'
        document.metadata = {'extension': file_path.suffix.lower()}
        document.activo = True
        document.save()

        document.chunks.all().delete()
        chunks = split_document(normalized_text)
        AsistenteChunk.objects.bulk_create([
            AsistenteChunk(
                documento=document,
                orden=index,
                heading=chunk['heading'][:255],
                contenido=chunk['content'],
                search_text=build_search_text(document.titulo, chunk['heading'], chunk['content'], relative_path),
                metadata={'source': relative_path},
            )
            for index, chunk in enumerate(chunks, start=1)
        ])
        indexed += 1

    return {
        'indexed': indexed,
        'skipped': skipped,
        'files_found': len(files),
    }