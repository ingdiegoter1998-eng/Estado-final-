from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('correspondencia', '0063_ejecucioncontrolcorreos'),
    ]

    operations = [
        migrations.AddField(
            model_name='comunicacioninterna',
            name='anio_radicado',
            field=models.PositiveSmallIntegerField(blank=True, editable=False, null=True),
        ),
        migrations.AddField(
            model_name='comunicacioninterna',
            name='codigo_dependencia',
            field=models.CharField(
                blank=True,
                editable=False,
                help_text='Código jerárquico de la dependencia/oficina productora',
                max_length=30,
                null=True,
            ),
        ),
        migrations.AddField(
            model_name='comunicacioninterna',
            name='consecutivo_radicado',
            field=models.PositiveIntegerField(blank=True, editable=False, null=True),
        ),
    ]