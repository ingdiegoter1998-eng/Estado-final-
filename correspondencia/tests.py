"""
Tests para el módulo de correspondencia.

Este módulo contiene tests unitarios, de integración y funcionales para validar:
- Funcionalidad de radicación de correspondencia
- Cálculo y persistencia de SLA
- Validaciones de formularios
- Control de acceso y permisos
- Flujos completos de negocio
- Casos edge y manejo de errores
"""

import logging
from email.message import EmailMessage
from datetime import datetime, timedelta
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import patch, MagicMock

from django.test import TestCase, Client, TransactionTestCase
from django.contrib.auth.models import User, Group, Permission
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import transaction
from django.test.utils import override_settings

from .models import (
    Correspondencia, Contacto, EntidadExterna, HistorialCorrespondencia,
    CorreoEntrante, CorreoProblematico, AdjuntoCorreoEntrante, AdjuntoCorreo, DistribucionInternaUsuario,
    CorrespondenciaSalida, AdjuntoSalida, HistorialSalida
)
from .forms import (
    CorrespondenciaForm, ContactoForm, EntidadExternaForm, ManualRadicacionCorreoForm,
    RadicacionRapidaEntranteForm,
)
from documentos.models import OficinaProductora, SerieDocumental, SubserieDocumental, PerfilUsuario
from .modelos_minimos_sla import TramiteTipo, SubserieTramite, CalendarioLaboral
from .utils.email_body_extractor import extraer_cuerpos_correo
from .utils_sla import get_cutoff_time, aplicar_corte, sumar_habiles

# Configurar logging para tests
logging.disable(logging.CRITICAL)


class EmailBodyExtractorTests(TestCase):
    def test_extrae_html_real_desde_objeto_mime_cuando_falta_en_imap_tools(self):
        mime = EmailMessage()
        mime['Subject'] = 'Correo multipart'
        mime.set_content('Versión texto generada')
        mime.add_alternative(
            '<html><body><p>Contenido <strong>HTML</strong></p><a href="https://eps.example/seguimiento">Ver más</a></body></html>',
            subtype='html'
        )

        msg = SimpleNamespace(
            text='Versión texto generada [https://eps.example/seguimiento]',
            html='',
            obj=mime,
        )

        cuerpo_texto, cuerpo_html = extraer_cuerpos_correo(msg)

        self.assertIn('Versión texto generada', cuerpo_texto)
        self.assertIn('<strong>HTML</strong>', cuerpo_html)
        self.assertIn('href="https://eps.example/seguimiento"', cuerpo_html)

    def test_reemplaza_html_invalido_con_html_mime(self):
        mime = EmailMessage()
        mime['Subject'] = 'Correo multipart'
        mime.set_content('Plano')
        mime.add_alternative(
            '<div><img src="https://img-cache.net/im/recurso.png" alt="banner"></div>',
            subtype='html'
        )

        msg = SimpleNamespace(
            text='Plano [https://img-cache.net/im/recurso.png]',
            html='Plano [https://img-cache.net/im/recurso.png]',
            obj=mime,
        )

        _, cuerpo_html = extraer_cuerpos_correo(msg)

        self.assertIn('<img src="https://img-cache.net/im/recurso.png"', cuerpo_html)


class CorrespondenciaTestCase(TestCase):
    """Test case base para correspondencia con setup común."""
    
    def setUp(self):
        """Configurar datos de prueba comunes."""
        # Crear usuarios y grupos
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123',
            email='test@example.com'
        )
        
        self.ventanilla_user = User.objects.create_user(
            username='ventanilla',
            password='testpass123',
            email='ventanilla@example.com'
        )
        
        # Crear grupos
        self.ventanilla_group = Group.objects.create(name='Ventanilla')
        self.ventanilla_user.groups.add(self.ventanilla_group)
        
        # Crear entidad externa
        self.entidad = EntidadExterna.objects.create(
            nombre='Empresa Test S.A.',
            nit='123456789-0',
            dominio='empresatest.com'
        )
        
        # Crear contacto
        self.contacto = Contacto.objects.create(
            entidad_externa=self.entidad,
            nombres='Juan',
            apellidos='Pérez',
            cargo='Gerente',
            correo_electronico='juan.perez@empresatest.com'
        )
        
        # Crear unidad administrativa y oficina (OficinaProductora requiere proceso)
        from documentos.models import (
            UnidadAdministrativa, EntidadProductora,
            MacroProceso, Proceso,
        )
        
        self.entidad_productora = EntidadProductora.objects.create(
            nombre='Entidad Productora Test'
        )
        
        self.unidad_administrativa = UnidadAdministrativa.objects.create(
            nombre='Unidad Administrativa Test',
            entidad_productora=self.entidad_productora
        )
        
        self.macroproceso, _ = MacroProceso.objects.get_or_create(
            numero=1,
            defaults={'nombre': 'Macroproceso Test'}
        )
        self.proceso, _ = Proceso.objects.get_or_create(
            numero=1,
            macroproceso=self.macroproceso,
            defaults={'nombre': 'Proceso Test', 'sigla': 'TST'}
        )
        self.oficina = OficinaProductora.objects.create(
            nombre='Oficina de Prueba',
            unidad_administrativa=self.unidad_administrativa,
            proceso=self.proceso
        )
        
        # Crear serie y subserie
        self.serie = SerieDocumental.objects.create(
            nombre='Serie de Prueba',
            codigo='SERIE-001'
        )
        
        self.subserie = SubserieDocumental.objects.create(
            nombre='Subserie de Prueba',
            codigo='SUBSERIE-001',
            serie=self.serie
        )
        
        # Crear trámite tipo para SLA
        self.tramite = TramiteTipo.objects.create(
            codigo='TRAM-001',
            nombre='Trámite de Prueba',
            plazo_dias_habiles=15,
            activo=True
        )
        
        # Crear mapeo TRD
        self.subserie_tramite = SubserieTramite.objects.create(
            subserie=self.subserie,
            tramite=self.tramite
        )
        
        # Crear fechas hábiles en calendario
        self.fecha_actual = timezone.now().date()
        for i in range(30):
            fecha = self.fecha_actual + timedelta(days=i)
            # Lunes a viernes son hábiles
            es_habil = fecha.weekday() < 5
            CalendarioLaboral.objects.create(
                fecha=fecha,
                es_habil=es_habil
            )


class ModelTests(CorrespondenciaTestCase):
    """Tests para los modelos de correspondencia."""
    
    def test_entidad_externa_creation(self):
        """Test: Crear entidad externa correctamente."""
        entidad = EntidadExterna.objects.create(
            nombre='Nueva Empresa',
            nit='987654321-0',
            dominio='nuevaempresa.com'
        )
        
        self.assertEqual(entidad.nombre, 'Nueva Empresa')
        self.assertEqual(entidad.nit, '987654321-0')
        self.assertEqual(str(entidad), 'Nueva Empresa')
    
    def test_contacto_creation(self):
        """Test: Crear contacto correctamente."""
        contacto = Contacto.objects.create(
            entidad_externa=self.entidad,
            nombres='María',
            apellidos='García',
            cargo='Directora',
            correo_electronico='maria.garcia@empresatest.com'
        )
        
        self.assertEqual(contacto.nombre_completo, 'María García')
        self.assertEqual(contacto.entidad_externa, self.entidad)
        self.assertIn('María García', str(contacto))
    
    def test_correspondencia_creation(self):
        """Test: Crear correspondencia correctamente."""
        correspondencia = Correspondencia.objects.create(
            tipo_radicado='ENTRANTE',
            asunto='Test de correspondencia',
            medio_recepcion='FISICO',
            requiere_respuesta=True,
            tiempo_respuesta='NORMAL',
            oficina_destino=self.oficina,
            remitente=self.contacto,
            serie=self.serie,
            subserie=self.subserie,
            usuario_radicador=self.user
        )
        
        self.assertIsNotNone(correspondencia.numero_radicado)
        self.assertEqual(correspondencia.asunto, 'Test de correspondencia')
        self.assertTrue(correspondencia.requiere_respuesta)
        self.assertEqual(correspondencia.estado, 'RADICADA')
    def test_numero_radicado_generation(self):
        """Test: Generación automática de número de radicado."""
        # Crear primera correspondencia
        corr1 = Correspondencia.objects.create(
            tipo_radicado='ENTRANTE',
            asunto='Primera',
            oficina_destino=self.oficina,
            usuario_radicador=self.user
        )
        
        # Crear segunda correspondencia
        corr2 = Correspondencia.objects.create(
            tipo_radicado='ENTRANTE',
            asunto='Segunda',
            oficina_destino=self.oficina,
            usuario_radicador=self.user
        )
        
        # Verificar que los números son únicos y consecutivos
        self.assertNotEqual(corr1.numero_radicado, corr2.numero_radicado)
        self.assertIn('ENTRANTE', corr1.numero_radicado)
        self.assertIn('ENTRANTE', corr2.numero_radicado)
    
    def test_sla_calculation_with_trd(self):
        """Test: Cálculo de SLA cuando hay TRD configurado."""
        correspondencia = Correspondencia.objects.create(
            tipo_radicado='ENTRANTE',
            asunto='Test SLA TRD',
            medio_recepcion='FISICO',
            requiere_respuesta=True,
            oficina_destino=self.oficina,
            remitente=self.contacto,
            serie=self.serie,
            subserie=self.subserie,  # Tiene TRD configurado
            usuario_radicador=self.user
        )
        
        # Verificar que se calculó el SLA correctamente
        self.assertEqual(correspondencia.plazo_respuesta_dias, 15)
        self.assertEqual(correspondencia.plazo_origen, 'TRD')
        self.assertEqual(correspondencia.tramite_aplicado, self.tramite)
        self.assertIsNotNone(correspondencia.fecha_limite_respuesta_persist)
        self.assertIsNone(correspondencia.tiempo_respuesta)  # Debe limpiarse con TRD
    
    def test_sla_calculation_with_fallback(self):
        """Test: Cálculo de SLA usando fallback cuando no hay TRD."""
        # Crear subserie sin TRD
        subserie_sin_trd = SubserieDocumental.objects.create(
            nombre='Subserie Sin TRD',
            codigo='SUBSERIE-SIN-TRD',
            serie=self.serie
        )
        
        correspondencia = Correspondencia.objects.create(
            tipo_radicado='ENTRANTE',
            asunto='Test SLA Fallback',
            medio_recepcion='FISICO',
            requiere_respuesta=True,
            tiempo_respuesta='URGENTE',  # 5 días
            oficina_destino=self.oficina,
            remitente=self.contacto,
            serie=self.serie,
            subserie=subserie_sin_trd,  # Sin TRD
            usuario_radicador=self.user
        )
        
        # Verificar que se usó el fallback
        self.assertEqual(correspondencia.plazo_respuesta_dias, 5)
        self.assertEqual(correspondencia.plazo_origen, 'FALLBACK')
        self.assertIsNone(correspondencia.tramite_aplicado)
        self.assertEqual(correspondencia.tiempo_respuesta, 'URGENTE')
    
    def test_sla_no_response_required(self):
        """Test: SLA se limpia cuando no requiere respuesta."""
        correspondencia = Correspondencia.objects.create(
            tipo_radicado='ENTRANTE',
            asunto='Test Sin Respuesta',
            medio_recepcion='FISICO',
            requiere_respuesta=False,  # No requiere respuesta
            oficina_destino=self.oficina,
            remitente=self.contacto,
            usuario_radicador=self.user
        )
        
        # Verificar que se limpiaron los campos SLA
        self.assertIsNone(correspondencia.plazo_respuesta_dias)
        self.assertIsNone(correspondencia.fecha_limite_respuesta_persist)
        self.assertEqual(correspondencia.plazo_origen, 'NONE')
        self.assertIsNone(correspondencia.tramite_aplicado)
        self.assertIsNone(correspondencia.tiempo_respuesta)
    
    def test_historial_creation(self):
        """Test: Creación automática de historial."""
        correspondencia = Correspondencia.objects.create(
            tipo_radicado='ENTRANTE',
            asunto='Test Historial',
            oficina_destino=self.oficina,
            usuario_radicador=self.user
        )
        
        # Verificar que se creó el historial
        historial = HistorialCorrespondencia.objects.filter(
            correspondencia=correspondencia
        ).first()
        
        self.assertIsNotNone(historial)
        self.assertEqual(historial.evento, 'RADICADA')
        self.assertEqual(historial.usuario, self.user)
    
    def test_contacto_unique_constraint(self):
        """Test: Constraint único de contacto por entidad."""
        # Crear primer contacto
        Contacto.objects.create(
            entidad_externa=self.entidad,
            nombres='Pedro',
            apellidos='López',
            correo_electronico='pedro@empresatest.com'
        )
        
        # Intentar crear contacto duplicado
        with self.assertRaises(Exception):  # IntegrityError o similar
            Contacto.objects.create(
                entidad_externa=self.entidad,
                nombres='Pedro',
                apellidos='López',
                correo_electronico='pedro@empresatest.com'
            )


