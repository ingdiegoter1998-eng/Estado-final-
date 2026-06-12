from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('correspondencia', '0062_adjuntocorreoentrante_content_id'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='EjecucionControlCorreos',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('tipo_operacion', models.CharField(choices=[('VERIFY', 'Verificar cobertura Gmail vs BD'), ('RECOVER', 'Recuperar faltantes'), ('DUPLICATES', 'Verificar duplicados'), ('DIAGNOSE', 'Diagnóstico operativo'), ('IMAP_TEST', 'Probar conexión IMAP'), ('SYNC_NOW', 'Sincronización inmediata')], max_length=24)),
                ('estado', models.CharField(choices=[('PENDING', 'Pendiente'), ('RUNNING', 'En ejecución'), ('SUCCESS', 'Exitosa'), ('WARN', 'Exitosa con advertencias'), ('FAIL', 'Fallida')], default='PENDING', max_length=16)),
                ('task_id', models.CharField(blank=True, default='', max_length=255)),
                ('parametros', models.TextField(blank=True, default='{}')),
                ('resumen', models.TextField(blank=True, default='{}')),
                ('salida', models.TextField(blank=True, default='')),
                ('error', models.TextField(blank=True, default='')),
                ('total_encontrados', models.PositiveIntegerField(blank=True, null=True)),
                ('total_nuevos', models.PositiveIntegerField(blank=True, null=True)),
                ('total_guardados', models.PositiveIntegerField(blank=True, null=True)),
                ('total_rechazados', models.PositiveIntegerField(blank=True, null=True)),
                ('total_adjuntos', models.PositiveIntegerField(blank=True, null=True)),
                ('total_duplicados', models.PositiveIntegerField(blank=True, null=True)),
                ('total_sospechosos', models.PositiveIntegerField(blank=True, null=True)),
                ('total_errores', models.PositiveIntegerField(blank=True, null=True)),
                ('creado_en', models.DateTimeField(auto_now_add=True)),
                ('iniciado_en', models.DateTimeField(blank=True, null=True)),
                ('finalizado_en', models.DateTimeField(blank=True, null=True)),
                ('ejecutado_por', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='ejecuciones_control_correos', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Ejecución de Control de Correos',
                'verbose_name_plural': 'Ejecuciones de Control de Correos',
                'ordering': ['-creado_en'],
            },
        ),
    ]