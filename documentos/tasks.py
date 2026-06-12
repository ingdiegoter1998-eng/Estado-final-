"""
Tareas Celery para la app documentos.
"""
import os
import pandas as pd
from celery import shared_task
from django.contrib.auth.models import User


def _parse_date_safe(value):
    """Convierte un valor a fecha de forma segura."""
    if pd.isna(value):
        return None
    try:
        return pd.to_datetime(value).date()
    except Exception:
        return None


def _safe_int(value):
    """Convierte un valor a entero de forma segura."""
    try:
        return int(value)
    except (ValueError, TypeError):
        return None


@shared_task(bind=True)
def importar_excel_task(self, archivo_path, fuid_id, user_id):
    """
    Tarea Celery para importar registros desde un archivo Excel.
    Optimizada con:
    - Cacheo de series/subseries en memoria (evita N+1 queries)
    - bulk_create en lotes (menos INSERTs)
    - Asignación M2M en lote
    - Reporte de progreso en tiempo real
    """
    from documentos.models import (
        FUID, RegistroDeArchivo, SerieDocumental, SubserieDocumental
    )

    # ── Fase 1: Leer archivo Excel ──────────────────────────────────────────
    self.update_state(state='PROGRESS', meta={
        'current': 0, 'total': 0,
        'fase': 'Leyendo archivo Excel...',
        'exitos': 0, 'errores_count': 0,
    })

    try:
        df = pd.read_excel(archivo_path, engine='openpyxl')
    except Exception as e:
        return {
            'estado': 'error',
            'mensaje': f'Error al leer el archivo: {e}',
            'exitos': 0, 'errores': [],
        }
    finally:
        # Limpiar archivo temporal
        if os.path.exists(archivo_path):
            os.remove(archivo_path)

    total = len(df)
    if total == 0:
        return {
            'estado': 'completado',
            'exitos': 0, 'errores': ['El archivo está vacío.'], 'total': 0,
        }

    # ── Validar FUID y usuario ──────────────────────────────────────────────
    try:
        fuid = FUID.objects.get(id=fuid_id)
    except FUID.DoesNotExist:
        return {
            'estado': 'error',
            'mensaje': 'El FUID seleccionado no existe.',
            'exitos': 0, 'errores': [],
        }

    try:
        usuario = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return {
            'estado': 'error',
            'mensaje': 'El usuario no existe.',
            'exitos': 0, 'errores': [],
        }

    # ── Fase 2: Cachear Series y Subseries en memoria ──────────────────────
    self.update_state(state='PROGRESS', meta={
        'current': 0, 'total': total,
        'fase': 'Cargando catálogos...',
        'exitos': 0, 'errores_count': 0,
    })

    series_dict = {}
    for s in SerieDocumental.objects.all():
        series_dict[s.nombre.strip().lower()] = s

    subseries_dict = {}
    for s in SubserieDocumental.objects.all():
        subseries_dict[s.nombre.strip().lower()] = s

    # ── Fase 3: Validar filas y preparar registros ─────────────────────────
    errores = []
    registros_para_crear = []
    filas = df.to_dict('records')

    for i, row in enumerate(filas):
        fila_num = i + 2  # +2 porque Excel empieza en 1 y la fila 1 es encabezado

        # Actualizar progreso cada 50 filas
        if i % 50 == 0:
            self.update_state(state='PROGRESS', meta={
                'current': i, 'total': total,
                'fase': f'Validando fila {i + 1} de {total}...',
                'exitos': 0, 'errores_count': len(errores),
            })

        try:
            numero_orden = row.get("numero_orden")
            codigo_serie_val = row.get("codigo_serie")
            unidad_documental = row.get("unidad_documental")

            # Validar campos obligatorios
            if pd.isna(numero_orden) or pd.isna(codigo_serie_val) or pd.isna(unidad_documental):
                errores.append(
                    f"Fila {fila_num}: Faltan campos obligatorios: "
                    f"numero_orden, codigo_serie o unidad_documental."
                )
                continue

            # Buscar serie en caché
            serie_key = str(codigo_serie_val).strip().lower()
            serie = series_dict.get(serie_key)
            if not serie:
                errores.append(
                    f"Fila {fila_num}: Serie documental "
                    f"'{codigo_serie_val}' no encontrada."
                )
                continue

            # Buscar subserie en caché
            subserie = None
            codigo_subserie_val = row.get("codigo_subserie")
            if codigo_subserie_val is not None and not pd.isna(codigo_subserie_val):
                subserie_key = str(codigo_subserie_val).strip().lower()
                subserie = subseries_dict.get(subserie_key)
                if not subserie:
                    errores.append(
                        f"Fila {fila_num}: Subserie documental "
                        f"'{codigo_subserie_val}' no encontrada."
                    )
                    continue

            # Construir instancia (sin guardar)
            ident_doc = row.get("identificador_documento")
            if ident_doc is not None and not pd.isna(ident_doc):
                ident_doc = str(ident_doc).strip()
            else:
                ident_doc = None

            registro = RegistroDeArchivo(
                Estado_archivo=bool(row.get("estado_archivo", True)),
                numero_orden=_safe_int(row["numero_orden"]),
                codigo=row.get("codigo"),
                codigo_serie=serie,
                codigo_subserie=subserie,
                unidad_documental=unidad_documental,
                fecha_inicial=_parse_date_safe(row.get("fecha_inicial")),
                fecha_final=_parse_date_safe(row.get("fecha_final")),
                fecha_archivo=_parse_date_safe(row.get("fecha_archivo")),
                soporte_fisico=bool(row.get("soporte_fisico", False)),
                soporte_electronico=bool(row.get("soporte_electronico", False)),
                caja=_safe_int(row.get("caja")),
                carpeta=_safe_int(row.get("carpeta")),
                tomo_legajo_libro=row.get("tomo_legajo_libro"),
                numero_folios=_safe_int(row.get("numero_folios")),
                tipo=row.get("tipo"),
                cantidad=_safe_int(row.get("cantidad")),
                ubicacion=row.get("ubicacion"),
                cantidad_documentos_electronicos=_safe_int(
                    row.get("cantidad_documentos_electronicos")
                ),
                tamano_documentos_electronicos=row.get(
                    "tamano_documentos_electronicos"
                ),
                identificador_documento=ident_doc,
                notas=row.get("notas"),
                creado_por=usuario,
            )
            registros_para_crear.append(registro)

        except Exception as e:
            errores.append(f"Fila {fila_num}: {e}")

    # ── Fase 4: Guardar registros con bulk_create ──────────────────────────
    exitos = 0
    batch_size = 500
    total_a_crear = len(registros_para_crear)
    todos_los_ids = []

    for batch_start in range(0, total_a_crear, batch_size):
        batch = registros_para_crear[batch_start:batch_start + batch_size]
        batch_end = min(batch_start + len(batch), total_a_crear)

        self.update_state(state='PROGRESS', meta={
            'current': batch_end,
            'total': total,
            'fase': f'Guardando registros {batch_start + 1} a {batch_end} de {total_a_crear}...',
            'exitos': exitos, 'errores_count': len(errores),
        })

        try:
            # Anotar max ID antes del bulk_create (para recuperar IDs si el backend no los devuelve)
            from django.db.models import Max
            max_id_antes = RegistroDeArchivo.objects.aggregate(
                Max('id')
            )['id__max'] or 0

            creados = RegistroDeArchivo.objects.bulk_create(batch)
            exitos += len(creados)

            # Intentar obtener PKs de los objetos creados
            pks = [r.pk for r in creados if r.pk]
            if pks:
                todos_los_ids.extend(pks)
            else:
                # Fallback: recuperar por IDs mayores al max anterior
                nuevos_ids = list(
                    RegistroDeArchivo.objects.filter(
                        id__gt=max_id_antes
                    ).values_list('id', flat=True)
                )
                todos_los_ids.extend(nuevos_ids)

        except Exception as e:
            errores.append(
                f"Error al guardar lote "
                f"{batch_start // batch_size + 1}: {e}"
            )

    # ── Fase 5: Asociar todos los registros al FUID (M2M en lote) ─────────
    if todos_los_ids:
        self.update_state(state='PROGRESS', meta={
            'current': total, 'total': total,
            'fase': 'Asociando registros al FUID...',
            'exitos': exitos, 'errores_count': len(errores),
        })

        try:
            # Asignar M2M en una sola operación (o pocas si son muchos)
            fuid.registros.add(*todos_los_ids)
        except Exception as e:
            errores.append(f"Error al asociar registros al FUID: {e}")

    # ── Resultado final ────────────────────────────────────────────────────
    return {
        'estado': 'completado',
        'exitos': exitos,
        'errores': errores,
        'total': total,
    }
