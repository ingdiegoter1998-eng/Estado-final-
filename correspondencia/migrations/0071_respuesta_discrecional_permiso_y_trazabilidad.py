from django.db import migrations, models


PERMISO_CODENAME = 'responder_correspondencia_discrecional'
PERMISO_NOMBRE = 'Puede responder discrecionalmente correspondencias que no requieren respuesta'
GRUPO_NOMBRE = 'Respuesta discrecional correspondencia'
OFICINAS_INICIALES = ['Planeación', 'Planeacion', 'Facturación', 'Facturacion']


def seed_discretionary_response_group(apps, schema_editor):
    ContentType = apps.get_model('contenttypes', 'ContentType')
    Permission = apps.get_model('auth', 'Permission')
    Group = apps.get_model('auth', 'Group')
    PerfilUsuario = apps.get_model('documentos', 'PerfilUsuario')

    try:
        content_type = ContentType.objects.get(app_label='correspondencia', model='correspondencia')
    except ContentType.DoesNotExist:
        # En SQLite fresco (tests) el ContentType puede no existir aún.
        return
    permiso, _ = Permission.objects.get_or_create(
        codename=PERMISO_CODENAME,
        content_type_id=content_type.id,
        defaults={'name': PERMISO_NOMBRE},
    )

    grupo, _ = Group.objects.get_or_create(name=GRUPO_NOMBRE)
    grupo.permissions.add(permiso)

    user_ids = list(
        PerfilUsuario.objects.filter(oficina__nombre__in=OFICINAS_INICIALES).values_list('user_id', flat=True)
    )
    if user_ids:
        grupo.user_set.add(*user_ids)


def noop_reverse(apps, schema_editor):
    return


class Migration(migrations.Migration):

    dependencies = [
        ('correspondencia', '0070_chat_adjuntos'),
        ('documentos', '0021_prestamodocumental_oficina_responsable'),
        ('auth', '0012_alter_user_first_name_max_length'),
        ('contenttypes', '0002_remove_content_type_name'),
    ]

    operations = [
        migrations.AddField(
            model_name='correspondenciasalida',
            name='motivo_respuesta_discrecional',
            field=models.TextField(blank=True, default='', help_text='Motivo obligatorio cuando la respuesta es discrecional.'),
        ),
        migrations.AddField(
            model_name='correspondenciasalida',
            name='tipo_respuesta',
            field=models.CharField(choices=[('OBLIGATORIA', 'Obligatoria'), ('DISCRECIONAL', 'Discrecional')], default='OBLIGATORIA', help_text='Indica si la salida corresponde a una respuesta obligatoria o discrecional.', max_length=20),
        ),
        migrations.AlterModelOptions(
            name='correspondencia',
            options={
                'ordering': ['-fecha_radicacion'],
                'permissions': [
                    (
                        PERMISO_CODENAME,
                        PERMISO_NOMBRE,
                    ),
                ],
                'verbose_name': 'Correspondencia',
                'verbose_name_plural': 'Correspondencias',
            },
        ),
        migrations.RunPython(seed_discretionary_response_group, noop_reverse),
    ]
