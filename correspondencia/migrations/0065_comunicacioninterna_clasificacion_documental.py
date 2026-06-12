from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('documentos', '0021_prestamodocumental_oficina_responsable'),
        ('correspondencia', '0064_comunicacioninterna_radicado_archivistico'),
    ]

    operations = [
        migrations.AddField(
            model_name='comunicacioninterna',
            name='serie_documental',
            field=models.ForeignKey(blank=True, help_text='Serie documental asociada a la comunicación interna', null=True, on_delete=django.db.models.deletion.PROTECT, related_name='comunicaciones_internas', to='documentos.seriedocumental'),
        ),
        migrations.AddField(
            model_name='comunicacioninterna',
            name='subserie_documental',
            field=models.ForeignKey(blank=True, help_text='Subserie documental asociada a la comunicación interna', null=True, on_delete=django.db.models.deletion.PROTECT, related_name='comunicaciones_internas', to='documentos.subseriedocumental'),
        ),
    ]