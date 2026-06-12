"""
Validador de seguridad para adjuntos de email
"""
import os
from django.core.exceptions import ValidationError
from correspondencia.settings.email_config import (
    ALLOWED_FILE_EXTENSIONS,
    BLOCKED_FILE_EXTENSIONS,
    MAX_FILE_SIZE_MB,
    MAX_TOTAL_SIZE_MB,
    MAX_FILES_PER_EMAIL,
)


class EmailAttachmentValidator:
    """
    Validador de seguridad para adjuntos de email
    Controla:
    - Tipos de archivo permitidos/bloqueados
    - Tamaño máximo por archivo (20MB)
    - Tamaño máximo total por email (40MB)
    - Cantidad máxima de archivos (20)
    """
    
    @staticmethod
    def get_file_extension(filename):
        """Extrae la extensión del archivo en minúsculas"""
        return os.path.splitext(filename)[1].lstrip('.').lower()
    
    @staticmethod
    def validate_extension(filename):
        """Valida que la extensión esté permitida"""
        ext = EmailAttachmentValidator.get_file_extension(filename)
        
        if not ext:
            raise ValidationError(
                f"El archivo '{filename}' no tiene extensión válida"
            )
        
        if ext in BLOCKED_FILE_EXTENSIONS:
            raise ValidationError(
                f"El tipo de archivo '.{ext}' está bloqueado por seguridad"
            )
        
        if ext not in ALLOWED_FILE_EXTENSIONS:
            allowed = ', '.join(sorted(ALLOWED_FILE_EXTENSIONS))
            raise ValidationError(
                f"El tipo de archivo '.{ext}' no está permitido. "
                f"Tipos permitidos: {allowed}"
            )
    
    @staticmethod
    def validate_file_size(file_size_bytes, filename):
        """Valida el tamaño individual del archivo"""
        max_size_bytes = MAX_FILE_SIZE_MB * 1024 * 1024
        
        if file_size_bytes > max_size_bytes:
            file_size_mb = file_size_bytes / (1024 * 1024)
            raise ValidationError(
                f"El archivo '{filename}' ({file_size_mb:.1f} MB) excede "
                f"el tamaño máximo de {MAX_FILE_SIZE_MB} MB"
            )
    
    @staticmethod
    def validate_attachment(filename, file_size_bytes):
        """
        Validación completa de un adjunto
        
        Args:
            filename: Nombre del archivo
            file_size_bytes: Tamaño en bytes
            
        Raises:
            ValidationError: Si hay algún problema de seguridad
        """
        EmailAttachmentValidator.validate_extension(filename)
        EmailAttachmentValidator.validate_file_size(file_size_bytes, filename)
    
    @staticmethod
    def validate_email_attachments(attachments):
        """
        Valida todos los adjuntos de un email
        
        Args:
            attachments: Lista de tuplas (filename, file_size)
            
        Returns:
            dict con resumen de validación
            
        Raises:
            ValidationError: Si hay problemas con los adjuntos
        """
        if len(attachments) > MAX_FILES_PER_EMAIL:
            raise ValidationError(
                f"El email contiene {len(attachments)} archivos. "
                f"Máximo permitido: {MAX_FILES_PER_EMAIL}"
            )
        
        total_size = 0
        max_total_bytes = MAX_TOTAL_SIZE_MB * 1024 * 1024
        valid_files = []
        
        for filename, file_size in attachments:
            # Validar cada archivo
            EmailAttachmentValidator.validate_attachment(filename, file_size)
            total_size += file_size
            
            if total_size > max_total_bytes:
                total_size_mb = total_size / (1024 * 1024)
                raise ValidationError(
                    f"El tamaño total de los archivos ({total_size_mb:.1f} MB) excede "
                    f"el máximo permitido ({MAX_TOTAL_SIZE_MB} MB)"
                )
            
            valid_files.append({
                'filename': filename,
                'size_mb': file_size / (1024 * 1024)
            })
        
        return {
            'valid': True,
            'total_files': len(valid_files),
            'total_size_mb': total_size / (1024 * 1024),
            'files': valid_files
        }
    
    @staticmethod
    def get_config_summary():
        """Retorna un resumen de la configuración de seguridad"""
        return {
            'max_file_size_mb': MAX_FILE_SIZE_MB,
            'max_total_size_mb': MAX_TOTAL_SIZE_MB,
            'max_files_per_email': MAX_FILES_PER_EMAIL,
            'allowed_extensions': sorted(ALLOWED_FILE_EXTENSIONS),
            'blocked_extensions': sorted(BLOCKED_FILE_EXTENSIONS),
        }
