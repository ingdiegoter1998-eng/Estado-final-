from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('correspondencia', '0074_postmark_webhooks'),
    ]

    operations = [
        migrations.AddField(
            model_name='estadosincronizacioncorreos',
            name='ultimo_history_id',
            field=models.CharField(blank=True, default='', max_length=64),
        ),
        migrations.AddField(
            model_name='estadosincronizacioncorreos',
            name='ultima_renovacion_watch',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='estadosincronizacioncorreos',
            name='watch_expira_en',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='estadosincronizacioncorreos',
            name='watch_topic',
            field=models.CharField(blank=True, default='', max_length=255),
        ),
        migrations.AlterField(
            model_name='ejecucioncontrolcorreos',
            name='tipo_operacion',
            field=models.CharField(
                choices=[
                    ('VERIFY', 'Verificar cobertura Gmail vs BD'),
                    ('RECOVER', 'Recuperar faltantes'),
                    ('DUPLICATES', 'Verificar duplicados'),
                    ('DIAGNOSE', 'Diagnóstico operativo'),
                    ('IMAP_TEST', 'Probar conexión IMAP'),
                    ('SYNC_NOW', 'Sincronización inmediata'),
                    ('GMAIL_PUBSUB_PULL', 'Consumir Pub/Sub Gmail'),
                    ('GMAIL_WATCH_RENEW', 'Renovar watch Gmail'),
                    ('GMAIL_HISTORY_SYNC', 'Sincronizar history Gmail'),
                    ('GMAIL_PIPELINE_TICK', 'Ciclo Gmail (watch + Pub/Sub)'),
                    ('GMAIL_STATUS', 'Estado operativo Gmail API'),
                ],
                max_length=24,
            ),
        ),
    ]