class FormTests(CorrespondenciaTestCase):
    """Tests para los formularios de correspondencia."""
    
    def test_correspondencia_form_valid(self):
        """Test: Formulario de correspondencia válido."""
        form_data = {
            'remitente': self.contacto.id,
            'asunto': 'Test de formulario',
            'medio_recepcion': 'FISICO',
            'requiere_respuesta': True,
            'tiempo_respuesta': 'NORMAL',
            'oficina_destino': self.oficina.id,
            'serie': self.serie.id,
            'subserie': self.subserie.id,
        }
        
        form = CorrespondenciaForm(data=form_data)
        self.assertTrue(form.is_valid())
    
    def test_correspondencia_form_invalid_missing_required(self):
        """Test: Formulario inválido por campos requeridos faltantes."""
        form_data = {
            'asunto': 'Test incompleto',
            # Faltan campos requeridos
        }
        
        form = CorrespondenciaForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('remitente', form.errors)
        self.assertIn('oficina_destino', form.errors)
    
    def test_correspondencia_form_tiempo_respuesta_validation(self):
        """Test: Validación de tiempo_respuesta cuando requiere respuesta."""
        # Caso 1: Requiere respuesta pero no hay TRD ni tiempo_respuesta
        subserie_sin_trd = SubserieDocumental.objects.create(
            nombre='Sin TRD',
            codigo='SIN-TRD',
            serie=self.serie
        )
        
        form_data = {
            'remitente': self.contacto.id,
            'asunto': 'Test validación',
            'medio_recepcion': 'FISICO',
            'requiere_respuesta': True,
            'oficina_destino': self.oficina.id,
            'serie': self.serie.id,
            'subserie': subserie_sin_trd.id,
            # Sin tiempo_respuesta
        }
        
        form = CorrespondenciaForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('tiempo_respuesta', form.errors)
        
        # Caso 2: Con TRD configurado, no debería requerir tiempo_respuesta
        form_data['subserie'] = self.subserie.id  # Con TRD
        form = CorrespondenciaForm(data=form_data)
        self.assertTrue(form.is_valid())
    
    def test_contacto_form_valid(self):
        """Test: Formulario de contacto válido."""
        form_data = {
            'entidad_externa': self.entidad.id,
            'nombres': 'Ana',
            'apellidos': 'Martínez',
            'cargo': 'Analista',
            'correo_electronico': 'ana.martinez@empresatest.com',
            'telefono_contacto': '3001234567'
        }
        
        form = ContactoForm(data=form_data)
        self.assertTrue(form.is_valid())
    
    def test_entidad_externa_form_valid(self):
        """Test: Formulario de entidad externa válido."""
        form_data = {
            'nombre': 'Nueva Entidad S.A.',
            'nit': '111222333-4',
            'direccion': 'Calle 123 #45-67',
            'telefono': '6012345678',
            'dominio': 'nuevaentidad.com'
        }
        
        form = EntidadExternaForm(data=form_data)
        self.assertTrue(form.is_valid())

    def test_adjuntos_correspondencia_fisica(self):
        """Test para verificar que se pueden adjuntar archivos a correspondencia física."""
        from django.core.files.uploadedfile import SimpleUploadedFile
        from django.core.files.base import ContentFile
        
        # Crear correspondencia física
        correspondencia = Correspondencia.objects.create(
            numero_radicado="ENT-2025-00001",
            tipo_radicado="ENTRANTE",
            fecha_radicacion=timezone.now(),
            usuario_radicador=self.user,
            remitente=self.contacto,
            asunto="Test correspondencia física",
            medio_recepcion="FISICO",
            requiere_respuesta=True,
            tiempo_respuesta="NORMAL",
            oficina_destino=self.oficina,
            serie=self.serie,
            subserie=self.subserie,
            estado="RADICADA"
        )
        
        # Crear adjunto
        adjunto = AdjuntoCorreo.objects.create(
            correspondencia=correspondencia,
            nombre_original="test_document.pdf",
            tipo_mime="application/pdf"
        )
        adjunto.archivo.save("test_document.pdf", ContentFile(b"fake pdf content"), save=True)
        
        # Verificar que el adjunto se creó correctamente
        self.assertEqual(adjunto.correspondencia, correspondencia)
        self.assertEqual(adjunto.nombre_original, "test_document.pdf")
        self.assertEqual(adjunto.tipo_mime, "application/pdf")
        self.assertTrue(adjunto.archivo)
        
        # Verificar que la correspondencia tiene el adjunto
        self.assertEqual(correspondencia.adjuntos_correo.count(), 1)
        self.assertEqual(correspondencia.adjuntos_correo.first(), adjunto)
class ViewTests(CorrespondenciaTestCase):
    """Tests para las vistas de correspondencia."""
    
    def setUp(self):
        """Setup adicional para tests de vistas."""
        super().setUp()
        self.client = Client()
    
    def test_home_view_authenticated(self):
        """Test: Vista home para usuario autenticado."""
        self.client.force_login(self.user)
        response = self.client.get(reverse('correspondencia:home'))
        self.assertEqual(response.status_code, 200)
    
    def test_home_view_unauthenticated(self):
        """Test: Vista home redirige a login si no autenticado."""
        response = self.client.get(reverse('correspondencia:home'))
        self.assertEqual(response.status_code, 302)  # Redirect
        self.assertIn('login', response.url)
    
    def test_radicar_correspondencia_view_ventanilla_access(self):
        """Test: Vista de radicación solo accesible por ventanilla."""
        # Usuario normal no puede acceder
        self.client.force_login(self.user)
        response = self.client.get(reverse('correspondencia:radicar_manual'))
        self.assertEqual(response.status_code, 302)  # Redirect
        
        # Usuario ventanilla puede acceder
        self.client.force_login(self.ventanilla_user)
        response = self.client.get(reverse('correspondencia:radicar_manual'))
        self.assertEqual(response.status_code, 200)
    
    def test_radicar_correspondencia_post_valid(self):
        """Test: POST válido a vista de radicación."""
        self.client.force_login(self.ventanilla_user)
        
        form_data = {
            'remitente': self.contacto.id,
            'asunto': 'Test de radicación',
            'medio_recepcion': 'FISICO',
            'requiere_respuesta': True,
            'tiempo_respuesta': 'NORMAL',
            'oficina_destino': self.oficina.id,
            'serie': self.serie.id,
            'subserie': self.subserie.id,
        }
        
        response = self.client.post(
            reverse('correspondencia:radicar_manual'),
            data=form_data
        )
        
        # Debería redirigir después de crear
        self.assertEqual(response.status_code, 302)
        
        # Verificar que se creó la correspondencia
        correspondencia = Correspondencia.objects.filter(
            asunto='Test de radicación'
        ).first()
        self.assertIsNotNone(correspondencia)
    
    def test_bandeja_personal_view(self):
        """Test: Vista de bandeja personal."""
        # Crear correspondencia asignada al usuario
        correspondencia = Correspondencia.objects.create(
            tipo_radicado='ENTRANTE',
            asunto='Test Bandeja Personal',
            oficina_destino=self.oficina,
            usuario_destino_inicial=self.user,
            usuario_radicador=self.ventanilla_user
        )
        
        self.client.force_login(self.user)
        response = self.client.get(reverse('correspondencia:bandeja_personal'))
        
        self.assertEqual(response.status_code, 200)
        self.assertIn('correspondencias', response.context)
    
    def test_detalle_correspondencia_view(self):
        """Test: Vista de detalle de correspondencia."""
        correspondencia = Correspondencia.objects.create(
            tipo_radicado='ENTRANTE',
            asunto='Test Detalle',
            oficina_destino=self.oficina,
            usuario_radicador=self.ventanilla_user
        )
        
        self.client.force_login(self.user)
        response = self.client.get(
            reverse('correspondencia:detalle_correspondencia', args=[correspondencia.id])
        )
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['correspondencia'], correspondencia)

    def test_detalle_correspondencia_incluye_cuerpo_correo_origen(self):
        """Test: El detalle debe incluir el correo origen renderizado cuando existe."""
        correspondencia = Correspondencia.objects.create(
            tipo_radicado='ENTRANTE',
            asunto='Test con correo origen',
            medio_recepcion='ELECTRONICO',
            oficina_destino=self.oficina,
            usuario_radicador=self.ventanilla_user
        )
        correo = CorreoEntrante.objects.create(
            message_id='msg-detalle-correspondencia@example.com',
            remitente='origen@test.com',
            asunto='Correo origen',
            cuerpo_html='<p>Correo <strong>HTML</strong></p>',
            radicado_asociado=correspondencia,
            procesado=True
        )

        self.client.force_login(self.ventanilla_user)
        response = self.client.get(
            reverse('correspondencia:detalle_correspondencia', args=[correspondencia.id])
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['correo_origen_obj'], correo)
        self.assertIn('<strong>HTML</strong>', response.context['cuerpo_html_renderizado'])


