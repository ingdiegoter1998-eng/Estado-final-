#!/usr/bin/env python
"""
Script para mostrar ejemplos de correspondencias físicas.

Uso:
    python ejemplos_correspondencias.py
"""

import os
import sqlite3

def mostrar_ejemplos():
    """Muestra ejemplos de correspondencias físicas."""
    print("EJEMPLOS DE CORRESPONDENCIAS FISICAS")
    print("=" * 50)

    db_path = 'db.sqlite3'
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    print("Algunos ejemplos de correspondencias físicas:")
    cursor.execute("""
        SELECT numero_radicado, asunto, fecha_radicacion,
               u.first_name || ' ' || u.last_name as usuario,
               o.nombre as oficina, c.nombres || ' ' || c.apellidos as contacto,
               e.nombre as entidad
        FROM correspondencia_correspondencia cor
        JOIN auth_user u ON cor.usuario_radicador_id = u.id
        JOIN documentos_oficinaproductora o ON cor.oficina_destino_id = o.id
        JOIN correspondencia_contacto c ON cor.remitente_id = c.id
        JOIN correspondencia_entidadexterna e ON c.entidad_externa_id = e.id
        WHERE numero_radicado LIKE 'FISICO-2025-%'
        ORDER BY fecha_radicacion DESC
        LIMIT 10;
    """)
    ejemplos = cursor.fetchall()

    for i, (numero, asunto, fecha, usuario, oficina, contacto, entidad) in enumerate(ejemplos, 1):
        print(f"\n{i}. {numero}")
        print(f"   Asunto: {asunto}")
        print(f"   Usuario: {usuario}")
        print(f"   Oficina: {oficina}")
        print(f"   Contacto: {contacto} ({entidad})")
        print(f"   Fecha: {fecha}")

    print(f"\nTotal de correspondencias físicas: {len(ejemplos)} mostradas de 800 totales")
    conn.close()

if __name__ == '__main__':
    mostrar_ejemplos()
