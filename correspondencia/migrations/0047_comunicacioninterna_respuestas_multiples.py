# Generated manually - Respuestas múltiples para comunicaciones internas

from django.db import migrations, models


class Migration(migrations.Migration):
    """
    Migración para permitir múltiples respuestas a comunicaciones internas.
    
    Cambios:
    1. Agrega campo es_respuesta_destacada para marcar respuestas de líderes/asignados
    2. Elimina el constraint unique_respuesta_por_comunicacion
    
    Flujo nuevo:
    - Cualquier destinatario puede responder a una comunicación
    - Las respuestas NO se pueden responder (solo ida y vuelta)
    - Líderes y usuarios asignados tienen respuestas destacadas (estrellita)
    """

    dependencies = [
        ('correspondencia', '0046_add_origen_radicacion'),
    ]

    operations = [
        # 1. Agregar campo es_respuesta_destacada
        migrations.AddField(
            model_name='comunicacioninterna',
            name='es_respuesta_destacada',
            field=models.BooleanField(
                default=False,
                help_text='Indica si esta respuesta está destacada (estrellita). Líderes y usuarios asignados inicialmente tienen respuestas destacadas.'
            ),
        ),
        
        # 2. Eliminar el constraint único que solo permitía 1 respuesta
        migrations.RemoveConstraint(
            model_name='comunicacioninterna',
            name='unique_respuesta_por_comunicacion',
        ),
    ]
