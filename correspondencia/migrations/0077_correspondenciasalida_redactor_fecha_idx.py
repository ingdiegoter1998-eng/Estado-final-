from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('correspondencia', '0076_correspondenciasalida_sla_indexes'),
    ]

    operations = [
        migrations.AddIndex(
            model_name='correspondenciasalida',
            index=models.Index(
                fields=['usuario_redactor', '-fecha_creacion'],
                name='corr_salida_red_fcrea_idx',
            ),
        ),
    ]
