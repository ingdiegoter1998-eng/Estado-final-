from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('correspondencia', '0061_firma_auxiliar_correspondencia'),
    ]

    operations = [
        migrations.AddField(
            model_name='adjuntocorreoentrante',
            name='content_id',
            field=models.CharField(blank=True, db_index=True, help_text='Content-ID del adjunto, útil para imágenes inline del HTML', max_length=255),
        ),
    ]