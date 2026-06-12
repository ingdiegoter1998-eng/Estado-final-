"""
Configuración centralizada para procesamiento seguro de emails y adjuntos
"""

# Extensiones de archivo PERMITIDAS (whitelist)
ALLOWED_FILE_EXTENSIONS = {
    # Documentos
    'pdf', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx',
    'txt', 'rtf', 'odt', 'ods', 'odp',
    # Imágenes
    'jpg', 'jpeg', 'png', 'gif', 'bmp', 'webp',
    # Comprimidos (controlados)
    'zip', 'rar', '7z',
}

# Extensiones BLOQUEADAS explícitamente (blacklist)
BLOCKED_FILE_EXTENSIONS = {
    # Ejecutables
    'exe', 'bat', 'cmd', 'com', 'pif', 'scr',
    # Scripts
    'js', 'vbs', 'vbe', 'jse', 'wsf', 'wsh', 'msi', 'ps1', 'py', 'sh', 'bash',
    # Macros peligrosos
    'docm', 'xlsm', 'pptm',
    # Otros peligrosos
    'app', 'dmg', 'deb', 'rpm', 'apk', 'jar', 'dll', 'so', 'dylib',
}

# Límites de tamaño
MAX_FILE_SIZE_MB = 20  # Máximo por archivo
MAX_TOTAL_SIZE_MB = 40  # Máximo total por email
MAX_FILES_PER_EMAIL = 20  # Máximo de archivos por email

# Directorio de almacenamiento
ATTACHMENT_STORAGE_PATH = 'email_attachments/'

# Configuración de escaneo
SCAN_FOR_VIRUSES = False  # Usar ClamAV si está disponible (desactivado por defecto)
DELETE_SUSPICIOUS_FILES = True  # Eliminar automáticamente archivos sospechosos
