from django.core.exceptions import ValidationError

from documentos.models import SerieDocumental, SubserieDocumental


SERIE_INTERNA_NOMBRE = 'COMUNICACIONES OFICIALES'
SERIE_INTERNA_CODIGO_TRD = '03'
SUBSERIE_INTERNA_NOMBRE = 'Comunicaciones Internas'
SUBSERIE_INTERNA_CODIGO_TRD = '30'


def queryset_series_comunicacion_interna():
    return SerieDocumental.objects.filter(
        nombre__iexact=SERIE_INTERNA_NOMBRE,
        codigo_trd=SERIE_INTERNA_CODIGO_TRD,
    ).order_by('nombre')


def queryset_subseries_comunicacion_interna():
    return SubserieDocumental.objects.filter(
        nombre__iexact=SUBSERIE_INTERNA_NOMBRE,
        codigo_trd=SUBSERIE_INTERNA_CODIGO_TRD,
        serie__nombre__iexact=SERIE_INTERNA_NOMBRE,
        serie__codigo_trd=SERIE_INTERNA_CODIGO_TRD,
    ).select_related('serie').order_by('nombre')


def obtener_clasificacion_comunicacion_interna():
    serie = queryset_series_comunicacion_interna().first()
    subserie = queryset_subseries_comunicacion_interna().first()

    if not serie or not subserie:
        raise ValidationError(
            'No está configurada la clasificación archivística fija para comunicaciones internas. '
            'Debe existir la serie COMUNICACIONES OFICIALES (03) y la subserie Comunicaciones Internas (30).'
        )

    return serie, subserie


def validar_clasificacion_comunicacion_interna(serie, subserie):
    serie_valida, subserie_valida = obtener_clasificacion_comunicacion_interna()

    if not serie or not subserie:
        raise ValidationError('Debe seleccionar la serie COMUNICACIONES OFICIALES y la subserie Comunicaciones Internas.')

    if serie.pk != serie_valida.pk or subserie.pk != subserie_valida.pk:
        raise ValidationError(
            'Para comunicaciones internas solo está permitida la serie COMUNICACIONES OFICIALES '
            'con la subserie Comunicaciones Internas.'
        )

    return serie_valida, subserie_valida