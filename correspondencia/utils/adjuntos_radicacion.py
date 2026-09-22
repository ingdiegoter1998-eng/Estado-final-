"""Límites y validación de adjuntos para los distintos formularios de radicación
(física y rápida, entrante y saliente).

Centralizado para que el límite sea el mismo en toda la aplicación sin importar
por cuál formulario entre el archivo — antes cada flujo tenía su propio número
(o ninguno), lo que llevaba a comportamientos inconsistentes y sin mensaje claro.

Alineado con los límites de adjuntos de correo (email_config.MAX_FILE_SIZE_MB /
MAX_TOTAL_SIZE_MB).
"""
import os

from django.core.exceptions import ValidationError

MAX_FILES = 10
MAX_FILE_SIZE_MB = 20
MAX_TOTAL_SIZE_MB = 40

EXTENSIONES_FISICO = ['.pdf', '.jpg', '.jpeg', '.png', '.tiff', '.bmp']
EXTENSIONES_GENERAL = ['.pdf', '.doc', '.docx', '.jpg', '.jpeg', '.png', '.tiff', '.bmp', '.xls', '.xlsx', '.zip']


def validar_lista_adjuntos(
    archivos,
    *,
    allowed_extensions=EXTENSIONES_GENERAL,
    max_files=MAX_FILES,
    max_file_size_mb=MAX_FILE_SIZE_MB,
    max_total_size_mb=MAX_TOTAL_SIZE_MB,
):
    """Valida cantidad, extensión y tamaño de una lista de archivos subidos
    (``UploadedFile``). Lanza ``ValidationError`` con un mensaje claro en
    español si algo no cumple. No guarda nada; solo valida.
    """
    if not archivos:
        return

    if len(archivos) > max_files:
        raise ValidationError(f"Máximo {max_files} archivos permitidos por correspondencia.")

    max_file_size = max_file_size_mb * 1024 * 1024
    max_total_size = max_total_size_mb * 1024 * 1024
    total_size = 0

    for adjunto_file in archivos:
        file_extension = os.path.splitext(adjunto_file.name)[1].lower()
        if file_extension not in allowed_extensions:
            raise ValidationError(
                f"Formato no permitido: {adjunto_file.name}. Solo se permiten: {', '.join(allowed_extensions)}"
            )

        if adjunto_file.size > max_file_size:
            raise ValidationError(
                f"Archivo {adjunto_file.name} ({adjunto_file.size / (1024 * 1024):.1f}MB) "
                f"excede el tamaño máximo de {max_file_size_mb}MB."
            )

        total_size += adjunto_file.size
        if total_size > max_total_size:
            raise ValidationError(
                f"El tamaño total de archivos ({total_size / (1024 * 1024):.1f}MB) "
                f"excede el límite de {max_total_size_mb}MB."
            )
