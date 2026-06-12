# Script de configuración para SQL Server Express
# Ejecutar como Administrador

Write-Host "=== Configuración de SQL Server Express ===" -ForegroundColor Green

# 1. Verificar e iniciar servicio SQL Server
Write-Host "1. Verificando servicios de SQL Server..." -ForegroundColor Yellow
$services = Get-Service | Where-Object {$_.DisplayName -like "*SQL*"}
if ($services) {
    $services | ForEach-Object {
        Write-Host "Servicio encontrado: $($_.DisplayName) - Estado: $($_.Status)"
    }
} else {
    Write-Host "No se encontraron servicios de SQL Server"
}

# 2. Iniciar servicio SQL Server Express
Write-Host "2. Iniciando servicio SQL Server Express..." -ForegroundColor Yellow
try {
    Start-Service -Name "MSSQL$SQLEXPRESS" -ErrorAction Stop
    Write-Host "Servicio iniciado correctamente" -ForegroundColor Green
} catch {
    Write-Host "Error al iniciar servicio: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host "Intentando con nombre alternativo..." -ForegroundColor Yellow
    try {
        Start-Service -Name "SQL Server (SQLEXPRESS)" -ErrorAction Stop
        Write-Host "Servicio iniciado correctamente con nombre alternativo" -ForegroundColor Green
    } catch {
        Write-Host "Error: $($_.Exception.Message)" -ForegroundColor Red
        exit 1
    }
}

# 3. Verificar que el servicio esté corriendo
$service = Get-Service -Name "MSSQL$SQLEXPRESS" -ErrorAction SilentlyContinue
if (-not $service) {
    $service = Get-Service -Name "SQL Server (SQLEXPRESS)" -ErrorAction SilentlyContinue
}

if ($service -and $service.Status -eq "Running") {
    Write-Host "Servicio SQL Server está corriendo correctamente" -ForegroundColor Green
} else {
    Write-Host "Error: El servicio SQL Server no está corriendo" -ForegroundColor Red
    exit 1
}

# 4. Habilitar autenticación mixta y configurar usuario sa
Write-Host "3. Configurando autenticación mixta y usuario sa..." -ForegroundColor Yellow

# Crear script SQL para configurar autenticación mixta
$sqlScript = @"
-- Habilitar autenticación mixta
EXEC xp_instance_regwrite N'HKEY_LOCAL_MACHINE', N'Software\Microsoft\MSSQLServer\MSSQLServer', N'LoginMode', REG_DWORD, 2

-- Reiniciar servicio para aplicar cambios
PRINT 'Autenticación mixta habilitada. Necesario reiniciar servicio.'
"@

# Guardar script temporalmente
$sqlScript | Out-File -FilePath "temp_config.sql" -Encoding ASCII

# Ejecutar configuración inicial
Write-Host "Ejecutando configuración inicial..." -ForegroundColor Cyan
try {
    Invoke-Sqlcmd -ServerInstance "TEROGAR\SQLEXPRESS" -InputFile "temp_config.sql" -ErrorAction Stop
    Write-Host "Configuración inicial aplicada" -ForegroundColor Green
} catch {
    Write-Host "Nota: Puede requerir reinicio manual del servicio" -ForegroundColor Yellow
}

# 5. Reiniciar servicio para aplicar cambios de autenticación
Write-Host "4. Reiniciando servicio para aplicar cambios..." -ForegroundColor Yellow
try {
    Restart-Service -Name "MSSQL$SQLEXPRESS" -Force -ErrorAction Stop
    Write-Host "Servicio reiniciado correctamente" -ForegroundColor Green
} catch {
    Write-Host "Error al reiniciar servicio: $($_.Exception.Message)" -ForegroundColor Red
}

# 6. Crear usuario sa con contraseña
Write-Host "5. Creando usuario administrador 'sa'..." -ForegroundColor Yellow
$saPassword = "TuPassword123"  # Cambia esto por una contraseña segura

