"""Utilidades para el cálculo de plazos legales basados en días hábiles.

Todas las funciones son lo suficientemente independientes para reutilizarse en otros contextos.
"""

import datetime
from functools import lru_cache
from typing import Optional

from django.conf import settings
from django.utils import timezone

from .modelos_minimos_sla import CalendarioLaboral

# Zona horaria por defecto para la aplicación.
TZ = timezone.pytz.timezone("America/Bogota") if hasattr(timezone, "pytz") else timezone.get_default_timezone()


@lru_cache(maxsize=1)
def get_cutoff_time() -> datetime.time:
    """Hora de corte configurada en *settings.SLA_CUTOFF_HOUR*.

    Si no existe la configuración, retorna las 18:00.
    Se cachea porque no suele cambiar en tiempo de ejecución.
    """
    return getattr(settings, "SLA_CUTOFF_HOUR", datetime.time(18, 0))


@lru_cache(maxsize=1)
def include_saturday() -> bool:
    """Indica si el sábado se considera día hábil.

    Lee *settings.SLA_INCLUDE_SATURDAY*; por defecto `False`.
    """
    return getattr(settings, "SLA_INCLUDE_SATURDAY", False)


def _es_habil(fecha: datetime.date) -> bool:
    """Determina si la fecha es hábil.

    1. Busca en la tabla *CalendarioLaboral*.
    2. Si no hay registro, considera hábil toda fecha de lunes a viernes.
       Si es sábado, depende de *include_saturday()*; domingo siempre es inhábil.
    """
    try:
        registro = CalendarioLaboral.objects.get(fecha=fecha)
        return registro.es_habil
    except CalendarioLaboral.DoesNotExist:
        # Fallback por día de la semana
        weekday = fecha.weekday()  # 0 = lunes
        if weekday < 5:
            return True
        if weekday == 5:
            return include_saturday()
        return False  # Domingo


def _siguiente_habil(fecha: datetime.date) -> datetime.date:
    """Devuelve la próxima fecha hábil a partir de *fecha* (que podría ser la misma)."""
    current = fecha
    while not _es_habil(current):
        current += datetime.timedelta(days=1)
    return current


def aplicar_corte(fecha_dt: datetime.datetime) -> datetime.datetime:
    """Aplica la lógica de corte horario.

    Si la hora **local** de *fecha_dt* es mayor (>) o igual al *cutoff*
    configurado, el inicio del conteo se traslada al siguiente día hábil
    conservando la hora original.  También asegura que la fecha resultante
    sea hábil.

    **Nota:** la comparación se realiza en hora local (``settings.TIME_ZONE``)
    para que el corte represente siempre las 6 p.m. Colombia, sin importar
    si el datetime entrante está en UTC o en otra TZ.
    """
    cutoff = get_cutoff_time()

    # Convertir a hora local para la comparación con el cutoff.
    if timezone.is_aware(fecha_dt):
        local_dt = timezone.localtime(fecha_dt)
    else:
        local_dt = fecha_dt

    nueva_dt = fecha_dt
    if local_dt.time() >= cutoff:
        nueva_dt = fecha_dt + datetime.timedelta(days=1)

    # Ajustar hasta encontrar un día hábil (usando fecha local)
    def _local_date(dt):
        return timezone.localtime(dt).date() if timezone.is_aware(dt) else dt.date()

    while not _es_habil(_local_date(nueva_dt)):
        nueva_dt += datetime.timedelta(days=1)

    return nueva_dt


def sumar_habiles(inicio_dt: datetime.datetime, dias: int) -> datetime.datetime:
    """Suma *dias* días hábiles a *inicio_dt* preservando la hora.

    Usa la fecha **local** para determinar si un día es hábil, de modo que
    un datetime en UTC cercano a medianoche se evalúa correctamente en la
    zona horaria configurada.
    """
    if dias <= 0:
        return inicio_dt

    def _local_date(dt):
        return timezone.localtime(dt).date() if timezone.is_aware(dt) else dt.date()

    current_dt = inicio_dt
    contados = 0
    while contados < dias:
        current_dt += datetime.timedelta(days=1)
        if _es_habil(_local_date(current_dt)):
            contados += 1
    return current_dt


