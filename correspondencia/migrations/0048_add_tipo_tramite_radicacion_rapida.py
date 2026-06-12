# Generated manually - Tipo de trámite (texto libre) para radicación rápida entrante

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('correspondencia', '0047_comunicacioninterna_respuestas_multiples'),
    ]

    operations = [
        migrations.AddField(
            model_name='correspondencia',
            name='tipo_tramite',
            field=models.CharField(
                blank=True,
                help_text='Tipo de trámite (texto libre, radicación rápida)',
                max_length=255,
                null=True
            ),
        ),
    ]
