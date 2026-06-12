import unicodedata

from django.db import migrations, models


def normalizar_nombre_oficina(valor):
    texto = unicodedata.normalize('NFKD', (valor or '').strip())
    texto = ''.join(ch for ch in texto if not unicodedata.combining(ch))
    texto = texto.lower()
    texto = texto.replace('.', ' ')
    texto = texto.replace(',', ' ')
    texto = texto.replace('-', ' ')
    return ' '.join(texto.split())


CODIGOS_SIS_POR_OFICINA = {
    'subgerencia cientifica': 'SUC-00',
}


def poblar_codigo_sis(apps, schema_editor):
    OficinaProductora = apps.get_model('documentos', 'OficinaProductora')
    actualizaciones = []
    for oficina in OficinaProductora.objects.all():
        codigo = CODIGOS_SIS_POR_OFICINA.get(normalizar_nombre_oficina(oficina.nombre))
        if codigo:
            oficina.codigo_sis = codigo
            actualizaciones.append(oficina)
    if actualizaciones:
        OficinaProductora.objects.bulk_update(actualizaciones, ['codigo_sis'])


def revertir_codigo_sis(apps, schema_editor):
    OficinaProductora = apps.get_model('documentos', 'OficinaProductora')
    OficinaProductora.objects.filter(
        codigo_sis__in=set(CODIGOS_SIS_POR_OFICINA.values())
    ).update(codigo_sis=None)


class Migration(migrations.Migration):

    dependencies = [
        ('documentos', '0025_despliegueoficina'),
    ]

    operations = [
        migrations.AddField(
            model_name='oficinaproductora',
            name='codigo_sis',
            field=models.CharField(
                blank=True,
                help_text='Código SIS de la dependencia para comunicaciones internas (ej: SUC-00, DIR-03). Si se define, tiene prioridad sobre el cálculo automático.',
                max_length=30,
                null=True,
            ),
        ),
        migrations.RunPython(poblar_codigo_sis, revertir_codigo_sis),
    ]
