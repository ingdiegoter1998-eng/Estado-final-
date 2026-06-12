from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('correspondencia', '0075_estado_sincronizacion_gmail_watch_fields'),
    ]

    operations = [
        migrations.AddIndex(
            model_name='correspondenciasalida',
            index=models.Index(
                fields=['estado', 'respuesta_a'],
                name='corr_salida_est_resp_idx',
            ),
        ),
        migrations.AddIndex(
            model_name='correspondencia',
            index=models.Index(
                fields=['estado', 'fecha_radicacion'],
                name='corr_estado_fradic_idx',
            ),
        ),
    ]
