from django.core.management.base import BaseCommand
from django.db import connection
from correspondencia.modelos_minimos_sla import SubserieTramite, TramiteTipo
from documentos.models import SubserieDocumental, SerieDocumental


class Command(BaseCommand):
    help = 'Verifica el estado del sistema SLA y mapeos TRD'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('🔍 Verificando sistema SLA...'))
        
        # Verificar modelos TRD
        self.stdout.write('\n📊 ESTADO DE MODELOS TRD:')
        
        # Contar tipos de trámite
        tramites_count = TramiteTipo.objects.count()
        self.stdout.write(f'   • Tipos de trámite: {tramites_count}')
        
        if tramites_count > 0:
            self.stdout.write('   • Primeros 5 tipos de trámite:')
            for tramite in TramiteTipo.objects.all()[:5]:
                self.stdout.write(f'     - {tramite.codigo}: {tramite.nombre} ({tramite.plazo_dias_habiles} días)')
        
        # Contar mapeos TRD
        mapeos_count = SubserieTramite.objects.count()
        self.stdout.write(f'   • Mapeos TRD: {mapeos_count}')
        
        if mapeos_count > 0:
            self.stdout.write('   • Primeros 5 mapeos TRD:')
            for mapeo in SubserieTramite.objects.select_related('subserie', 'tramite').all()[:5]:
                self.stdout.write(f'     - {mapeo.subserie.nombre} → {mapeo.tramite.codigo}')
        
        # Verificar subseries sin mapeo
        subseries_sin_mapeo = SubserieDocumental.objects.filter(tramite_map__isnull=True).count()
        self.stdout.write(f'   • Subseries sin mapeo TRD: {subseries_sin_mapeo}')
        
        # Verificar series y subseries
        self.stdout.write('\n📊 ESTADO DE SERIES Y SUBSERIES:')
        series_count = SerieDocumental.objects.count()
        subseries_count = SubserieDocumental.objects.count()
        self.stdout.write(f'   • Series documentales: {series_count}')
        self.stdout.write(f'   • Subseries documentales: {subseries_count}')
        
        if series_count > 0:
            self.stdout.write('   • Primeras 3 series:')
            for serie in SerieDocumental.objects.all()[:3]:
                subseries_de_serie = SubserieDocumental.objects.filter(serie=serie).count()
                self.stdout.write(f'     - {serie.nombre} ({subseries_de_serie} subseries)')
                
                if subseries_de_serie > 0:
                    for subserie in SubserieDocumental.objects.filter(serie=serie)[:3]:
                        tiene_mapeo = hasattr(subserie, 'tramite_map')
                        self.stdout.write(f'       • {subserie.nombre} (ID: {subserie.id}) - TRD: {"✅" if tiene_mapeo else "❌"}')
        
        # Verificar endpoint
        self.stdout.write('\n🔗 VERIFICACIÓN DE ENDPOINT:')
        try:
            from django.urls import reverse
            from django.test import Client
            from django.contrib.auth import get_user_model
            
            User = get_user_model()
            client = Client()
            
            # Crear usuario de prueba si no existe
            test_user, created = User.objects.get_or_create(
                username='test_sla',
                defaults={'email': 'test@sla.com', 'is_staff': True}
            )
            
            if created:
                test_user.set_password('test123')
                test_user.save()
            
            # Login
            client.login(username='test_sla', password='test123')
            
            # Probar endpoint
            url = reverse('correspondencia:calcular_plazo_sla')
            response = client.post(url, {
                'subserie_id': 1,
                'requiere_respuesta': 'true'
            })
            
            if response.status_code == 200:
                self.stdout.write(self.style.SUCCESS(f'   ✅ Endpoint responde correctamente (Status: {response.status_code})'))
                try:
                    import json
                    data = json.loads(response.content)
                    self.stdout.write(f'   📄 Respuesta: {data}')
                except:
                    self.stdout.write(f'   📄 Respuesta: {response.content.decode()}')
            else:
                self.stdout.write(self.style.ERROR(f'   ❌ Endpoint falla (Status: {response.status_code})'))
                self.stdout.write(f'   📄 Respuesta: {response.content.decode()}')
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'   ❌ Error al probar endpoint: {e}'))
        
        # Recomendaciones
        self.stdout.write('\n💡 RECOMENDACIONES:')
        if mapeos_count == 0:
            self.stdout.write(self.style.WARNING('   ⚠️  No hay mapeos TRD configurados. El SLA calculator no funcionará correctamente.'))
            self.stdout.write('   💡 Para crear un mapeo de prueba:')
            self.stdout.write('      python manage.py shell')
            self.stdout.write('      from correspondencia.modelos_minimos_sla import TramiteTipo, SubserieTramite')
            self.stdout.write('      from documentos.models import SubserieDocumental')
            self.stdout.write('      tramite = TramiteTipo.objects.create(codigo="TEST", nombre="Trámite de Prueba", plazo_dias_habiles=5)')
            self.stdout.write('      subserie = SubserieDocumental.objects.first()')
            self.stdout.write('      SubserieTramite.objects.create(subserie=subserie, tramite=tramite)')
        
        if subseries_count == 0:
            self.stdout.write(self.style.WARNING('   ⚠️  No hay subseries documentales. El SLA calculator no tendrá datos para trabajar.'))
        
        self.stdout.write(self.style.SUCCESS('\n✅ Verificación completada'))
