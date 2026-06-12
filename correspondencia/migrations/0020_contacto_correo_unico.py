from django.db import migrations, models
import django.db.models as dj_models


class Migration(migrations.Migration):

    dependencies = [
        ('correspondencia', '0019_alter_historialcorrespondencia_evento_and_more'),
    ]

    operations = [
        migrations.AddConstraint(
            model_name='contacto',
            constraint=dj_models.UniqueConstraint(
                fields=['oficina_propietaria', 'correo_electronico'],
                condition=dj_models.Q(correo_electronico__isnull=False),
                name='contacto_correo_oficina_unico'
            ),
        ),
    ]

