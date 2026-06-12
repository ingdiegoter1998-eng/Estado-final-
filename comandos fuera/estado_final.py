#!/usr/bin/env python
"""
Estado final de la base de datos poblada.

Muestra el estado completo del sistema después del poblado masivo.
"""

import os
import sqlite3

def mostrar_estado_final():
    """Muestra el estado final completo."""
    print("ESTADO FINAL - BASE DE DATOS POBLADA")
    print("=" * 60)

    db_path = 'db.sqlite3'
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Datos generales
    cursor.execute('SELECT COUNT(*) FROM auth_user WHERE is_superuser = 0;')
    usuarios = cursor.fetchone()[0]

    cursor.execute('SELECT COUNT(*) FROM correspondencia_correspondencia WHERE numero_radicado LIKE "FISICO-2025-%";')
    correspondencias = cursor.fetchone()[0]

    cursor.execute('SELECT COUNT(*) FROM correspondencia_contacto;')
    contactos = cursor.fetchone()[0]

    print("
📊 RESUMEN GENERAL:"    print(f"   👥 Usuarios: {usuarios}")
    print(f"   📄 Correspondencias físicas: {correspondencias}")
    print(f"   👨‍💼 Contactos: {contactos}")

    # Usuarios por grupo
    print("
👥 USUARIOS POR GRUPO:"    cursor.execute("""
        SELECT g.name, COUNT(*) as cantidad
        FROM auth_user u
        JOIN auth_user_groups ug ON u.id = ug.user_id
        JOIN auth_group g ON ug.group_id = g.id
        WHERE u.is_superuser = 0
        GROUP BY g.name;
    """)
    for grupo, cantidad in cursor.fetchall():
        print(f"   {grupo}: {cantidad} usuarios")

    # Correspondencias por oficina
    print("
📄 CORRESPONDENCIAS POR OFICINA:"    cursor.execute("""
        SELECT o.nombre, COUNT(*) as cantidad
        FROM correspondencia_correspondencia c
        JOIN documentos_oficinaproductora o ON c.oficina_destino_id = o.id
        WHERE numero_radicado LIKE 'FISICO-2025-%'
        GROUP BY o.nombre
        ORDER BY cantidad DESC;
    """)
    for oficina, cantidad in cursor.fetchall():
        print(f"   {oficina}: {cantidad}")

    # Estados de correspondencia
    print("
📋 ESTADO DE CORRESPONDENCIAS:"    cursor.execute("""
        SELECT estado, COUNT(*) as cantidad
        FROM correspondencia_correspondencia
        WHERE numero_radicado LIKE 'FISICO-2025-%'
        GROUP BY estado;
    """)
    for estado, cantidad in cursor.fetchall():
        print(f"   {estado}: {cantidad}")

    # Usuarios más activos
    print("
🏆 USUARIOS MAS ACTIVOS:"    cursor.execute("""
        SELECT u.first_name || ' ' || u.last_name, COUNT(*) as cantidad
        FROM correspondencia_correspondencia c
        JOIN auth_user u ON c.usuario_radicador_id = u.id
        WHERE numero_radicado LIKE 'FISICO-2025-%'
        GROUP BY u.id, u.first_name, u.last_name
        ORDER BY cantidad DESC
        LIMIT 5;
    """)
    for usuario, cantidad in cursor.fetchall():
        print(f"   {usuario}: {cantidad} correspondencias")

    print("
🔐 ACCESO AL SISTEMA:"    print("   Superusuario: admin / admin123"    print(f"   Usuarios regulares: {usuarios} usuarios disponibles")
    print("   Formato: [nombre.apellido] / password123"
    print("
🎯 SISTEMA LISTO!"    print(f"   {usuarios} usuarios para pruebas de carga")
    print(f"   {correspondencias} correspondencias físicas")
    print("   Datos distribuidos y listos para usar"
    print("=" * 60)

    conn.close()

if __name__ == '__main__':
    mostrar_estado_final()
