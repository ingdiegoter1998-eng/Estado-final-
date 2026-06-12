from django.db import migrations, models

import correspondencia.models


class Migration(migrations.Migration):

    dependencies = [
        ('correspondencia', '0072_notificacion_tipo_rebote'),
    ]

    operations = [
        migrations.AddField(
            model_name='correoproblematico',
            name='respaldo_eml',
            field=models.FileField(
                blank=True,
                help_text='Respaldo RFC822/.eml del correo original para permitir su admisión manual posterior.',
                max_length=255,
                null=True,
                upload_to=correspondencia.models.ruta_respaldo_correo_problematico,
            ),
        ),
    ]