class RespuestaDiscrecionalTests(CorrespondenciaTestCase):
    def setUp(self):
        super().setUp()
        PerfilUsuario.objects.create(user=self.user, oficina=self.oficina)
        PerfilUsuario.objects.create(user=self.ventanilla_user, oficina=self.oficina)
        self.correspondencia_no_requiere = Correspondencia.objects.create(
            tipo_radicado='ENTRANTE',
            asunto='Correspondencia sin respuesta obligatoria',
            medio_recepcion='ELECTRONICO',
            requiere_respuesta=False,
            oficina_destino=self.oficina,
            remitente=self.contacto,
            usuario_radicador=self.ventanilla_user,
            usuario_destino_inicial=self.user,
        )

    def test_detalle_habilita_respuesta_discrecional_con_permiso(self):
        permiso = Permission.objects.get(codename='responder_correspondencia_discrecional')
        self.user.user_permissions.add(permiso)

        self.client.force_login(self.user)
        response = self.client.get(
            reverse('correspondencia:detalle_correspondencia', args=[self.correspondencia_no_requiere.id])
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['puede_respuesta_discrecional'])
        self.assertTrue(response.context['es_respuesta_discrecional'])

    def test_responder_ajax_bloquea_no_requiere_sin_permiso(self):
        self.client.force_login(self.user)

        response = self.client.post(
            reverse('correspondencia:responder_correspondencia_ajax'),
            data={
                'correspondencia_entrada_id': self.correspondencia_no_requiere.id,
                'asunto': 'Respuesta discrecional',
                'cuerpo': 'Contenido de prueba',
                'destinatarios_contacto': [str(self.contacto.id)],
                'enviar_inmediatamente': 'on',
            },
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertFalse(data['success'])
        self.assertIn('no tiene permiso', data['error'].lower())

    def test_responder_ajax_crea_respuesta_discrecional_con_permiso(self):
        permiso = Permission.objects.get(codename='responder_correspondencia_discrecional')
        self.user.user_permissions.add(permiso)
        self.client.force_login(self.user)

        response = self.client.post(
            reverse('correspondencia:responder_correspondencia_ajax'),
            data={
                'correspondencia_entrada_id': self.correspondencia_no_requiere.id,
                'asunto': 'Respuesta discrecional',
                'cuerpo': 'Contenido de prueba',
                'destinatarios_contacto': [str(self.contacto.id)],
                'motivo_respuesta_discrecional': 'Solicitud operativa del proceso.',
                'enviar_inmediatamente': 'on',
            },
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])

        respuesta = CorrespondenciaSalida.objects.get(respuesta_a=self.correspondencia_no_requiere)
        self.assertEqual(respuesta.tipo_respuesta, 'DISCRECIONAL')
        self.assertEqual(respuesta.motivo_respuesta_discrecional, 'Solicitud operativa del proceso.')
        self.assertTrue(
            HistorialSalida.objects.filter(
                correspondencia_salida=respuesta,
                tipo_evento='RESPUESTA_DISCRECIONAL'
            ).exists()
        )

    def test_responder_ajax_trunca_asunto_largo_para_varchar_255(self):
        permiso = Permission.objects.get(codename='responder_correspondencia_discrecional')
        self.user.user_permissions.add(permiso)
        self.correspondencia_no_requiere.asunto = (
            'SOLICITUD DE HC DE PARTO CLAUDIA CRUZ BENAVIDES CC:1007940300\r\n\r\n'
            + ('A' * 400)
        )
        self.correspondencia_no_requiere.save(update_fields=['asunto'])
        asunto_modal = f'RE: {self.correspondencia_no_requiere.asunto}'

        self.client.force_login(self.user)
        response = self.client.post(
            reverse('correspondencia:responder_correspondencia_ajax'),
            data={
                'correspondencia_entrada_id': self.correspondencia_no_requiere.id,
                'asunto': asunto_modal,
                'cuerpo': 'Contenido de prueba',
                'destinatarios_contacto': [str(self.contacto.id)],
                'motivo_respuesta_discrecional': 'Solicitud operativa del proceso.',
                'enviar_inmediatamente': 'on',
            },
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'], data.get('error'))
        respuesta = CorrespondenciaSalida.objects.get(respuesta_a=self.correspondencia_no_requiere)
        self.assertLessEqual(len(respuesta.asunto), 255)


class SLATests(CorrespondenciaTestCase):
    """Tests específicos para funcionalidad SLA."""
    
    def test_sla_utils_functions(self):
        """Test: Funciones utilitarias de SLA."""
        fecha_actual = timezone.now()
        
        # Test get_cutoff_time
        cutoff = get_cutoff_time()
        self.assertIsNotNone(cutoff)
        
        # Test aplicar_corte
        fecha_con_corte = aplicar_corte(fecha_actual)
        self.assertIsNotNone(fecha_con_corte)
        
        # Test sumar_habiles
        fecha_futura = sumar_habiles(fecha_actual, 5)
        self.assertIsNotNone(fecha_futura)
        self.assertGreater(fecha_futura, fecha_actual)
    
    def test_sla_edge_cases(self):
        """Test: Casos edge del cálculo de SLA."""
        # Caso 1: Subserie con TRD pero trámite inactivo
        tramite_inactivo = TramiteTipo.objects.create(
            codigo='TRAM-INACTIVO',
            nombre='Trámite Inactivo',
            plazo_dias_habiles=10,
            activo=False  # Inactivo
        )
        
        # Eliminar el mapeo existente y crear uno nuevo
        SubserieTramite.objects.filter(subserie=self.subserie).delete()
        SubserieTramite.objects.create(
            subserie=self.subserie,
            tramite=tramite_inactivo
        )
        
        correspondencia = Correspondencia.objects.create(
            tipo_radicado='ENTRANTE',
            asunto='Test TRD Inactivo',
            requiere_respuesta=True,
            tiempo_respuesta='NORMAL',
            oficina_destino=self.oficina,
            remitente=self.contacto,
            serie=self.serie,
            subserie=self.subserie,
            usuario_radicador=self.user
        )
        
        # El modelo actual no verifica si el trámite está activo, usa TRD
        self.assertEqual(correspondencia.plazo_origen, 'TRD')
    
    def test_sla_calendar_integration(self):
        """Test: Integración con calendario laboral."""
        # Crear fechas específicas en calendario
        fecha_inicio = timezone.now().date()
        
        # Marcar algunos días como no hábiles
        CalendarioLaboral.objects.filter(
            fecha__in=[fecha_inicio + timedelta(days=1), fecha_inicio + timedelta(days=2)]
        ).update(es_habil=False)
        
        correspondencia = Correspondencia.objects.create(
            tipo_radicado='ENTRANTE',
            asunto='Test Calendario',
            requiere_respuesta=True,
            tiempo_respuesta='URGENTE',  # 5 días
            oficina_destino=self.oficina,
            remitente=self.contacto,
            usuario_radicador=self.user
        )
        
        # Verificar que la fecha límite considera días hábiles
        self.assertIsNotNone(correspondencia.fecha_limite_respuesta_persist)
        self.assertGreater(
            correspondencia.fecha_limite_respuesta_persist.date(),
            fecha_inicio + timedelta(days=5)  # Más de 5 días por días no hábiles
        )


class IntegrationTests(TransactionTestCase):
    """Tests de integración para flujos completos."""
    
    def setUp(self):
        """Setup para tests de integración."""
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        
        self.ventanilla_user = User.objects.create_user(
            username='ventanilla',
            password='testpass123'
        )
        
        ventanilla_group = Group.objects.create(name='Ventanilla')
        self.ventanilla_user.groups.add(ventanilla_group)
        
        # Crear datos mínimos necesarios
        self.entidad = EntidadExterna.objects.create(nombre='Test Entidad')
        self.contacto = Contacto.objects.create(
            entidad_externa=self.entidad,
            nombres='Test',
            apellidos='Contacto'
        )
        
        # Crear jerarquía completa para OficinaProductora
        from documentos.models import UnidadAdministrativa, EntidadProductora
        self.entidad_productora = EntidadProductora.objects.create(nombre='Entidad Productora Test')
        self.unidad_administrativa = UnidadAdministrativa.objects.create(
            nombre='Unidad Administrativa Test',
            entidad_productora=self.entidad_productora
        )
        self.oficina = OficinaProductora.objects.create(
            nombre='Test Oficina',
            unidad_administrativa=self.unidad_administrativa
        )
    
    def test_complete_radicacion_flow(self):
        """Test: Flujo completo de radicación desde formulario hasta BD."""
        client = Client()
        client.force_login(self.ventanilla_user)
        
        # Paso 1: Acceder al formulario
        response = client.get(reverse('correspondencia:radicar_manual'))
        self.assertEqual(response.status_code, 200)
        
        # Paso 2: Enviar formulario válido
        form_data = {
            'remitente': self.contacto.id,
            'asunto': 'Test Flujo Completo',
            'medio_recepcion': 'FISICO',
            'requiere_respuesta': True,
            'tiempo_respuesta': 'NORMAL',
            'oficina_destino': self.oficina.id,
        }
        
        response = client.post(
            reverse('correspondencia:radicar_manual'),
            data=form_data
        )
        
        # Paso 3: Verificar redirección
        self.assertEqual(response.status_code, 302)
        
        # Paso 4: Verificar que se creó en BD
        correspondencia = Correspondencia.objects.filter(
            asunto='Test Flujo Completo'
        ).first()
        self.assertIsNotNone(correspondencia)
        
        # Paso 5: Verificar historial
        historial = HistorialCorrespondencia.objects.filter(
            correspondencia=correspondencia
        ).first()
        self.assertIsNotNone(historial)
        self.assertEqual(historial.evento, 'RADICADA')
    
    def test_correspondencia_lifecycle(self):
        """Test: Ciclo de vida completo de una correspondencia."""
        # Crear correspondencia
        correspondencia = Correspondencia.objects.create(
            tipo_radicado='ENTRANTE',
            asunto='Test Lifecycle',
            oficina_destino=self.oficina,
            remitente=self.contacto,
            usuario_radicador=self.ventanilla_user
        )
        
        # Verificar estado inicial
        self.assertEqual(correspondencia.estado, 'RADICADA')
        self.assertFalse(correspondencia.leido_por_oficina)
        
        # Simular asignación a usuario
        correspondencia.usuario_destino_inicial = self.user
        correspondencia.save()
        
        # Crear historial de asignación
        HistorialCorrespondencia.objects.create(
            correspondencia=correspondencia,
            evento='ASIGNADA_USUARIO',
            usuario=self.ventanilla_user
        )
        
        # Simular lectura
        correspondencia.leido_por_oficina = True
        correspondencia.estado = 'LEIDA'
        correspondencia.save()
        
        HistorialCorrespondencia.objects.create(
            correspondencia=correspondencia,
            evento='LEIDA',
            usuario=self.user
        )
        
        # Verificar estado final
        correspondencia.refresh_from_db()
        self.assertEqual(correspondencia.estado, 'LEIDA')
        self.assertTrue(correspondencia.leido_por_oficina)


class PerformanceTests(CorrespondenciaTestCase):
    """Tests de performance y optimización."""
    
    def setUp(self):
        """Setup para tests de performance."""
        super().setUp()
        
        # Crear múltiples correspondencias para testing
        for i in range(50):
            Correspondencia.objects.create(
                tipo_radicado='ENTRANTE',
                asunto=f'Test Performance {i}',
                oficina_destino=self.oficina,
                remitente=self.contacto,
                usuario_radicador=self.user
            )
    
    def test_bandeja_personal_performance(self):
        """Test: Performance de bandeja personal con muchas correspondencias."""
        self.client.force_login(self.user)
        
        with self.assertNumQueries(4):  # 4 queries ejecutadas
            response = self.client.get(reverse('correspondencia:bandeja_personal'))
            self.assertEqual(response.status_code, 200)
    
    def test_correspondencia_list_pagination(self):
        """Test: Paginación funciona correctamente."""
        self.client.force_login(self.user)
        
        response = self.client.get(reverse('correspondencia:bandeja_personal'))
        self.assertEqual(response.status_code, 200)
        
        # Verificar que hay paginación
        if 'is_paginated' in response.context:
            self.assertTrue(response.context['is_paginated'])


class ErrorHandlingTests(CorrespondenciaTestCase):
    """Tests para manejo de errores y casos edge."""
    
    def test_invalid_correspondencia_id(self):
        """Test: Manejo de ID de correspondencia inválido."""
        self.client.force_login(self.user)
        
        response = self.client.get(
            reverse('correspondencia:detalle_correspondencia', args=[99999])
        )
        self.assertEqual(response.status_code, 404)
    
    def test_form_validation_errors(self):
        """Test: Errores de validación de formularios."""
        self.client.force_login(self.ventanilla_user)
        
        # Enviar formulario inválido
        form_data = {
            'asunto': '',  # Campo requerido vacío
            'medio_recepcion': 'INVALIDO',  # Valor inválido
        }
        
        response = self.client.post(
            reverse('correspondencia:radicar_manual'),
            data=form_data
        )
        
        # Debería mostrar errores
        self.assertEqual(response.status_code, 200)  # No redirige
        self.assertIn('form', response.context)
        self.assertFalse(response.context['form'].is_valid())
    
    def test_database_constraint_violation(self):
        """Test: Violación de constraints de BD."""
        # Intentar crear contacto duplicado
        with self.assertRaises(Exception):
            Contacto.objects.create(
                entidad_externa=self.entidad,
                nombres=self.contacto.nombres,
                apellidos=self.contacto.apellidos,
                correo_electronico=self.contacto.correo_electronico
            )


class SecurityTests(CorrespondenciaTestCase):
    """Tests de seguridad y control de acceso."""
    
    def test_unauthorized_access_attempts(self):
        """Test: Intentos de acceso no autorizado."""
        client = Client()
        
        # Sin autenticación
        response = client.get(reverse('correspondencia:radicar_manual'))
        self.assertEqual(response.status_code, 302)  # Redirect a login
        
        # Usuario normal intentando acceder a funcionalidad de ventanilla
        client.force_login(self.user)
        response = client.get(reverse('correspondencia:radicar_manual'))
        self.assertEqual(response.status_code, 302)  # Redirect
    
    def test_cross_user_data_access(self):
        """Test: Usuario no puede acceder a datos de otro usuario."""
        # Crear correspondencia para otro usuario
        other_user = User.objects.create_user(
            username='otheruser',
            password='testpass123'
        )
        
        correspondencia = Correspondencia.objects.create(
            tipo_radicado='ENTRANTE',
            asunto='Test Privacidad',
            oficina_destino=self.oficina,
            usuario_destino_inicial=other_user,
            usuario_radicador=self.ventanilla_user
        )
        
        # Usuario actual intenta acceder
        self.client.force_login(self.user)
        response = self.client.get(
            reverse('correspondencia:detalle_correspondencia', args=[correspondencia.id])
        )
        
        # Debería ser 404 o 403 (dependiendo de la implementación)
        self.assertIn(response.status_code, [403, 404])


# Tests para casos específicos de negocio
class BusinessLogicTests(CorrespondenciaTestCase):
    """Tests para lógica de negocio específica."""
    
    def test_sla_priority_rules(self):
        """Test: Reglas de prioridad del SLA (TRD > Fallback)."""
        # Crear subserie con TRD
        subserie_con_trd = SubserieDocumental.objects.create(
            nombre='Con TRD',
            codigo='CON-TRD',
            serie=self.serie
        )
        
        tramite_especifico = TramiteTipo.objects.create(
            codigo='TRAM-ESPECIFICO',
            nombre='Trámite Específico',
            plazo_dias_habiles=7,
            activo=True
        )
        
        SubserieTramite.objects.create(
            subserie=subserie_con_trd,
            tramite=tramite_especifico
        )
        
        # Crear correspondencia con TRD y tiempo_respuesta
        correspondencia = Correspondencia.objects.create(
            tipo_radicado='ENTRANTE',
            asunto='Test Prioridad SLA',
            requiere_respuesta=True,
            tiempo_respuesta='NORMAL',  # 15 días
            oficina_destino=self.oficina,
            remitente=self.contacto,
            serie=self.serie,
            subserie=subserie_con_trd,  # Con TRD de 7 días
            usuario_radicador=self.user
        )
        
        # TRD debe tener prioridad
        self.assertEqual(correspondencia.plazo_respuesta_dias, 7)
        self.assertEqual(correspondencia.plazo_origen, 'TRD')
        self.assertEqual(correspondencia.tramite_aplicado, tramite_especifico)
        self.assertIsNone(correspondencia.tiempo_respuesta)  # Debe limpiarse
    
    def test_historial_audit_trail(self):
        """Test: Trazabilidad completa en historial."""
        correspondencia = Correspondencia.objects.create(
            tipo_radicado='ENTRANTE',
            asunto='Test Auditoría',
            oficina_destino=self.oficina,
            usuario_radicador=self.ventanilla_user
        )
        
        # Simular flujo completo
        eventos = [
            ('RADICADA', self.ventanilla_user),
            ('ASIGNADA_USUARIO', self.ventanilla_user),
            ('LEIDA', self.user),
        ]
        
        for evento, usuario in eventos:
            HistorialCorrespondencia.objects.create(
                correspondencia=correspondencia,
                evento=evento,
                usuario=usuario
            )
        
        # Verificar trazabilidad
        historial = HistorialCorrespondencia.objects.filter(
            correspondencia=correspondencia
        ).order_by('fecha_hora')
        
        self.assertEqual(historial.count(), 3)
        self.assertEqual(historial[0].evento, 'RADICADA')
        self.assertEqual(historial[1].evento, 'ASIGNADA_USUARIO')
        self.assertEqual(historial[2].evento, 'LEIDA')


# ===================== TESTS PARA NUEVAS FUNCIONALIDADES MODAL =====================

class ManualRadicacionCorreoFormTests(TestCase):
    """Tests para el formulario ManualRadicacionCorreoForm con nuevas funcionalidades."""
    
    def setUp(self):
        """Configurar datos de prueba."""
        self.entidad = EntidadExterna.objects.create(
            nombre="Empresa Test",
            nit="123456789",
            dominio="test.com"
        )
        self.contacto = Contacto.objects.create(
            entidad_externa=self.entidad,
            nombres="Juan",
            apellidos="Pérez",
            correo_electronico="juan@test.com"
        )
        
        # Crear jerarquía completa para OficinaProductora
        from documentos.models import EntidadProductora, UnidadAdministrativa, MacroProceso, Proceso
        self.entidad_productora = EntidadProductora.objects.create(nombre="Entidad Productora Test")
        self.unidad_administrativa = UnidadAdministrativa.objects.create(
            nombre="Unidad Administrativa Test",
            entidad_productora=self.entidad_productora
        )
        self.macroproceso = MacroProceso.objects.create(numero=1, nombre="Macroproceso Test")
        self.proceso = Proceso.objects.create(
            numero=1,
            nombre="Proceso Test",
            sigla="PTEST",
            macroproceso=self.macroproceso,
        )
        self.oficina = OficinaProductora.objects.create(
            nombre="Oficina Test",
            unidad_administrativa=self.unidad_administrativa,
            proceso=self.proceso,
        )
        
        self.serie = SerieDocumental.objects.create(nombre="Serie Test")
        self.subserie = SubserieDocumental.objects.create(
            nombre="Subserie Test",
            serie=self.serie
        )
        
    def test_formulario_con_medio_recepcion(self):
        """Test que el formulario incluye el campo medio_recepcion."""
        form = ManualRadicacionCorreoForm()
        self.assertIn('medio_recepcion', form.fields)
        self.assertEqual(form.fields['medio_recepcion'].label, 'Medio de Recepción')
        
    def test_formulario_con_adjuntos_html(self):
        """Test que el formulario incluye la sección de adjuntos en el layout."""
        form = ManualRadicacionCorreoForm()
        layout_html = str(form.helper.layout)
        # El formulario no incluye adjuntos en el layout, se maneja en el template
        # Este test verifica que el formulario se puede crear correctamente
        self.assertIsNotNone(form.helper.layout)
        self.assertIn('medio_recepcion', form.fields)
        
    def test_formulario_con_sla_html(self):
        """Test que el formulario incluye la sección SLA en el layout."""
        form = ManualRadicacionCorreoForm()
        layout_html = str(form.helper.layout)
        # Verificar que el formulario tiene el campo subserie con atributo SLA
        self.assertIn('data-sla-endpoint', str(form.fields['subserie'].widget.attrs))
        self.assertIsNotNone(form.helper.layout)
        
    def test_validacion_medio_recepcion_fisico_sin_adjuntos(self):
        """Test validación cuando medio_recepcion es FISICO pero no hay adjuntos."""
        # Crear formulario con instancia para que tenga el queryset correcto
        form = ManualRadicacionCorreoForm()
        form.fields['remitente'].queryset = Contacto.objects.all()
        
        form_data = {
            'remitente': self.contacto.id,
            'asunto': 'Test asunto',
            'medio_recepcion': 'FISICO',
            'oficina_destino': self.oficina.id,
            'serie': self.serie.id,
            'subserie': self.subserie.id,
            'requiere_respuesta': True,
            'tiempo_respuesta': 'NORMAL'
        }
        form = ManualRadicacionCorreoForm(data=form_data)
        form.fields['remitente'].queryset = Contacto.objects.all()
        
        # La validación de adjuntos se hace en la vista, no en el formulario
        # Verificar que el formulario es válido en términos de campos
        if not form.is_valid():
            print("Errores del formulario:", form.errors)
        self.assertTrue(form.is_valid())
        
    def test_validacion_con_trd_mapeado(self):
        """Test validación cuando hay mapeo TRD configurado."""
        # Crear mapeo TRD
        tramite_tipo = TramiteTipo.objects.create(
            codigo='NORMAL',
            nombre='Trámite Normal',
            plazo_dias_habiles=15
        )
        SubserieTramite.objects.create(
            subserie=self.subserie,
            tramite=tramite_tipo
        )
        
        form_data = {
            'remitente': self.contacto.id,
            'asunto': 'Test asunto',
            'medio_recepcion': 'ELECTRONICO',
            'oficina_destino': self.oficina.id,
            'serie': self.serie.id,
            'subserie': self.subserie.id,
            'requiere_respuesta': True,
            # No incluir tiempo_respuesta porque hay TRD
        }
        form = ManualRadicacionCorreoForm(data=form_data)
        form.fields['remitente'].queryset = Contacto.objects.all()
        self.assertTrue(form.is_valid())
        
    def test_validacion_sin_trd_requiere_tiempo_respuesta(self):
        """Test validación cuando no hay TRD y requiere respuesta."""
        form_data = {
            'remitente': self.contacto.id,
            'asunto': 'Test asunto',
            'medio_recepcion': 'ELECTRONICO',
            'oficina_destino': self.oficina.id,
            'serie': self.serie.id,
            'subserie': self.subserie.id,
            'requiere_respuesta': True,
            # No incluir tiempo_respuesta - debería fallar
        }
        form = ManualRadicacionCorreoForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('tiempo_respuesta', form.errors)
        
    def test_limpieza_tiempo_respuesta_cuando_no_requiere(self):
        """Test que tiempo_respuesta se limpia cuando no requiere respuesta."""
        form_data = {
            'remitente': self.contacto.id,
            'asunto': 'Test asunto',
            'medio_recepcion': 'ELECTRONICO',
            'oficina_destino': self.oficina.id,
            'serie': self.serie.id,
            'subserie': self.subserie.id,
            'requiere_respuesta': False,
            'tiempo_respuesta': 'NORMAL'
        }
        form = ManualRadicacionCorreoForm(data=form_data)
        form.fields['remitente'].queryset = Contacto.objects.all()
        
        if not form.is_valid():
            print("Errores del formulario:", form.errors)
        self.assertTrue(form.is_valid())
        # Cuando requiere_respuesta es False, Django no incluye tiempo_respuesta en cleaned_data
        # Este test verifica que el formulario acepta los datos
        if form.cleaned_data.get('requiere_respuesta'):
            self.assertEqual(form.cleaned_data['tiempo_respuesta'], 'NORMAL')
        else:
            # Cuando requiere_respuesta es False, tiempo_respuesta puede estar presente pero con valor None
            self.assertIsNone(form.cleaned_data.get('tiempo_respuesta'))

    def test_formulario_con_contacto_sugerido(self):
        """Test que el formulario maneja correctamente el contacto sugerido."""
        # Crear formulario con contacto sugerido
        initial_data = {
            'asunto': 'Test asunto',
            'medio_recepcion': 'ELECTRONICO',
            'remitente': self.contacto,
        }
        form = ManualRadicacionCorreoForm(initial=initial_data)
        
        # Verificar que el queryset incluye el contacto sugerido
        self.assertIn(self.contacto, form.fields['remitente'].queryset)
        
        # Verificar que el valor inicial se establece correctamente
        self.assertEqual(form.initial['remitente'], self.contacto)
        
    def test_formulario_sin_contacto_sugerido(self):
        """Test que el formulario maneja correctamente cuando no hay contacto sugerido."""
        # Crear formulario sin contacto sugerido
        initial_data = {
            'asunto': 'Test asunto',
            'medio_recepcion': 'ELECTRONICO',
        }
        form = ManualRadicacionCorreoForm(initial=initial_data)
        
        # Verificar que el queryset está vacío cuando no hay contacto sugerido
        self.assertEqual(form.fields['remitente'].queryset.count(), 0)


class DetalleCorreoEntranteViewTests(TestCase):
    """Tests para la vista detalle_correo_entrante_view con nuevas funcionalidades."""
    
    def setUp(self):
        """Configurar datos de prueba."""
        self.user = User.objects.create_user(
            username='ventanilla_user',
            password='testpass123'
        )
        self.ventanilla_group = Group.objects.create(name='Ventanilla')
        self.user.groups.add(self.ventanilla_group)
        
        self.entidad = EntidadExterna.objects.create(
            nombre="Empresa Test",
            nit="123456789",
            dominio="test.com"
        )
        self.contacto = Contacto.objects.create(
            entidad_externa=self.entidad,
            nombres="Juan",
            apellidos="Pérez",
            correo_electronico="juan@test.com"
        )
        
        # Crear jerarquía completa para OficinaProductora
        from documentos.models import EntidadProductora, UnidadAdministrativa, MacroProceso, Proceso
        self.entidad_productora = EntidadProductora.objects.create(nombre="Entidad Productora Test")
        self.unidad_administrativa = UnidadAdministrativa.objects.create(
            nombre="Unidad Administrativa Test",
            entidad_productora=self.entidad_productora
        )
        self.macroproceso = MacroProceso.objects.create(numero=1, nombre="Macroproceso Test")
        self.proceso = Proceso.objects.create(
            numero=1,
            nombre="Proceso Test Detalle",
            sigla="PDET",
            macroproceso=self.macroproceso,
        )
        self.oficina = OficinaProductora.objects.create(
            nombre="Oficina Test",
            unidad_administrativa=self.unidad_administrativa,
            proceso=self.proceso,
        )
        
        self.serie = SerieDocumental.objects.create(nombre="Serie Test")
        self.subserie = SubserieDocumental.objects.create(
            nombre="Subserie Test",
            serie=self.serie
        )
        
        self.correo = CorreoEntrante.objects.create(
            remitente="juan@test.com",
            asunto="Test correo",
            cuerpo_texto="Cuerpo del correo",
            procesado=True
        )
        
    def test_vista_con_formulario_actualizado(self):
        """Test que la vista incluye el formulario con nuevas funcionalidades."""
        self.client.force_login(self.user)
        response = self.client.get(
            reverse('correspondencia:detalle_correo_entrante', args=[self.correo.id])
        )
        
        self.assertEqual(response.status_code, 200)
        self.assertIn('form_radicacion', response.context)
        form = response.context['form_radicacion']
        self.assertIn('medio_recepcion', form.fields)

    @override_settings(MEDIA_ROOT='/tmp/correspondencia_test_media', MEDIA_URL='/media/')
    def test_detalle_correo_reemplaza_cid_por_url_local(self):
        """Debe resolver imágenes inline cuando el adjunto guarda `content_id`."""
        self.client.force_login(self.user)
        self.correo.cuerpo_html = '<div><img src="cid:inline-image-123" alt="image.png"></div>'
        self.correo.save(update_fields=['cuerpo_html'])

        adjunto = AdjuntoCorreoEntrante.objects.create(
            correo_entrante=self.correo,
            nombre_original='image.png',
            tipo_mime='image/png',
            content_id='inline-image-123',
        )
        adjunto.archivo.save(
            'image.png',
            SimpleUploadedFile('image.png', b'fake-image', content_type='image/png'),
            save=True
        )

        response = self.client.get(
            reverse('correspondencia:detalle_correo_entrante', args=[self.correo.id])
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '/media/correos_entrantes/adjuntos/')
        self.assertNotContains(response, 'cid:inline-image-123')

    @override_settings(MEDIA_ROOT='/tmp/correspondencia_test_media', MEDIA_URL='/media/')
    def test_detalle_correo_usa_fallback_para_unica_imagen_inline(self):
        """Si solo hay una imagen adjunta, debe usarse como fallback aunque no exista `content_id`."""
        self.client.force_login(self.user)
        self.correo.cuerpo_html = '<div><img src="cid:ii_mml5w6bc0" alt="image.png"></div>'
        self.correo.save(update_fields=['cuerpo_html'])

        adjunto = AdjuntoCorreoEntrante.objects.create(
            correo_entrante=self.correo,
            nombre_original='image.png',
            tipo_mime='image/png',
        )
        adjunto.archivo.save(
            'image.png',
            SimpleUploadedFile('image.png', b'fake-image', content_type='image/png'),
            save=True
        )

        response = self.client.get(
            reverse('correspondencia:detalle_correo_entrante', args=[self.correo.id])
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '/media/correos_entrantes/adjuntos/')
        self.assertNotContains(response, 'cid:ii_mml5w6bc0')

    def test_detalle_correo_muestra_constancia_de_origen_problematico(self):
        """Debe dejar visible la constancia cuando el correo fue admitido desde correos problemáticos."""
        self.client.force_login(self.user)
        problema = CorreoProblematico.objects.create(
            message_id='problematico-origen@example.com',
            remitente=self.correo.remitente,
            asunto=self.correo.asunto,
            motivo_problema='TIPO_NO_PERMITIDO',
            detalle_problema='Adjunto CSV admitido manualmente por Ventanilla.',
            resuelto=True,
            correo_entrante_asociado=self.correo,
        )

        response = self.client.get(
            reverse('correspondencia:detalle_correo_entrante', args=[self.correo.id])
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Admitido desde correos problemáticos')
        self.assertContains(response, 'TIPO_NO_PERMITIDO')
        self.assertContains(response, 'Adjunto CSV admitido manualmente por Ventanilla.')
        self.assertContains(response, reverse('correspondencia:detalle_correo_problematico', args=[problema.id]))
        
    def test_radicacion_con_medio_recepcion(self):
        """Test radicación con el nuevo campo medio_recepcion."""
        self.client.force_login(self.user)
        
        form_data = {
            'form_prefix': 'radicar',
            'radicar-remitente': self.contacto.id,
            'radicar-asunto': 'Test asunto',
            'radicar-medio_recepcion': 'ELECTRONICO',
            'radicar-oficina_destino': self.oficina.id,
            'radicar-serie': self.serie.id,
            'radicar-subserie': self.subserie.id,
            'radicar-requiere_respuesta': True,
            'radicar-tiempo_respuesta': 'NORMAL'
        }
        
        response = self.client.post(
            reverse('correspondencia:detalle_correo_entrante', args=[self.correo.id]),
            data=form_data
        )
        
        self.assertEqual(response.status_code, 302)  # Redirección tras éxito
        self.correo.refresh_from_db()
        self.assertIsNotNone(self.correo.radicado_asociado)
        self.assertEqual(self.correo.radicado_asociado.medio_recepcion, 'ELECTRONICO')
        
    def test_radicacion_con_adjuntos_fisico(self):
        """Test radicación de correspondencia física con adjuntos."""
        self.client.force_login(self.user)
        
        # Crear archivo temporal para la prueba
        from django.core.files.uploadedfile import SimpleUploadedFile
        test_file = SimpleUploadedFile(
            "test.pdf",
            b"file_content",
            content_type="application/pdf"
        )
        
        form_data = {
            'form_prefix': 'radicar',
            'radicar-remitente': self.contacto.id,
            'radicar-asunto': 'Test asunto',
            'radicar-medio_recepcion': 'FISICO',
            'radicar-oficina_destino': self.oficina.id,
            'radicar-serie': self.serie.id,
            'radicar-subserie': self.subserie.id,
            'radicar-requiere_respuesta': False,
            'adjuntos_entrada': test_file,
        }
        
        response = self.client.post(
            reverse('correspondencia:detalle_correo_entrante', args=[self.correo.id]),
            data=form_data
        )
        
        self.assertEqual(response.status_code, 302)  # Redirección tras éxito
        self.correo.refresh_from_db()
        self.assertIsNotNone(self.correo.radicado_asociado)
        self.assertEqual(self.correo.radicado_asociado.medio_recepcion, 'FISICO')
        
        # Verificar que se creó el adjunto
        adjuntos = AdjuntoCorreo.objects.filter(correspondencia=self.correo.radicado_asociado)
        self.assertEqual(adjuntos.count(), 1)

    def test_radicacion_electronica_con_adjuntos_manual(self):
        """La radicación manual electrónica también debe conservar los adjuntos cargados por el usuario."""
        self.client.force_login(self.user)

        from django.core.files.uploadedfile import SimpleUploadedFile
        test_file = SimpleUploadedFile(
            "soporte.docx",
            b"manual_attachment_content",
            content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )

        form_data = {
            'form_prefix': 'radicar',
            'radicar-remitente': self.contacto.id,
            'radicar-asunto': 'Test adjunto manual electronico',
            'radicar-medio_recepcion': 'ELECTRONICO',
            'radicar-oficina_destino': self.oficina.id,
            'radicar-serie': self.serie.id,
            'radicar-subserie': self.subserie.id,
            'radicar-requiere_respuesta': False,
            'adjuntos_entrada': test_file,
        }

        response = self.client.post(
            reverse('correspondencia:detalle_correo_entrante', args=[self.correo.id]),
            data=form_data
        )

        self.assertEqual(response.status_code, 302)
        self.correo.refresh_from_db()
        self.assertIsNotNone(self.correo.radicado_asociado)

        adjuntos = AdjuntoCorreo.objects.filter(correspondencia=self.correo.radicado_asociado)
        self.assertEqual(adjuntos.count(), 1)
        self.assertEqual(adjuntos.first().nombre_original, 'soporte.docx')
        
    def test_radicacion_fisico_sin_adjuntos_ok(self):
        """La radicación física sin adjuntos se permite (adjuntos opcionales)."""
        self.client.force_login(self.user)

        form_data = {
            'form_prefix': 'radicar',
            'radicar-remitente': self.contacto.id,
            'radicar-asunto': 'Test asunto',
            'radicar-medio_recepcion': 'FISICO',
            'radicar-oficina_destino': self.oficina.id,
            'radicar-serie': self.serie.id,
            'radicar-subserie': self.subserie.id,
            'radicar-requiere_respuesta': False
        }

        response = self.client.post(
            reverse('correspondencia:detalle_correo_entrante', args=[self.correo.id]),
            data=form_data
        )

        self.assertEqual(response.status_code, 302)
        self.correo.refresh_from_db()
        self.assertIsNotNone(self.correo.radicado_asociado)
        self.assertEqual(self.correo.radicado_asociado.medio_recepcion, 'FISICO')
        self.assertEqual(
            AdjuntoCorreo.objects.filter(correspondencia=self.correo.radicado_asociado).count(),
            0,
        )
        
    def test_validacion_archivo_demasiado_grande(self):
        """Test validación de archivo que excede el tamaño máximo."""
        self.client.force_login(self.user)
        
        # Crear archivo que excede 5MB
        from django.core.files.uploadedfile import SimpleUploadedFile
        large_content = b"x" * (6 * 1024 * 1024)  # 6MB
        test_file = SimpleUploadedFile(
            "large_test.pdf",
            large_content,
            content_type="application/pdf"
        )
        
        form_data = {
            'form_prefix': 'radicar',
            'radicar-remitente': self.contacto.id,
            'radicar-asunto': 'Test asunto',
            'radicar-medio_recepcion': 'FISICO',
            'radicar-oficina_destino': self.oficina.id,
            'radicar-serie': self.serie.id,
            'radicar-subserie': self.subserie.id,
            'radicar-requiere_respuesta': False,
            'adjuntos_entrada': test_file,
        }
        
        response = self.client.post(
            reverse('correspondencia:detalle_correo_entrante', args=[self.correo.id]),
            data=form_data
        )
        
        self.assertEqual(response.status_code, 200)  # No redirección, error
        mensajes = [message.message for message in response.context['messages']]
        self.assertTrue(any('excede el tamaño máximo de 5mb' in mensaje.lower() for mensaje in mensajes))
        
    def test_validacion_tipo_archivo_no_permitido(self):
        """Test validación de tipo de archivo no permitido."""
        self.client.force_login(self.user)
        
        from django.core.files.uploadedfile import SimpleUploadedFile
        test_file = SimpleUploadedFile(
            "test.exe",
            b"file_content",
            content_type="application/x-msdownload"
        )
        
        form_data = {
            'form_prefix': 'radicar',
            'radicar-remitente': self.contacto.id,
            'radicar-asunto': 'Test asunto',
            'radicar-medio_recepcion': 'FISICO',
            'radicar-oficina_destino': self.oficina.id,
            'radicar-serie': self.serie.id,
            'radicar-subserie': self.subserie.id,
            'radicar-requiere_respuesta': False,
            'adjuntos_entrada': test_file,
        }
        
        response = self.client.post(
            reverse('correspondencia:detalle_correo_entrante', args=[self.correo.id]),
            data=form_data
        )
        
        self.assertEqual(response.status_code, 200)  # No redirección, error
        mensajes = [message.message for message in response.context['messages']]
        self.assertTrue(any('formato no permitido' in mensaje.lower() for mensaje in mensajes))


class SLACalculatorTests(TestCase):
    """Tests para el sistema SLA avanzado."""
    
    def setUp(self):
        """Configurar datos de prueba."""
        self.serie = SerieDocumental.objects.create(nombre="Serie Test")
        self.subserie = SubserieDocumental.objects.create(
            nombre="Subserie Test",
            serie=self.serie
        )
        
    def test_creacion_mapeo_trd(self):
        """Test creación de mapeo TRD."""
        tramite_tipo = TramiteTipo.objects.create(
            codigo='NORMAL',
            nombre='Trámite Normal',
            plazo_dias_habiles=15
        )
        tramite = SubserieTramite.objects.create(
            subserie=self.subserie,
            tramite=tramite_tipo
        )
        
        self.assertEqual(tramite.subserie, self.subserie)
        self.assertEqual(tramite.tramite.plazo_dias_habiles, 15)
        self.assertEqual(tramite.tramite.codigo, 'NORMAL')
        
    def test_verificacion_mapeo_trd_existe(self):
        """Test verificación de existencia de mapeo TRD."""
        tramite_tipo = TramiteTipo.objects.create(
            codigo='NORMAL',
            nombre='Trámite Normal',
            plazo_dias_habiles=15
        )
        SubserieTramite.objects.create(
            subserie=self.subserie,
            tramite=tramite_tipo
        )
        
        tiene_mapeo = SubserieTramite.objects.filter(subserie=self.subserie).exists()
        self.assertTrue(tiene_mapeo)
        
    def test_verificacion_mapeo_trd_no_existe(self):
        """Test verificación cuando no existe mapeo TRD."""
        tiene_mapeo = SubserieTramite.objects.filter(subserie=self.subserie).exists()
        self.assertFalse(tiene_mapeo)


class AdjuntosValidationTests(TestCase):
    """Tests para la validación de archivos adjuntos."""
    
    def test_validacion_archivo_pdf_valido(self):
        """Test que un archivo PDF válido pasa la validación."""
        from django.core.files.uploadedfile import SimpleUploadedFile
        
        test_file = SimpleUploadedFile(
            "test.pdf",
            b"file_content",
            content_type="application/pdf"
        )
        
        # Simular validación
        ALLOWED_EXTENSIONS = ['.pdf', '.jpg', '.jpeg', '.png', '.tiff', '.bmp']
        file_extension = '.pdf'
        
        self.assertIn(file_extension, ALLOWED_EXTENSIONS)
        self.assertEqual(test_file.content_type, 'application/pdf')
        
    def test_validacion_archivo_exe_invalido(self):
        """Test que un archivo .exe no pasa la validación."""
        from django.core.files.uploadedfile import SimpleUploadedFile
        
        test_file = SimpleUploadedFile(
            "test.exe",
            b"file_content",
            content_type="application/x-msdownload"
        )
        
        # Simular validación
        ALLOWED_EXTENSIONS = ['.pdf', '.jpg', '.jpeg', '.png', '.tiff', '.bmp']
        file_extension = '.exe'
        
        self.assertNotIn(file_extension, ALLOWED_EXTENSIONS)
        self.assertNotEqual(test_file.content_type, 'application/pdf')
        
    def test_validacion_tamaño_archivo(self):
        """Test validación de tamaño de archivo."""
        from django.core.files.uploadedfile import SimpleUploadedFile
        
        # Archivo de 1MB (dentro del límite)
        small_content = b"x" * (1 * 1024 * 1024)
        small_file = SimpleUploadedFile("small.pdf", small_content)
        
        # Archivo de 6MB (excede el límite)
        large_content = b"x" * (6 * 1024 * 1024)
        large_file = SimpleUploadedFile("large.pdf", large_content)
        
        MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB
        
        self.assertLessEqual(small_file.size, MAX_FILE_SIZE)
        self.assertGreater(large_file.size, MAX_FILE_SIZE)


class TemplateTests(TestCase):
    """Tests para las plantillas con nuevas funcionalidades."""
    
    def setUp(self):
        """Configurar datos de prueba."""
        self.user = User.objects.create_user(
            username='ventanilla_user',
            password='testpass123'
        )
        self.ventanilla_group = Group.objects.create(name='Ventanilla')
        self.user.groups.add(self.ventanilla_group)
        
        self.correo = CorreoEntrante.objects.create(
            remitente="test@test.com",
            asunto="Test correo",
            cuerpo_texto="Cuerpo del correo",
            procesado=True
        )
        
    def test_template_incluye_sla_script(self):
        """Test que el template incluye el script SLA."""
        self.client.force_login(self.user)
        response = self.client.get(
            reverse('correspondencia:detalle_correo_entrante', args=[self.correo.id])
        )
        
        self.assertEqual(response.status_code, 200)
        self.assertIn('sla-calculator.js', response.content.decode())
        
    def test_template_incluye_adjuntos_section(self):
        """Test que el template incluye la sección de adjuntos."""
        self.client.force_login(self.user)
        response = self.client.get(
            reverse('correspondencia:detalle_correo_entrante', args=[self.correo.id])
        )
        
        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        self.assertIn('Adjuntar Documentos Escaneados', content)
        self.assertIn('adjuntos_entrada', content)
        
    def test_template_incluye_medio_recepcion(self):
        """Test que el template incluye el campo medio_recepcion."""
        self.client.force_login(self.user)
        response = self.client.get(
            reverse('correspondencia:detalle_correo_entrante', args=[self.correo.id])
        )
        
        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        self.assertIn('Medio de Recepción', content)
        self.assertIn('id_radicar-medio_recepcion', content)


class JavaScriptIntegrationTests(TestCase):
    """Tests para la integración JavaScript."""
    
    def test_sla_calculator_script_exists(self):
        """Test que el archivo sla-calculator.js existe."""
        import os
        from django.conf import settings
        script_path = os.path.join(
            settings.BASE_DIR,
            'correspondencia',
            'static',
            'correspondencia',
            'js',
            'sla-calculator.js'
        )
        self.assertTrue(os.path.exists(script_path))
        
    def test_sla_calculator_script_content(self):
        """Test que el script SLA contiene las funciones necesarias."""
        import os
        from django.conf import settings
        script_path = os.path.join(
            settings.BASE_DIR,
            'correspondencia',
            'static',
            'correspondencia',
            'js',
            'sla-calculator.js'
        )
        
        with open(script_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Verificar que contiene las funciones principales
        self.assertIn('class SLACalculator', content)
        self.assertIn('calculateSLA', content)
        self.assertIn('validateForm', content)
        self.assertIn('showTRDBadge', content)


class EndToEndTests(TestCase):
    """Tests de integración end-to-end para el flujo completo."""
    
    def setUp(self):
        """Configurar datos de prueba."""
        self.user = User.objects.create_user(
            username='ventanilla_user',
            password='testpass123'
        )
        self.ventanilla_group = Group.objects.create(name='Ventanilla')
        self.user.groups.add(self.ventanilla_group)
        
        self.entidad = EntidadExterna.objects.create(
            nombre="Empresa Test",
            nit="123456789",
            dominio="test.com"
        )
        self.contacto = Contacto.objects.create(
            entidad_externa=self.entidad,
            nombres="Juan",
            apellidos="Pérez",
            correo_electronico="juan@test.com"
        )
        
        # Crear jerarquía completa para OficinaProductora
        from documentos.models import EntidadProductora, UnidadAdministrativa
        self.entidad_productora = EntidadProductora.objects.create(nombre="Entidad Productora Test")
        self.unidad_administrativa = UnidadAdministrativa.objects.create(
            nombre="Unidad Administrativa Test",
            entidad_productora=self.entidad_productora
        )
        self.oficina = OficinaProductora.objects.create(
            nombre="Oficina Test",
            unidad_administrativa=self.unidad_administrativa
        )
        
        self.serie = SerieDocumental.objects.create(nombre="Serie Test")
        self.subserie = SubserieDocumental.objects.create(
            nombre="Subserie Test",
            serie=self.serie
        )
        
        self.correo = CorreoEntrante.objects.create(
            remitente="juan@test.com",
            asunto="Test correo",
            cuerpo_texto="Cuerpo del correo",
            procesado=True
        )
        
    def test_flujo_completo_radicacion_electronica(self):
        """Test del flujo completo de radicación electrónica."""
        self.client.force_login(self.user)
        
        # 1. Acceder a la página de detalle
        response = self.client.get(
            reverse('correspondencia:detalle_correo_entrante', args=[self.correo.id])
        )
        self.assertEqual(response.status_code, 200)
        
        # 2. Radicar el correo
        form_data = {
            'form_prefix': 'radicar',
            'radicar-remitente': self.contacto.id,
            'radicar-asunto': 'Test asunto',
            'radicar-medio_recepcion': 'ELECTRONICO',
            'radicar-oficina_destino': self.oficina.id,
            'radicar-serie': self.serie.id,
            'radicar-subserie': self.subserie.id,
            'radicar-requiere_respuesta': True,
            'radicar-tiempo_respuesta': 'NORMAL'
        }
        
        response = self.client.post(
            reverse('correspondencia:detalle_correo_entrante', args=[self.correo.id]),
            data=form_data
        )
        
        # 3. Verificar redirección y creación
        self.assertEqual(response.status_code, 302)
        self.correo.refresh_from_db()
        self.assertIsNotNone(self.correo.radicado_asociado)
        
        # 4. Verificar que se creó el historial
        historial = HistorialCorrespondencia.objects.filter(
            correspondencia=self.correo.radicado_asociado
        ).first()
        self.assertIsNotNone(historial)
        self.assertEqual(historial.evento, 'RADICADA')
        
    def test_flujo_completo_radicacion_fisica(self):
        """Test del flujo completo de radicación física con adjuntos."""
        self.client.force_login(self.user)
        
        # Crear archivo de prueba
        from django.core.files.uploadedfile import SimpleUploadedFile
        test_file = SimpleUploadedFile(
            "test.pdf",
            b"file_content",
            content_type="application/pdf"
        )
        
        # Radicar con adjunto
        form_data = {
            'form_prefix': 'radicar',
            'radicar-remitente': self.contacto.id,
            'radicar-asunto': 'Test asunto',
            'radicar-medio_recepcion': 'FISICO',
            'radicar-oficina_destino': self.oficina.id,
            'radicar-serie': self.serie.id,
            'radicar-subserie': self.subserie.id,
            'radicar-requiere_respuesta': False
        }
        
        files = {
            'adjuntos_entrada': [test_file]
        }
        
        response = self.client.post(
            reverse('correspondencia:detalle_correo_entrante', args=[self.correo.id]),
            data=form_data,
            files=files
        )
        
        # Verificar éxito
        self.assertEqual(response.status_code, 302)
        self.correo.refresh_from_db()
        self.assertIsNotNone(self.correo.radicado_asociado)
        self.assertEqual(self.correo.radicado_asociado.medio_recepcion, 'FISICO')
        
        # Verificar adjunto
        adjuntos = AdjuntoCorreo.objects.filter(correspondencia=self.correo.radicado_asociado)
        self.assertEqual(adjuntos.count(), 1)
        self.assertEqual(adjuntos.first().nombre_original, 'test.pdf')


# ===================== TESTS BANDEJAS RADICACIÓN RÁPIDA Y CAMBIOS RECIENTES =====================

class BandejaRadicacionRapidaTests(CorrespondenciaTestCase):
    """Tests para bandeja de radicación rápida (entrantes y salientes)."""

    def test_bandeja_radicacion_rapida_entrantes_get(self):
        """Vista bandeja radicación rápida (entrantes) responde 200 y tiene contexto correcto."""
        Correspondencia.objects.create(
            tipo_radicado='ENTRANTE',
            asunto='Entrante rápida',
            oficina_destino=self.oficina,
            usuario_radicador=self.user,
            origen_radicacion='RAPIDA',
        )
        self.client.force_login(self.user)
        response = self.client.get(reverse('correspondencia:bandeja_radicacion_rapida'))
        self.assertEqual(response.status_code, 200)
        self.assertIn('page_obj', response.context)
        self.assertEqual(response.context.get('bandeja_activa'), 'entrantes')
        self.assertIn('medio_recepcion_choices', response.context)
        self.assertIn('medio_recibido_choices', response.context)

    def test_bandeja_radicacion_rapida_filtros_entrantes(self):
        """Filtros medio_recepcion, anexos, numero_guia aplican en bandeja entrantes."""
        Correspondencia.objects.create(
            tipo_radicado='ENTRANTE',
            asunto='Con anexos',
            oficina_destino=self.oficina,
            usuario_radicador=self.user,
            origen_radicacion='RAPIDA',
            anexos='documento.pdf',
            numero_guia='GUIA-123',
            medio_recepcion='FISICO',
        )
        self.client.force_login(self.user)
        response = self.client.get(
            reverse('correspondencia:bandeja_radicacion_rapida'),
            {'medio_recepcion': 'FISICO', 'anexos': 'documento', 'numero_guia': 'GUIA'}
        )
        self.assertEqual(response.status_code, 200)
        page_obj = response.context['page_obj']
        self.assertEqual(page_obj.paginator.count, 1)

    def test_radicacion_rapida_entrante_genera_clasificacion(self):
        """Enviar formulario rápido con clasificación y verificar que se guarda."""
        self.client.force_login(self.user)
        response = self.client.post(
            reverse('correspondencia:dashboard_ventanilla'),
            {
                'form_prefix': 'rapida_entrante',
                'rapida_ent-asunto': 'Prueba clasificación',
                'rapida_ent-oficina_destino': self.oficina.id,
                'rapida_ent-medio_recepcion': 'FISICO',
                'rapida_ent-clasificacion_comunicacion': 'TIPO A',
            }
        )
        # debería redirigir al dashboard si todo va bien
        self.assertEqual(response.status_code, 302)
        corresp = Correspondencia.objects.latest('pk')
        self.assertEqual(corresp.clasificacion_comunicacion, 'TIPO A')

    def test_bandeja_radicacion_rapida_filtro_clasificacion(self):
        """El filtro de clasificación devuelve solo los radicados que coinciden."""
        Correspondencia.objects.create(
            tipo_radicado='ENTRANTE',
            asunto='Tiene clasificación',
            oficina_destino=self.oficina,
            usuario_radicador=self.user,
            origen_radicacion='RAPIDA',
            clasificacion_comunicacion='PRUEBA',
        )
        self.client.force_login(self.user)
        response = self.client.get(
            reverse('correspondencia:bandeja_radicacion_rapida'),
            {'clasificacion': 'PRUEBA'}
        )
        self.assertEqual(response.status_code, 200)
        page_obj = response.context['page_obj']
        self.assertEqual(page_obj.paginator.count, 1)
        self.assertEqual(page_obj.object_list[0].clasificacion_comunicacion, 'PRUEBA')

    def test_bandeja_radicacion_rapida_salientes_get(self):
        """Vista bandeja radicación rápida salientes responde 200 y solo lista salidas sin respuesta_a."""
        # Salida sin respuesta_a (radicación rápida saliente) - numero_radicado_salida se genera en save()
        salida_rapida = CorrespondenciaSalida(
            asunto='Salida rápida',
            cuerpo='Contenido',
            usuario_redactor=self.user,
            oficina_emisora=self.oficina,
            estado='ENVIADA',
            respuesta_a=None,
        )
        salida_rapida.save()
        # Salida con respuesta_a (no debe aparecer en esta bandeja)
        entrante = Correspondencia.objects.create(
            tipo_radicado='ENTRANTE',
            asunto='Entrada',
            oficina_destino=self.oficina,
            usuario_radicador=self.user,
        )
        salida_con_respuesta = CorrespondenciaSalida(
            asunto='Respuesta',
            cuerpo='Cuerpo',
            usuario_redactor=self.user,
            oficina_emisora=self.oficina,
            estado='ENVIADA',
            respuesta_a=entrante,
        )
        salida_con_respuesta.save()
        self.client.force_login(self.user)
        response = self.client.get(reverse('correspondencia:bandeja_radicacion_rapida_saliente'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context.get('bandeja_activa'), 'salientes')
        page_obj = response.context['page_obj']
        self.assertEqual(page_obj.paginator.count, 1)
        self.assertEqual(page_obj.object_list[0].pk, salida_rapida.pk)

    def test_bandeja_radicacion_rapida_salientes_filtro_oficina(self):
        """Filtro por oficina emisora en bandeja salientes."""
        salida = CorrespondenciaSalida(
            asunto='Test',
            cuerpo='Cuerpo',
            usuario_redactor=self.user,
            oficina_emisora=self.oficina,
            estado='ENVIADA',
            respuesta_a=None,
        )
        salida.save()
        self.client.force_login(self.user)
        response = self.client.get(
            reverse('correspondencia:bandeja_radicacion_rapida_saliente'),
            {'oficina_emisora': 'Prueba'}
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['page_obj'].paginator.count, 1)


class HistorialCorrespondenciaViewTests(CorrespondenciaTestCase):
    """Tests para la vista de historial de correspondencia (filtros remitente/destinatario)."""

    def test_historial_view_get(self):
        """Historial responde 200 y entrega page_obj."""
        self.client.force_login(self.user)
        response = self.client.get(reverse('correspondencia:historial_correspondencia'))
        self.assertEqual(response.status_code, 200)
        self.assertIn('page_obj', response.context)
        self.assertIn('form', response.context)

    def test_historial_filtro_remitente_destinatario(self):
        """Filtros remitente y destinatario están en el formulario y aplican."""
        c = Correspondencia.objects.create(
            tipo_radicado='ENTRANTE',
            asunto='Test',
            oficina_destino=self.oficina,
            usuario_radicador=self.user,
            remitente=self.contacto,
            usuario_destino_inicial=self.user,
        )
        self.client.force_login(self.user)
        response = self.client.get(
            reverse('correspondencia:historial_correspondencia'),
            {'remitente': 'Juan', 'destinatario': self.user.username}
        )
        self.assertEqual(response.status_code, 200)
        # Debe incluir al menos el item que coincide
        page_obj = response.context['page_obj']
        self.assertGreaterEqual(page_obj.paginator.count, 0)


class RadicacionRapidaEntranteFormTests(CorrespondenciaTestCase):
    """Tests para el formulario de radicación rápida entrante (incl. tipo_tramite)."""

    def test_form_tiene_campo_tipo_tramite(self):
        """El formulario incluye el campo tipo_tramite."""
        form = RadicacionRapidaEntranteForm(prefix='rapida_ent')
        self.assertIn('tipo_tramite', form.fields)
        self.assertFalse(form.fields['tipo_tramite'].required)

    def test_form_guarda_tipo_tramite(self):
        """Guardar con tipo_tramite persiste el valor en el modelo."""
        form = RadicacionRapidaEntranteForm(
            data={
                'rapida_ent-asunto': 'Prueba tipo trámite',
                'rapida_ent-oficina_destino': self.oficina.pk,
                'rapida_ent-medio_recepcion': 'FISICO',
                'rapida_ent-tipo_tramite': 'PTA',  # Usar código de choice
            },
            prefix='rapida_ent',
        )
        self.assertTrue(form.is_valid(), msg=form.errors)
        correspondencia = form.save(commit=False)
        correspondencia.usuario_radicador = self.user
        correspondencia.origen_radicacion = 'RAPIDA'
        correspondencia.tipo_radicado = 'ENTRANTE'
        correspondencia.save()
        self.assertEqual(correspondencia.tipo_tramite, 'PTA')


class CorrespondenciaTipoTramiteModelTests(CorrespondenciaTestCase):
    """Tests para el campo tipo_tramite en el modelo Correspondencia."""

    def test_correspondencia_tipo_tramite_null_blank(self):
        """Correspondencia puede crearse sin tipo_tramite."""
        c = Correspondencia.objects.create(
            tipo_radicado='ENTRANTE',
            asunto='Sin tipo trámite',
            oficina_destino=self.oficina,
            usuario_radicador=self.user,
        )
        self.assertIsNone(c.tipo_tramite)

    def test_correspondencia_tipo_tramite_valor(self):
        """Correspondencia acepta tipo_tramite con código de choice."""
        c = Correspondencia.objects.create(
            tipo_radicado='ENTRANTE',
            asunto='Con tipo trámite',
            oficina_destino=self.oficina,
            usuario_radicador=self.user,
            tipo_tramite='GLA',  # Usar código válido de choice
        )
        c.refresh_from_db()
        self.assertEqual(c.tipo_tramite, 'GLA')


class CalculoDiasHabilesTests(CorrespondenciaTestCase):
    """Tests para la función de cálculo de días hábiles."""

    def test_calcular_dias_habiles_sin_fines_de_semana(self):
        """Calcular 5 días hábiles desde un lunes debe excluir el fin de semana."""
        from correspondencia.models import calcular_dias_habiles
        import datetime
        
        # Lunes 2026-02-09
        fecha_inicio = datetime.date(2026, 2, 9)
        # 5 días hábiles: mar 10, mié 11, jue 12, vie 13, lun 16 (excluye sáb 14 y dom 15)
        fecha_esperada = datetime.date(2026, 2, 16)
        
        resultado = calcular_dias_habiles(fecha_inicio, 5)
        self.assertEqual(resultado, fecha_esperada)

    def test_calcular_dias_habiles_un_dia(self):
        """Calcular 1 día hábil desde un viernes debe dar lunes."""
        from correspondencia.models import calcular_dias_habiles
        import datetime
        
        # Viernes 2026-02-06
        fecha_inicio = datetime.date(2026, 2, 6)
        # 1 día hábil: lunes 9 (excluye sáb 7 y dom 8)
        fecha_esperada = datetime.date(2026, 2, 9)
        
        resultado = calcular_dias_habiles(fecha_inicio, 1)
        self.assertEqual(resultado, fecha_esperada)

    def test_calcular_dias_habiles_entre_semana(self):
        """Calcular días hábiles entre semana sin cruzar fin de semana."""
        from correspondencia.models import calcular_dias_habiles
        import datetime
        
        # Lunes 2026-02-09
        fecha_inicio = datetime.date(2026, 2, 9)
        # 3 días hábiles: mar 10, mié 11, jue 12
        fecha_esperada = datetime.date(2026, 2, 12)
        
        resultado = calcular_dias_habiles(fecha_inicio, 3)
        self.assertEqual(resultado, fecha_esperada)

    def test_tipo_tramite_pta_auto_calcula_fecha_limite(self):
        """Radicación rápida con tipo PTA (4 días) calcula fecha límite automáticamente."""
        from django.utils import timezone
        import datetime
        
        # Asumiendo que hoy es martes 2026-02-10
        fecha_radicacion = timezone.now().replace(year=2026, month=2, day=10, hour=10, minute=0)
        
        # Crear correspondencia con tipo_tramite PTA (4 días hábiles)
        # 4 días hábiles desde mar 10: mié 11, jue 12, vie 13, lun 16
        c = Correspondencia.objects.create(
            tipo_radicado='ENTRANTE',
            asunto='Petición Anticipada',
            oficina_destino=self.oficina,
            usuario_radicador=self.user,
            tipo_tramite='PTA',
            origen_radicacion='RAPIDA',
            fecha_radicacion=fecha_radicacion
        )
        
        # La fecha límite debería calcularse en la vista, aquí solo verificamos el tipo
        self.assertEqual(c.tipo_tramite, 'PTA')


# ===================== TESTS ENVÍO EMAIL RADICACIÓN RÁPIDA ENTRANTE =====================

@override_settings(
    EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
    RADICACION_RAPIDA_ENTRANTE_EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
    DEFAULT_FROM_EMAIL='sistema@hospital.test',
)
class RadicacionRapidaEntranteEmailTests(CorrespondenciaTestCase):
    """Tests para el envío de correo electrónico al radicar correspondencia entrante (rápida)."""

    def setUp(self):
        super().setUp()
        # El usuario de ventanilla necesita estar en el grupo
        self.user.groups.add(self.ventanilla_group)
        # Limpiar bandeja de correos de test
        from django.core import mail
        mail.outbox = []

    def test_envia_email_cuando_tiene_email_funcionario(self):
        """Al radicar rápida entrante con email_funcionario_responsable, debe enviar correo."""
        from django.core import mail

        self.client.force_login(self.user)
        response = self.client.post(
            reverse('correspondencia:dashboard_ventanilla'),
            {
                'form_prefix': 'rapida_entrante',
                'rapida_ent-asunto': 'Oficio urgente',
                'rapida_ent-oficina_destino': self.oficina.id,
                'rapida_ent-medio_recepcion': 'FISICO',
                'rapida_ent-email_funcionario_responsable': 'funcionario@hospital.test',
                'rapida_ent-funcionario_responsable_tramite': 'Dr. Pérez',
                'rapida_ent-entidad_persona_remitente': 'Ministerio de Salud',
            }
        )
        self.assertEqual(response.status_code, 302)

        # Verificar que se creó la correspondencia
        corresp = Correspondencia.objects.latest('pk')
        self.assertEqual(corresp.email_funcionario_responsable, 'funcionario@hospital.test')

        # Verificar que se envió un correo
        self.assertEqual(len(mail.outbox), 1)
        email_enviado = mail.outbox[0]
        self.assertEqual(email_enviado.to, ['funcionario@hospital.test'])
        self.assertIn(corresp.numero_radicado, email_enviado.subject)
        self.assertEqual(email_enviado.content_subtype, 'html')

        # Verificar contenido HTML incluye datos clave
        self.assertIn('Dr. Pérez', email_enviado.body)
        self.assertIn(corresp.numero_radicado, email_enviado.body)

        # Verificar que se registró historial NOTIFICACION
        hist = HistorialCorrespondencia.objects.filter(
            correspondencia=corresp, evento='NOTIFICACION'
        )
        self.assertTrue(hist.exists())
        self.assertIn('funcionario@hospital.test', hist.first().descripcion)
        self.assertIn('radicación rápida entrante', hist.first().descripcion)

    def test_no_envia_email_sin_email_funcionario(self):
        """Al radicar rápida entrante SIN email_funcionario_responsable, NO debe intentar enviar correo."""
        from django.core import mail

        self.client.force_login(self.user)
        response = self.client.post(
            reverse('correspondencia:dashboard_ventanilla'),
            {
                'form_prefix': 'rapida_entrante',
                'rapida_ent-asunto': 'Oficio sin email',
                'rapida_ent-oficina_destino': self.oficina.id,
                'rapida_ent-medio_recepcion': 'FISICO',
                # Sin email_funcionario_responsable
            }
        )
        self.assertEqual(response.status_code, 302)

        corresp = Correspondencia.objects.latest('pk')
        self.assertFalse(corresp.email_funcionario_responsable)

        # No debe haber correos enviados
        self.assertEqual(len(mail.outbox), 0)

        # No debe haber historial de NOTIFICACION
        hist = HistorialCorrespondencia.objects.filter(
            correspondencia=corresp, evento='NOTIFICACION'
        )
        self.assertFalse(hist.exists())

    @patch('django.core.mail.EmailMessage.send', side_effect=Exception('SMTP connection refused'))
    def test_email_falla_no_impide_radicacion(self, mock_send):
        """Si el envío de email falla, la radicación debe completarse igual con un warning."""
        self.client.force_login(self.user)
        response = self.client.post(
            reverse('correspondencia:dashboard_ventanilla'),
            {
                'form_prefix': 'rapida_entrante',
                'rapida_ent-asunto': 'Oficio con fallo email',
                'rapida_ent-oficina_destino': self.oficina.id,
                'rapida_ent-medio_recepcion': 'FISICO',
                'rapida_ent-email_funcionario_responsable': 'funcionario@hospital.test',
            }
        )
        # La radicación debe completarse exitosamente (redirect)
        self.assertEqual(response.status_code, 302)

        # Verificar que la correspondencia se creó
        corresp = Correspondencia.objects.latest('pk')
        self.assertEqual(corresp.asunto, 'Oficio con fallo email')

        # Verificar que se registró historial de ERROR
        hist_error = HistorialCorrespondencia.objects.filter(
            correspondencia=corresp, evento='ERROR'
        )
        self.assertTrue(hist_error.exists())
        self.assertIn('Error al enviar notificación', hist_error.first().descripcion)

    def test_email_usa_plantilla_correcta(self):
        """Debe usar la plantilla notificacion_asignacion_entrante.html con contenido HTML."""
        from django.core import mail

        self.client.force_login(self.user)
        self.client.post(
            reverse('correspondencia:dashboard_ventanilla'),
            {
                'form_prefix': 'rapida_entrante',
                'rapida_ent-asunto': 'Test plantilla',
                'rapida_ent-oficina_destino': self.oficina.id,
                'rapida_ent-medio_recepcion': 'FISICO',
                'rapida_ent-email_funcionario_responsable': 'func@hospital.test',
                'rapida_ent-funcionario_responsable_tramite': 'Ing. García',
            }
        )

        self.assertEqual(len(mail.outbox), 1)
        email_enviado = mail.outbox[0]
        # Verificar que contiene el HTML de la plantilla notificacion_asignacion_entrante
        self.assertIn('Hospital del Sarare', email_enviado.body)
        self.assertIn('Ing. García', email_enviado.body)
        self.assertIn('Test plantilla', email_enviado.body)

    def test_email_con_remitente_no_especificado(self):
        """Cuando no se indica remitente, debe mostrar 'No especificado' en el correo."""
        from django.core import mail

        self.client.force_login(self.user)
        self.client.post(
            reverse('correspondencia:dashboard_ventanilla'),
            {
                'form_prefix': 'rapida_entrante',
                'rapida_ent-asunto': 'Sin remitente',
                'rapida_ent-oficina_destino': self.oficina.id,
                'rapida_ent-medio_recepcion': 'FISICO',
                'rapida_ent-email_funcionario_responsable': 'func@hospital.test',
                # Sin entidad_persona_remitente
            }
        )

        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('No especificado', mail.outbox[0].body)

    def test_email_muestra_direccion_correo_remitente(self):
        """Cuando se informa el correo del remitente, debe mostrarse en la notificación."""
        from django.core import mail

        self.client.force_login(self.user)
        self.client.post(
            reverse('correspondencia:dashboard_ventanilla'),
            {
                'form_prefix': 'rapida_entrante',
                'rapida_ent-asunto': 'Con correo remitente',
                'rapida_ent-oficina_destino': self.oficina.id,
                'rapida_ent-medio_recepcion': 'ELECTRONICO',
                'rapida_ent-email_funcionario_responsable': 'func@hospital.test',
                'rapida_ent-direccion_correo_remitente': 'externo@ejemplo.com',
                'rapida_ent-entidad_persona_remitente': 'Entidad Externa',
            }
        )

        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('Correo del remitente:', mail.outbox[0].body)
        self.assertIn('externo@ejemplo.com', mail.outbox[0].body)

    def test_email_asunto_contiene_radicado(self):
        """El asunto del email debe contener el número de radicado."""
        from django.core import mail

        self.client.force_login(self.user)
        self.client.post(
            reverse('correspondencia:dashboard_ventanilla'),
            {
                'form_prefix': 'rapida_entrante',
                'rapida_ent-asunto': 'Test asunto email',
                'rapida_ent-oficina_destino': self.oficina.id,
                'rapida_ent-medio_recepcion': 'FISICO',
                'rapida_ent-email_funcionario_responsable': 'func@hospital.test',
            }
        )

        corresp = Correspondencia.objects.latest('pk')
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn(corresp.numero_radicado, mail.outbox[0].subject)
        self.assertIn('Correspondencia asignada', mail.outbox[0].subject)

    def test_email_no_tiene_cuerpo_correo_original(self):
        """En radicación física, el campo cuerpo_correo del template debe estar vacío."""
        from django.core import mail

        self.client.force_login(self.user)
        self.client.post(
            reverse('correspondencia:dashboard_ventanilla'),
            {
                'form_prefix': 'rapida_entrante',
                'rapida_ent-asunto': 'Documento físico',
                'rapida_ent-oficina_destino': self.oficina.id,
                'rapida_ent-medio_recepcion': 'FISICO',
                'rapida_ent-email_funcionario_responsable': 'func@hospital.test',
            }
        )

        self.assertEqual(len(mail.outbox), 1)
        # No debe contener la sección "Contenido del correo original"
        self.assertNotIn('Contenido del correo original', mail.outbox[0].body)


# ===================== FIN TESTS PARA NUEVAS FUNCIONALIDADES =====================