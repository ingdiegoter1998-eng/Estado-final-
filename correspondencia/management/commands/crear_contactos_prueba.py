from django.core.management.base import BaseCommand
from correspondencia.models import Contacto, EntidadExterna


class Command(BaseCommand):
    help = 'Crear contactos globales de prueba'

    def handle(self, *args, **options):
        # Obtener o crear entidades de prueba
        entidades_prueba = [
            ('Empresa ABC S.A.S.', 'empresa_abc@test.com'),
            ('Clínica XYZ Ltda.', 'contacto@clinica-xyz.com'),
            ('Consultorio Médico 123', 'admin@consultorio123.com'),
        ]

        contactos_creados = 0
        
        for nombre_entidad, email_dominio in entidades_prueba:
            # Crear o obtener entidad
            entidad, created = EntidadExterna.objects.get_or_create(
                nombre=nombre_entidad,
                defaults={'dominio': email_dominio}
            )
            
            if created:
                self.stdout.write(f"✓ Entidad creada: {nombre_entidad}")
            
            # Crear contactos para esta entidad
            contactos_entidad = [
                {
                    'nombres': 'Juan',
                    'apellidos': 'Pérez',
                    'cargo': 'Gerente Administrativo',
                    'correo_electronico': f'juan.perez@{email_dominio}',
                    'telefono_contacto': '3001234567'
                },
                {
                    'nombres': 'María',
                    'apellidos': 'González',
                    'cargo': 'Contadora',
                    'correo_electronico': f'maria.gonzalez@{email_dominio}',
                    'telefono_contacto': '3009876543'
                },
                {
                    'nombres': 'Carlos',
                    'apellidos': 'Rodríguez',
                    'cargo': 'Auxiliar Contable',
                    'correo_electronico': f'carlos.rodriguez@{email_dominio}',
                    'telefono_contacto': '3005551234'
                }
            ]
            
            for datos_contacto in contactos_entidad:
                contacto, created = Contacto.objects.get_or_create(
                    entidad_externa=entidad,
                    correo_electronico=datos_contacto['correo_electronico'],
                    defaults={
                        'nombres': datos_contacto['nombres'],
                        'apellidos': datos_contacto['apellidos'],
                        'cargo': datos_contacto['cargo'],
                        'telefono_contacto': datos_contacto['telefono_contacto']
                    }
                )
                
                if created:
                    contactos_creados += 1
                    self.stdout.write(
                        f"✓ Contacto creado: {contacto.nombre_completo} ({entidad.nombre})"
                    )
                else:
                    self.stdout.write(
                        f"- Contacto ya existe: {contacto.nombre_completo} ({entidad.nombre})"
                    )

        self.stdout.write(
            self.style.SUCCESS(
                f"\nResumen: {contactos_creados} contactos globales creados"
            )
        )
