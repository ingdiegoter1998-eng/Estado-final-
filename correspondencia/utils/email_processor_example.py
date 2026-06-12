"""
Ejemplo de uso del validador de adjuntos en procesamiento de emails
"""
from django.core.exceptions import ValidationError
from correspondencia.utils.email_attachment_validator import EmailAttachmentValidator
import logging

logger = logging.getLogger(__name__)


def procesar_email_con_adjuntos(email_data, verbose=False):
    """
    Procesa un email validando sus adjuntos de forma segura
    
    Args:
        email_data: Dict con estructura:
            {
                'from': 'sender@example.com',
                'subject': 'Email subject',
                'body': 'Email body',
                'attachments': [
                    {'filename': 'documento.pdf', 'size': 5242880},  # 5MB
                    {'filename': 'imagen.jpg', 'size': 2097152},     # 2MB
                ]
            }
        verbose: Si es True, imprime detalles del procesamiento
    
    Returns:
        dict con resultado del procesamiento
        
    Raises:
        ValidationError: Si hay problemas con los adjuntos
    """
    
    attachments_data = email_data.get('attachments', [])
    
    if not attachments_data:
        if verbose:
            print('✓ Email sin adjuntos - procesando normalmente')
        return {
            'success': True,
            'message': 'Email procesado exitosamente sin adjuntos',
            'attachments_validated': 0,
            'total_size_mb': 0
        }
    
    try:
        # Convertir a formato esperado por el validador
        attachments = [
            (att['filename'], att['size'])
            for att in attachments_data
        ]
        
        if verbose:
            print(f'📧 Validando {len(attachments)} adjunto(s)...')
        
        # Validar TODOS los adjuntos
        validation_result = EmailAttachmentValidator.validate_email_attachments(
            attachments
        )
        
        if verbose:
            print(f'✓ {validation_result["total_files"]} archivo(s) validado(s)')
            print(f'✓ Tamaño total: {validation_result["total_size_mb"]:.2f} MB')
            for file_info in validation_result['files']:
                print(f'  - {file_info["filename"]}: {file_info["size_mb"]:.2f} MB')
        
        # Aquí iría la lógica de guardar el email y sus adjuntos
        logger.info(
            f'Email procesado: {email_data.get("from")} - '
            f'{validation_result["total_files"]} adjunto(s), '
            f'{validation_result["total_size_mb"]:.2f} MB'
        )
        
        return {
            'success': True,
            'message': f'Email procesado con {validation_result["total_files"]} adjunto(s)',
            'attachments_validated': validation_result["total_files"],
            'total_size_mb': validation_result["total_size_mb"],
            'files': validation_result['files']
        }
    
    except ValidationError as e:
        error_msg = str(e.message) if hasattr(e, 'message') else str(e)
        
        if verbose:
            print(f'❌ Error: {error_msg}')
        
        logger.warning(
            f'Email rechazado: {email_data.get("from")} - '
            f'Razón: {error_msg}'
        )
        
        return {
            'success': False,
            'message': error_msg,
            'error': error_msg,
            'attachments_validated': 0,
            'total_size_mb': 0
        }


# ============ EJEMPLOS DE USO ============

if __name__ == '__main__':
    # Ejemplo 1: Email con adjuntos válidos
    print('EJEMPLO 1: Email con adjuntos válidos')
    print('-' * 50)
    
    email_valido = {
        'from': 'usuario@hospital.com',
        'subject': 'Documentación importante',
        'body': 'Adjunto la documentación solicitada',
        'attachments': [
            {'filename': 'reporte.pdf', 'size': 5 * 1024 * 1024},      # 5 MB
            {'filename': 'datos.xlsx', 'size': 3 * 1024 * 1024},       # 3 MB
            {'filename': 'imagen.jpg', 'size': 2 * 1024 * 1024},       # 2 MB
        ]
    }
    
    resultado = procesar_email_con_adjuntos(email_valido, verbose=True)
    print(f'Resultado: {resultado["message"]}\n')
    
    # Ejemplo 2: Archivo demasiado grande
    print('\nEJEMPLO 2: Archivo que excede 10 MB')
    print('-' * 50)
    
    email_archivo_grande = {
        'from': 'usuario@hospital.com',
        'subject': 'Archivo grande',
        'body': 'Adjunto video',
        'attachments': [
            {'filename': 'video.mp4', 'size': 15 * 1024 * 1024},  # 15 MB (rechazado)
        ]
    }
    
    resultado = procesar_email_con_adjuntos(email_archivo_grande, verbose=True)
    print(f'Resultado: {resultado["message"]}\n')
    
    # Ejemplo 3: Extensión bloqueada
    print('\nEJEMPLO 3: Archivo con extensión bloqueada')
    print('-' * 50)
    
    email_ejecutable = {
        'from': 'usuario@hospital.com',
        'subject': 'Software',
        'body': 'Adjunto programa',
        'attachments': [
            {'filename': 'programa.exe', 'size': 2 * 1024 * 1024},  # Bloqueado
        ]
    }
    
    resultado = procesar_email_con_adjuntos(email_ejecutable, verbose=True)
    print(f'Resultado: {resultado["message"]}\n')
    
    # Ejemplo 4: Total de email excede 20 MB
    print('\nEJEMPLO 4: Email excede 20 MB total')
    print('-' * 50)
    
    email_demasiado_pesado = {
        'from': 'usuario@hospital.com',
        'subject': 'Muchos documentos',
        'body': 'Adjuntos varios',
        'attachments': [
            {'filename': 'archivo1.pdf', 'size': 9 * 1024 * 1024},
            {'filename': 'archivo2.pdf', 'size': 9 * 1024 * 1024},
            {'filename': 'archivo3.pdf', 'size': 5 * 1024 * 1024},  # Total = 23 MB
        ]
    }
    
    resultado = procesar_email_con_adjuntos(email_demasiado_pesado, verbose=True)
    print(f'Resultado: {resultado["message"]}\n')
