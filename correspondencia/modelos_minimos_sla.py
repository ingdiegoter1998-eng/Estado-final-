from django.db import models
from django.utils.translation import gettext_lazy as _

# Dependencia externa de la app 'documentos'. Se asume que existe y está en INSTALLED_APPS
from documentos.models import SubserieDocumental


class TramiteTipo(models.Model):
    """Catálogo de tipos de trámite asociado a plazos legales de respuesta."""

    codigo = models.CharField(max_length=50, unique=True)
    nombre = models.CharField(max_length=255)
    plazo_dias_habiles = models.PositiveSmallIntegerField()
    fundamento_normativo = models.CharField(max_length=255, blank=True)
    activo = models.BooleanField(default=True)

    class Meta:
        verbose_name = _("Tipo de trámite")
        verbose_name_plural = _("Tipos de trámite")
        ordering = ["codigo"]

    def __str__(self):
        return f"{self.codigo} - {self.nombre}"


class SubserieTramite(models.Model):
    """Mapa 1-a-1 entre una Subserie Documental y un tipo de trámite definido por la TRD."""

    subserie = models.OneToOneField(
        SubserieDocumental,
        on_delete=models.CASCADE,
        related_name="tramite_map",
    )
    tramite = models.ForeignKey(
        TramiteTipo,
        on_delete=models.PROTECT,
        related_name="subseries",
    )

    class Meta:
        verbose_name = _("Trámite por subserie")
        verbose_name_plural = _("Trámites por subserie")

    def __str__(self):
        return f"{self.subserie} → {self.tramite}"


class CalendarioLaboral(models.Model):
    """Indica si una fecha determinada es hábil o no.

    Si la tabla está vacía, el utilitario _es_habil caerá al cálculo por día de la semana.
    """

    fecha = models.DateField(unique=True, db_index=True)
    es_habil = models.BooleanField(default=True)

    class Meta:
        verbose_name = _("Día laboral")
        verbose_name_plural = _("Calendario laboral")
        ordering = ["fecha"]

    def __str__(self):
        return f"{self.fecha} - {'Hábil' if self.es_habil else 'Feriado'}"