$sqlCreateSA = @"
-- Crear login sa si no existe
IF NOT EXISTS (SELECT * FROM sys.server_principals WHERE name = 'sa')
BEGIN
    CREATE LOGIN [sa] WITH PASSWORD = '$saPassword', DEFAULT_DATABASE=[master], CHECK_EXPIRATION=OFF, CHECK_POLICY=OFF
END

-- Habilitar usuario sa
ALTER LOGIN [sa] ENABLE

-- Agregar sa al rol sysadmin
EXEC master..sp_addsrvrolemember @loginame = N'sa', @rolename = N'sysadmin'

PRINT 'Usuario sa creado y configurado correctamente'
"@

$sqlCreateSA | Out-File -FilePath "create_sa.sql" -Encoding ASCII

try {
    Invoke-Sqlcmd -ServerInstance "TEROGAR\SQLEXPRESS" -InputFile "create_sa.sql" -ErrorAction Stop
    Write-Host "Usuario sa creado correctamente" -ForegroundColor Green
} catch {
    Write-Host "Error creando usuario sa: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host "Intente manualmente usando SQL Server Management Studio" -ForegroundColor Yellow
}

# 7. Crear base de datos de prueba
Write-Host "6. Creando base de datos de prueba..." -ForegroundColor Yellow
$sqlCreateDB = @"
CREATE DATABASE HospitalDB
GO
USE HospitalDB
GO
CREATE TABLE PruebaConexion (
    ID int PRIMARY KEY IDENTITY(1,1),
    Nombre varchar(100),
    FechaCreacion datetime DEFAULT GETDATE()
)
GO
INSERT INTO PruebaConexion (Nombre) VALUES ('Conexión exitosa desde PowerShell')
GO
PRINT 'Base de datos HospitalDB creada correctamente'
"@

$sqlCreateDB | Out-File -FilePath "create_db.sql" -Encoding ASCII

try {
    Invoke-Sqlcmd -ServerInstance "TEROGAR\SQLEXPRESS" -InputFile "create_db.sql" -ErrorAction Stop
    Write-Host "Base de datos de prueba creada correctamente" -ForegroundColor Green
} catch {
    Write-Host "Error creando base de datos: $($_.Exception.Message)" -ForegroundColor Red
}

# 8. Probar conexión con autenticación SQL Server
Write-Host "7. Probando conexión con autenticación SQL Server..." -ForegroundColor Yellow
try {
    Invoke-Sqlcmd -ServerInstance "TEROGAR\SQLEXPRESS" -Username "sa" -Password $saPassword -Query "SELECT @@VERSION" -ErrorAction Stop
    Write-Host "Conexión con autenticación SQL Server exitosa" -ForegroundColor Green
} catch {
    Write-Host "Error en conexión SQL: $($_.Exception.Message)" -ForegroundColor Red
}

# 9. Limpiar archivos temporales
Write-Host "8. Limpiando archivos temporales..." -ForegroundColor Yellow
Remove-Item "temp_config.sql" -ErrorAction SilentlyContinue
Remove-Item "create_sa.sql" -ErrorAction SilentlyContinue
Remove-Item "create_db.sql" -ErrorAction SilentlyContinue

Write-Host ""
Write-Host "=== Configuración completada ===" -ForegroundColor Green
Write-Host ""
Write-Host "Información de conexión:" -ForegroundColor Cyan
Write-Host "Servidor: TEROGAR\SQLEXPRESS"
Write-Host "Usuario: sa"
Write-Host "Contraseña: $saPassword"
Write-Host "Base de datos creada: HospitalDB"
Write-Host ""
Write-Host "Ahora puedes:" -ForegroundColor White
Write-Host "1. Abrir SQL Server Management Studio"
Write-Host "2. Conectar usando autenticación SQL Server"
Write-Host "3. Usar usuario: sa y contraseña: $saPassword"
Write-Host "4. Crear y gestionar tus bases de datos"
