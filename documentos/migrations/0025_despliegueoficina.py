from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('documentos', '0024_historialdescargaprestamo'),
    ]

    operations = [
        migrations.CreateModel(
            name='DespliegueOficina',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('estado_visita', models.CharField(
                    choices=[
                        ('pendiente', 'Pendiente de visita'),
                        ('visitada', 'Visitada'),
                        ('capacitada', 'Capacitada'),
                        ('no_aplica', 'No aplica'),
                    ],
                    default='pendiente',
                    max_length=20,
                )),
                ('fecha_visita', models.DateField(blank=True, null=True)),
                ('notas', models.TextField(blank=True, default='')),
                ('actualizado_en', models.DateTimeField(auto_now=True)),
                ('actualizado_por', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='despliegues_oficina_actualizados',
                    to=settings.AUTH_USER_MODEL,
                )),
                ('oficina', models.OneToOneField(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='despliegue',
                    to='documentos.oficinaproductora',
                )),
            ],
            options={
                'verbose_name': 'Despliegue de oficina',
                'verbose_name_plural': 'Despliegues de oficinas',
            },
        ),
    ]
