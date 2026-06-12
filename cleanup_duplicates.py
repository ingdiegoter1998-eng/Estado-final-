#!/usr/bin/env python3
"""
Script para eliminar funciones duplicadas en views.py
Mantiene solo la última definición de cada función
"""
import re
from pathlib import Path

def find_function_definitions(filepath):
    """Encuentra todas las definiciones de funciones con sus decoradores"""
    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    functions = {}  # {func_name: [(start_line, end_line, decorator_lines), ...]}
    i = 0
    
    while i < len(lines):
        line = lines[i]
        
        # Buscar decoradores (@login_required, @require_http_methods, etc.)
        decorator_start = i
        decorators = []
        while i < len(lines) and lines[i].strip().startswith('@'):
            decorators.append(i)
            i += 1
        
        # Buscar def
        if i < len(lines) and lines[i].strip().startswith('def '):
            match = re.match(r'\s*def\s+(\w+)\s*\(', lines[i])
            if match:
                func_name = match.group(1)
                func_def_line = i
                i += 1
                
                # Encontrar el final de la función (siguiente def o decorator en mismo nivel de indentación)
                func_end = i
                indent_level = len(lines[func_def_line]) - len(lines[func_def_line].lstrip())
                
                while func_end < len(lines):
                    current_line = lines[func_end]
                    
                    # Si está vacía o es solo whitespace, continuar
                    if current_line.strip() == '':
                        func_end += 1
                        continue
                    
                    # Calcular indentación actual
                    current_indent = len(current_line) - len(current_line.lstrip())
                    
                    # Si encuentra un decorador o def en el mismo nivel, termina la función
                    if (current_indent <= indent_level and 
                        (current_line.strip().startswith('@') or current_line.strip().startswith('def '))):
                        break
                    
                    func_end += 1
                
                # Registrar
                if func_name not in functions:
                    functions[func_name] = []
                
                decorator_line_nums = decorators if decorators else [func_def_line]
                functions[func_name].append({
                    'start': min(decorator_line_nums) if decorator_line_nums else func_def_line,
                    'end': func_end,
                    'def_line': func_def_line
                })
        
        i += 1
    
    return functions, lines

def main():
    filepath = Path('/home/devdiego/Correspondencia-diciembre-1.0/correspondencia/views.py')
    
    functions, lines = find_function_definitions(str(filepath))
    
    # Encontrar duplicadas
    duplicates = {name: defs for name, defs in functions.items() if len(defs) > 1}
    
    print(f"✓ Total de funciones únicas: {len(functions)}")
    print(f"✓ Funciones duplicadas: {len(duplicates)}\n")
    
    # Recolectar líneas a eliminar (todas excepto la última de cada duplicada)
    lines_to_delete = []
    
    for func_name, defs in sorted(duplicates.items()):
        print(f"  {func_name}: {len(defs)} definiciones")
        for idx, d in enumerate(defs):
            is_last = (idx == len(defs) - 1)
            status = "✓ MANTENER" if is_last else "✗ ELIMINAR"
            print(f"    - Líneas {d['start']+1}-{d['end']}: {status}")
            
            if not is_last:
                lines_to_delete.extend(range(d['start'], d['end']))
    
    lines_to_delete = sorted(set(lines_to_delete), reverse=True)  # Reverse para no afectar índices
    
    print(f"\n✓ Total de líneas a eliminar: {len(lines_to_delete)}")
    
    # Crear nuevo contenido
    new_lines = [line for i, line in enumerate(lines) if i not in lines_to_delete]
    
    # Backup
    backup_path = filepath.with_suffix('.py.backup')
    with open(backup_path, 'w', encoding='utf-8') as f:
        f.writelines(lines)
    print(f"✓ Backup creado: {backup_path}")
    
    # Guardar archivo limpio
    with open(filepath, 'w', encoding='utf-8') as f:
        f.writelines(new_lines)
    
    print(f"✓ Archivo limpio guardado: {filepath}")
    print(f"✓ Líneas originales: {len(lines)}")
    print(f"✓ Líneas finales: {len(new_lines)}")
    print(f"✓ Líneas eliminadas: {len(lines) - len(new_lines)}")

if __name__ == '__main__':
    main()
