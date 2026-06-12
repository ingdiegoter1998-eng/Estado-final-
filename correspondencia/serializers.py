from rest_framework import serializers
from .models import (
    InformeDiarioCorrespondencia,
    Correspondencia,
    FirmaCorrespondencia,
    FirmaAuxiliarCorrespondencia,
)


class InformeDiarioSerializer(serializers.ModelSerializer):
    tiene_archivo = serializers.SerializerMethodField()

    class Meta:
        model = InformeDiarioCorrespondencia
        fields = ['id', 'fecha', 'estado', 'total_correspondencias',
                  'archivo_firmado', 'tiene_archivo', 'fecha_subida_firma']

    def get_tiene_archivo(self, obj):
        return bool(obj.archivo_firmado)


class FirmaCorrespondenciaSerializer(serializers.ModelSerializer):
    class Meta:
        model = FirmaCorrespondencia
        fields = ['id', 'firma_imagen', 'fecha_firma', 'nombre_firmante',
                  'cargo_firmante', 'observaciones']


class FirmaAuxiliarCorrespondenciaSerializer(serializers.ModelSerializer):
    class Meta:
        model = FirmaAuxiliarCorrespondencia
        fields = ['id', 'firma_imagen', 'fecha_firma', 'nombre_firmante',
                  'cargo_firmante']


class CorrespondenciaListSerializer(serializers.ModelSerializer):
    remitente_nombre = serializers.SerializerMethodField()
    destinatario_nombre = serializers.SerializerMethodField()
    funcionario_responsable = serializers.SerializerMethodField()
    oficina_destino_nombre = serializers.SerializerMethodField()
    tiene_firma = serializers.SerializerMethodField()
    firma = FirmaCorrespondenciaSerializer(source='firma_recibida', read_only=True)
    firmas_auxiliares = FirmaAuxiliarCorrespondenciaSerializer(many=True, read_only=True)
    total_firmas_auxiliares = serializers.SerializerMethodField()
    cuerpo_correo = serializers.SerializerMethodField()
    medio_recepcion = serializers.CharField(read_only=True)
    clasificacion_comunicacion = serializers.CharField(read_only=True)
    numero_folios = serializers.IntegerField(read_only=True)
    estado = serializers.CharField(read_only=True)

    class Meta:
        model = Correspondencia
        fields = ['id', 'numero_radicado', 'fecha_radicacion', 'asunto',
                  'remitente_nombre', 'destinatario_nombre',
                  'funcionario_responsable', 'oficina_destino_nombre',
                  'requiere_respuesta', 'tiene_firma', 'firma',
                  'firmas_auxiliares', 'total_firmas_auxiliares',
                  'cuerpo_correo', 'medio_recepcion',
                  'clasificacion_comunicacion', 'numero_folios', 'estado']

    def get_remitente_nombre(self, obj):
        """Remitente: texto libre (radicación rápida) o contacto registrado."""
        if obj.entidad_persona_remitente:
            return obj.entidad_persona_remitente
        if obj.remitente:
            return obj.remitente.nombre_completo
        return "Sin remitente"

    def get_destinatario_nombre(self, obj):
        """Nombre del usuario asignado inicialmente (o la oficina como fallback)."""
        if obj.usuario_destino_inicial:
            return obj.usuario_destino_inicial.get_full_name() or obj.usuario_destino_inicial.username
        elif obj.oficina_destino:
            return obj.oficina_destino.nombre
        return "Sin asignar"

    def get_funcionario_responsable(self, obj):
        """Funcionario responsable del trámite (radicación rápida).
        Prioridad: funcionario_responsable_tramite → usuario_destino_inicial.
        """
        if obj.funcionario_responsable_tramite:
            return obj.funcionario_responsable_tramite
        if obj.usuario_destino_inicial:
            return obj.usuario_destino_inicial.get_full_name() or obj.usuario_destino_inicial.username
        return ""

    def get_oficina_destino_nombre(self, obj):
        """Nombre de la oficina de destino."""
        if obj.oficina_destino:
            return obj.oficina_destino.nombre
        return "Sin oficina"

    def get_tiene_firma(self, obj):
        """Verifica si tiene firma registrada"""
        return hasattr(obj, 'firma_recibida') and obj.firma_recibida is not None

    def get_total_firmas_auxiliares(self, obj):
        if hasattr(obj, '_prefetched_objects_cache') and 'firmas_auxiliares' in obj._prefetched_objects_cache:
            return len(obj._prefetched_objects_cache['firmas_auxiliares'])
        return obj.firmas_auxiliares.count()

    def get_cuerpo_correo(self, obj):
        """Obtiene el cuerpo del correo electrónico asociado (si existe)."""
        correo = obj.correo_origen.first() if hasattr(obj, 'correo_origen') else None
        if correo:
            return correo.cuerpo_texto or ''
        return ''
