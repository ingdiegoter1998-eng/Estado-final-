# Generated manually for adding numero_documento field

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('correspondencia', '0017_agregar_modelo_notificacion'),
    ]

    operations = [
        migrations.AddField(
            model_name='contacto',
            name='numero_documento',
            field=models.CharField(
                blank=True, 
                help_text='Cédula, pasaporte u otro documento de identificación (opcional)', 
                max_length=50, 
                null=True, 
                verbose_name='Número de Documento'
            ),
        ),
    ]