# =============================================================================
# FUNCIONES PARA CÁLCULO DE HORAS LABORALES (URGENCIAS)
# =============================================================================

def calcular_horas_laborales(fecha_inicio: datetime.datetime, fecha_fin: datetime.datetime) -> float:
    """
    Calcula horas laborales entre dos fechas (8am-5pm, Lun-Vie).
    Excluye fines de semana y festivos de CalendarioLaboral.
    
    Args:
        fecha_inicio: datetime de inicio
        fecha_fin: datetime de fin
    
    Returns:
        float: Horas laborales transcurridas
    """
    HORA_INICIO = 8  # 8 AM
    HORA_FIN = 17    # 5 PM
    HORAS_DIA = 9    # 9 horas laborales por día
    
    if fecha_fin <= fecha_inicio:
        return 0.0
    
    horas_totales = 0.0
    fecha_actual = fecha_inicio.replace(second=0, microsecond=0)
    
    while fecha_actual < fecha_fin:
        dia_actual = fecha_actual.date()
        
        # Verificar si es día hábil
        if not _es_habil(dia_actual):
            # Saltar al siguiente día
            fecha_actual = (fecha_actual + datetime.timedelta(days=1)).replace(
                hour=HORA_INICIO, minute=0
            )
            continue
        
        # Determinar hora de inicio del día
        if fecha_actual.date() == fecha_inicio.date():
            hora_inicio_dia = max(fecha_actual.hour + fecha_actual.minute / 60.0, HORA_INICIO)
        else:
            hora_inicio_dia = HORA_INICIO
        
        # Determinar hora de fin del día
        if fecha_actual.date() == fecha_fin.date():
            hora_fin_dia = min(fecha_fin.hour + fecha_fin.minute / 60.0, HORA_FIN)
        else:
            hora_fin_dia = HORA_FIN
        
        # Calcular horas del día
        if hora_inicio_dia < hora_fin_dia:
            horas_dia = hora_fin_dia - hora_inicio_dia
            horas_totales += horas_dia
        
        # Avanzar al siguiente día
        fecha_actual = (fecha_actual + datetime.timedelta(days=1)).replace(
            hour=HORA_INICIO, minute=0
        )
    
    return round(horas_totales, 2)


def sumar_horas_laborales(fecha_inicio: datetime.datetime, horas: float) -> datetime.datetime:
    """
    Suma horas laborales a una fecha, saltando fines de semana y festivos.
    
    Args:
        fecha_inicio: datetime de inicio
        horas: float de horas laborales a sumar
    
    Returns:
        datetime: Fecha límite resultante
    """
    HORA_INICIO = 8
    HORA_FIN = 17
    HORAS_DIA = 9
    
    fecha_actual = fecha_inicio.replace(second=0, microsecond=0)
    horas_restantes = float(horas)
    
    # Ajustar al siguiente momento laboral si estamos fuera de horario
    if fecha_actual.hour < HORA_INICIO:
        fecha_actual = fecha_actual.replace(hour=HORA_INICIO, minute=0)
    elif fecha_actual.hour >= HORA_FIN:
        fecha_actual = (fecha_actual + datetime.timedelta(days=1)).replace(
            hour=HORA_INICIO, minute=0
        )
    
    # Iterar hasta consumir todas las horas
    while horas_restantes > 0:
        dia_actual = fecha_actual.date()
        
        # Saltar si no es hábil
        if not _es_habil(dia_actual):
            fecha_actual = (fecha_actual + datetime.timedelta(days=1)).replace(
                hour=HORA_INICIO, minute=0
            )
            continue
        
        # Horas disponibles en el día actual
        horas_disponibles = HORA_FIN - fecha_actual.hour - fecha_actual.minute / 60.0
        
        if horas_restantes <= horas_disponibles:
            # Cabe en el día actual
            horas_enteras = int(horas_restantes)
            minutos = int((horas_restantes - horas_enteras) * 60)
            fecha_actual += datetime.timedelta(hours=horas_enteras, minutes=minutos)
            horas_restantes = 0
        else:
            # No cabe, pasar al siguiente día
            horas_restantes -= horas_disponibles
            fecha_actual = (fecha_actual + datetime.timedelta(days=1)).replace(
                hour=HORA_INICIO, minute=0
            )
    
    return fecha_actual
