from django.core.management.base import BaseCommand
from correspondencia.models import CorrespondenciaSalida, SalidaDestinatario
from django.db import transaction


class Command(BaseCommand):
    help = 'Backfill de SalidaDestinatario para correspondencias de salida existentes'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Mostrar qué se haría sin ejecutar cambios',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        
        # Obtener todas las salidas que no tienen destinatarios
        salidas_sin_destinatarios = CorrespondenciaSalida.objects.filter(
            destinatarios__isnull=True
        ).select_related('destinatario_contacto', 'respuesta_a__oficina_destino')
        
        self.stdout.write(f"Encontradas {salidas_sin_destinatarios.count()} salidas sin destinatarios")
        
        if dry_run:
            self.stdout.write("=== MODO DRY-RUN ===")
        
        creados = 0
        errores = 0
        
        for salida in salidas_sin_destinatarios:
            try:
                # Verificar que tiene destinatario_contacto (campo antiguo)
                if not salida.destinatario_contacto:
                    self.stdout.write(
                        self.style.WARNING(
                            f"Salida {salida.numero_radicado_salida}: Sin destinatario_contacto"
                        )
                    )
                    errores += 1
                    continue
                
                # Verificar que tiene oficina emisora
                if not salida.oficina_emisora and salida.respuesta_a:
                    salida.oficina_emisora = salida.respuesta_a.oficina_destino
                
                if not salida.oficina_emisora:
                    self.stdout.write(
                        self.style.WARNING(
                            f"Salida {salida.numero_radicado_salida}: Sin oficina emisora"
                        )
                    )
                    errores += 1
                    continue
                
                contacto = salida.destinatario_contacto
                
                if not dry_run:
                    with transaction.atomic():
                        # Crear SalidaDestinatario
                        SalidaDestinatario.objects.create(
                            correspondencia_salida=salida,
                            contacto=contacto,
                            email_snapshot=contacto.correo_electronico or '',
                            nombre_snapshot=contacto.nombre_completo,
                            estado='PENDIENTE' if salida.estado in ['BORRADOR', 'PENDIENTE_APROBACION'] else 'ENVIADO'
                        )
                        
                        # Actualizar snapshots si no existen
                        if not salida.oficina_emisora_nombre:
                            salida.oficina_emisora_nombre = salida.oficina_emisora.nombre
                        if not salida.redactor_nombre and salida.usuario_redactor:
                            salida.redactor_nombre = (
                                f"{salida.usuario_redactor.first_name} {salida.usuario_redactor.last_name}".strip() 
                                or salida.usuario_redactor.username
                            )
                        if not salida.redactor_cargo and salida.usuario_redactor:
                            try:
                                salida.redactor_cargo = getattr(salida.usuario_redactor, 'perfil', None).cargo
                            except:
                                pass
                        salida.save(update_fields=['oficina_emisora_nombre', 'redactor_nombre', 'redactor_cargo'])
                
                creados += 1
                self.stdout.write(
                    f"✓ Salida {salida.numero_radicado_salida}: {contacto.nombre_completo} <{contacto.correo_electronico}>"
                )
                
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(
                        f"Error en salida {salida.numero_radicado_salida}: {e}"
                    )
                )
                errores += 1
        
        self.stdout.write(
            self.style.SUCCESS(
                f"\nResumen: {creados} destinatarios creados, {errores} errores"
            )
        )
