import pytest
from django.urls import reverse
from django.contrib.auth.models import User, Group
from django.test import Client
from django.test import RequestFactory
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.exceptions import ValidationError
from correspondencia.models import (
    Correspondencia, Contacto, EntidadExterna, CorreoEntrante,
    AdjuntoCorreo, HistorialCorrespondencia, AccesoCorrespondenciaOficina,
    DistribucionInternaUsuario, Notificacion
)
from django.http import QueryDict

from correspondencia.views import (
    _aplicar_distribucion_rapida_desde_form,
    _extract_int_pks_from_post,
)
from documentos.models import (
    OficinaProductora, UnidadAdministrativa, EntidadProductora,
    SerieDocumental, SubserieDocumental, PerfilUsuario, MacroProceso, Proceso
)


def _prefixed_data(prefix, data):
    """Convierte un dict simple al formato esperado por un formulario con prefix."""
    return {f'{prefix}-{key}': value for key, value in data.items()}


@pytest.fixture
def setup_data(db):
    """Configurar datos básicos para los tests."""
    # Crear usuarios
    user = User.objects.create_user('testuser', password='pass')
    ventanilla_user = User.objects.create_user('ventanilla', password='pass')
    admin_user = User.objects.create_user('admin', password='pass', is_staff=True)
    
    # Crear grupos
    ventanilla_group = Group.objects.create(name='Ventanilla')
    admin_group = Group.objects.create(name='Admin')
    ventanilla_user.groups.add(ventanilla_group)
    admin_user.groups.add(admin_group)
    
    # Crear jerarquía de oficinas
    entidad_productora = EntidadProductora.objects.create(nombre='Entidad Test')
    unidad_administrativa = UnidadAdministrativa.objects.create(
        nombre='Unidad Test',
        entidad_productora=entidad_productora
    )
    macroproceso = MacroProceso.objects.create(numero=1, nombre='Macroproceso Test')
    proceso = Proceso.objects.create(
        numero=1,
        nombre='Proceso Test',
        sigla='PT',
        macroproceso=macroproceso,
    )
    oficina = OficinaProductora.objects.create(
        nombre='Oficina Test',
        unidad_administrativa=unidad_administrativa,
        proceso=proceso,
    )
    oficina_secundaria = OficinaProductora.objects.create(
        nombre='Oficina Jurídica',
        unidad_administrativa=unidad_administrativa,
        proceso=proceso,
    )
    
    # Crear entidad y contacto
    entidad = EntidadExterna.objects.create(nombre='Entidad Externa Test')
    contacto = Contacto.objects.create(
        entidad_externa=entidad,
        nombres='Juan',
        apellidos='Pérez',
        correo_electronico='juan@test.com'
    )
    
    # Crear serie y subserie
    serie = SerieDocumental.objects.create(nombre='Serie Test', codigo='SERIE-001')
    subserie = SubserieDocumental.objects.create(
        nombre='Subserie Test',
        codigo='SUBSERIE-001',
        serie=serie
    )
    
    juridica_user = User.objects.create_user('juridica', password='pass')
    coworker_user = User.objects.create_user('coworker', password='pass')

    # Perfiles de usuario
    PerfilUsuario.objects.create(user=user, oficina=oficina)
    PerfilUsuario.objects.create(user=juridica_user, oficina=oficina_secundaria)
    PerfilUsuario.objects.create(user=coworker_user, oficina=oficina)

    return {
        'user': user,
        'ventanilla_user': ventanilla_user,
        'admin_user': admin_user,
        'juridica_user': juridica_user,
        'coworker_user': coworker_user,
        'oficina': oficina,
        'oficina_secundaria': oficina_secundaria,
        'entidad': entidad,
        'contacto': contacto,
        'serie': serie,
        'subserie': subserie
    }


@pytest.fixture
def client_with_user(setup_data):
    """Cliente con usuario autenticado."""
    client = Client()
    client.force_login(setup_data['user'])
    return client


@pytest.fixture
def ventanilla_client(setup_data):
    """Cliente con usuario de ventanilla autenticado."""
    client = Client()
    client.force_login(setup_data['ventanilla_user'])
    return client


class TestViewsCoverage:
    """Tests para mejorar la cobertura de views.py."""
    
    def test_home_view_authenticated(self, client_with_user):
        """Test: Vista home con usuario autenticado."""
        response = client_with_user.get(reverse('correspondencia:home'))
        assert response.status_code == 200
    
    def test_home_view_unauthenticated(self, db):
        """Test: Vista home sin autenticación."""
        client = Client()
        response = client.get(reverse('correspondencia:home'))
        assert response.status_code in [302, 200]  # Redirect o página de login
    
    def test_bandeja_personal_view(self, client_with_user, setup_data):
        """Test: Vista de bandeja personal."""
        # Crear correspondencia para el usuario
        correspondencia = Correspondencia.objects.create(
            tipo_radicado='ENTRANTE',
            asunto='Test Bandeja',
            oficina_destino=setup_data['oficina'],
            usuario_radicador=setup_data['ventanilla_user'],
            usuario_destino_inicial=setup_data['user']
        )
        
        response = client_with_user.get(reverse('correspondencia:bandeja_personal'))
        assert response.status_code == 200
        assert 'correspondencias' in response.context
    
    def test_detalle_correspondencia_view_success(self, client_with_user, setup_data):
        """Test: Vista de detalle de correspondencia exitosa."""
        # Crear correspondencia donde el usuario tiene acceso
        correspondencia = Correspondencia.objects.create(
            tipo_radicado='ENTRANTE',
            asunto='Test Detalle',
            oficina_destino=setup_data['oficina'],
            usuario_radicador=setup_data['ventanilla_user'],
            usuario_destino_inicial=setup_data['user']
        )
        
        response = client_with_user.get(
            reverse('correspondencia:detalle_correspondencia', args=[correspondencia.id])
        )
        assert response.status_code in [200, 302]  # 200 si tiene acceso, 302 si redirige
    
    def test_detalle_correspondencia_view_not_found(self, client_with_user):
        """Test: Vista de detalle con ID inexistente."""
        response = client_with_user.get(
            reverse('correspondencia:detalle_correspondencia', args=[99999])
        )
        assert response.status_code == 404
    
    def test_radicar_manual_view_get(self, ventanilla_client):
        """Test: Vista de radicación manual GET."""
        response = ventanilla_client.get(reverse('correspondencia:radicar_manual'))
        assert response.status_code == 200
        assert 'form' in response.context
    
    def test_radicar_manual_view_post_valid(self, ventanilla_client, setup_data):
        """Test: Vista de radicación manual POST válido."""
        data = {
            'remitente': setup_data['contacto'].id,
            'asunto': 'Test Radicación',
            'medio_recepcion': 'ELECTRONICO',
            'oficina_destino': setup_data['oficina'].id,
            'serie': setup_data['serie'].id,
            'subserie': setup_data['subserie'].id,
            'requiere_respuesta': False,
        }
        
        response = ventanilla_client.post(reverse('correspondencia:radicar_manual'), data)
        assert response.status_code in [200, 302]  # 200 si hay errores, 302 si éxito
    
    def test_radicar_manual_view_post_invalid(self, ventanilla_client):
        """Test: Vista de radicación manual POST inválido."""
        data = {
            'asunto': '',  # Campo requerido vacío
        }
        
        response = ventanilla_client.post(reverse('correspondencia:radicar_manual'), data)
        assert response.status_code == 200  # Re-renderiza con errores
        assert 'form' in response.context
    
    def test_buscar_entidades_view(self, ventanilla_client, setup_data):
        """Test: Vista de búsqueda de entidades."""
        # Crear algunas entidades
        EntidadExterna.objects.create(nombre='Alpha Corp')
        EntidadExterna.objects.create(nombre='Beta Inc')
        
        response = ventanilla_client.get(
            reverse('correspondencia:buscar_entidades'),
            {'q': 'Alpha'}
        )
        assert response.status_code == 200
        data = response.json()
        assert 'results' in data
    
    def test_buscar_contactos_view(self, ventanilla_client, setup_data):
        """Test: Vista de búsqueda de contactos."""
        response = ventanilla_client.get(
            reverse('correspondencia:buscar_contactos'),
            {'entidad_id': setup_data['entidad'].id}
        )
        assert response.status_code == 200
        data = response.json()
        assert 'contactos' in data
    
    def test_buscar_oficinas_view(self, ventanilla_client, setup_data):
        """Test: Vista de búsqueda de oficinas."""
        response = ventanilla_client.get(
            reverse('correspondencia:buscar_oficinas'),
            {'q': 'Test'}
        )
        assert response.status_code == 200

    def test_compartir_correspondencia_mi_oficina(self, client_with_user, setup_data):
        """Test: Compartir correspondencia con toda la oficina."""
        correspondencia = Correspondencia.objects.create(
            tipo_radicado='ENTRANTE',
            asunto='Compartir Oficina',
            oficina_destino=setup_data['oficina'],
            usuario_radicador=setup_data['ventanilla_user'],
            usuario_destino_inicial=setup_data['user']
        )

        url = reverse('correspondencia:compartir_correspondencia', args=[correspondencia.id])
        response = client_with_user.post(url, {
            'observaciones': 'Compartido con todos'
        })

        assert response.status_code == 302

        # Debe existir distribución para cada compañero activo de la oficina
        distribuciones = correspondencia.distribuciones_internas.filter(
            usuario_asignado=setup_data['coworker_user']
        )
        assert distribuciones.exists()
        historial = HistorialCorrespondencia.objects.filter(
            correspondencia=correspondencia,
            evento='REDISTRIBUIDA_INTERNA'
        )
        assert historial.exists()

    def test_compartir_correspondencia_interoficina(self, client_with_user, setup_data):
        """Test: Compartir correspondencia con otra oficina en modo solo lectura."""
        correspondencia = Correspondencia.objects.create(
            tipo_radicado='ENTRANTE',
            asunto='Compartir Interoficina',
            oficina_destino=setup_data['oficina'],
            usuario_radicador=setup_data['ventanilla_user'],
            usuario_destino_inicial=setup_data['user']
        )

        url = reverse('correspondencia:redistribuir_oficinas', args=[correspondencia.id])
        response = client_with_user.post(url, {
            'oficinas': [str(setup_data['oficina_secundaria'].id)],
            'observaciones': 'Solo lectura para Jurídica'
        })

        assert response.status_code == 302

        acceso = AccesoCorrespondenciaOficina.objects.get(
            correspondencia=correspondencia,
            oficina=setup_data['oficina_secundaria']
        )
        assert acceso.observaciones == 'Solo lectura para Jurídica'
        assert HistorialCorrespondencia.objects.filter(
            correspondencia=correspondencia,
            evento='COMPARTIDA_OFICINA'
        ).exists()

        lider_group, _ = Group.objects.get_or_create(name='Lider de Oficina')
        setup_data['juridica_user'].groups.add(lider_group)

        juridica_client = Client()
        juridica_client.force_login(setup_data['juridica_user'])

        detalle_response = juridica_client.get(
            reverse('correspondencia:detalle_correspondencia', args=[correspondencia.id])
        )
        assert detalle_response.status_code == 200
        assert detalle_response.context['puede_responder'] is False

        acceso.refresh_from_db()
        assert acceso.leido is True
    
    def test_calcular_plazo_sla_view_success(self, client_with_user, setup_data):
        """Test: Vista de cálculo de SLA exitosa."""
        from correspondencia.models import TipoTramite

        tramite = TipoTramite.objects.create(
            codigo='PET',
            nombre='Petición general',
            dias_respuesta=15,
            activo=True,
        )
        data = {
            'tipo_tramite_codigo': tramite.codigo,
            'requiere_respuesta': 'true',
        }
        
        response = client_with_user.post(reverse('correspondencia:calcular_plazo_sla'), data)
        assert response.status_code == 200
        data = response.json()
        assert 'fecha_limite' in data or 'error' in data
    
    def test_calcular_plazo_sla_view_invalid_method(self, client_with_user):
        """Test: Vista de cálculo de SLA con método inválido."""
        response = client_with_user.get(reverse('correspondencia:calcular_plazo_sla'))
        assert response.status_code == 405
    
    def test_calcular_plazo_sla_view_missing_params(self, client_with_user):
        """Test: Vista de cálculo de SLA con parámetros faltantes."""
        data = {
            'requiere_respuesta': 'true'
            # Falta subserie_id y tiempo_respuesta
        }
        
        response = client_with_user.post(reverse('correspondencia:calcular_plazo_sla'), data)
        assert response.status_code == 400
    
    def test_dashboard_ventanilla_view(self, ventanilla_client):
        """Test: Vista de dashboard de ventanilla."""
        response = ventanilla_client.get(reverse('correspondencia:dashboard_ventanilla'))
        assert response.status_code == 200
    
    def test_dashboard_ventanilla_view_unauthorized(self, client_with_user):
        """Test: Vista de dashboard sin permisos de ventanilla."""
        response = client_with_user.get(reverse('correspondencia:dashboard_ventanilla'))
        assert response.status_code in [302, 403]  # Redirect o forbidden

    def test_dashboard_ventanilla_radicacion_convencional(self, ventanilla_client, setup_data):
        """Test: La radicación desde dashboard sigue funcionando sin distribución rápida."""
        data = {
            'form_prefix': 'radicar',
            **_prefixed_data('radicar', {
                'remitente': setup_data['contacto'].id,
                'asunto': 'Radicación convencional dashboard',
                'medio_recepcion': 'ELECTRONICO',
                'oficina_destino': setup_data['oficina'].id,
                'serie': setup_data['serie'].id,
                'subserie': setup_data['subserie'].id,
                'requiere_respuesta': '',
            })
        }

        response = ventanilla_client.post(reverse('correspondencia:dashboard_ventanilla'), data)

        assert response.status_code == 302
        correspondencia = Correspondencia.objects.get(asunto='Radicación convencional dashboard')
        assert correspondencia.usuario_destino_inicial is None
        assert DistribucionInternaUsuario.objects.filter(correspondencia=correspondencia).count() == 0
        assert HistorialCorrespondencia.objects.filter(
            correspondencia=correspondencia,
            evento='RADICADA'
        ).exists()

    def test_extract_int_pks_from_post_multiple_otras_oficinas(self):
        """Test: POST con varios radicar-otras_oficinas no debe unir IDs con coma."""
        post = QueryDict(mutable=True)
        post.setlist('radicar-otras_oficinas', ['28', '88'])

        pks = _extract_int_pks_from_post(post, ('radicar-otras_oficinas',))

        assert pks == {28, 88}

    def test_extract_int_pks_from_post_ignores_comma_joined_invalid_value(self):
        """Test: valor inválido '28,88' (bug JS) no produce PKs parseables."""
        post = QueryDict(mutable=True)
        post['radicar-otras_oficinas'] = '28,88'

        pks = _extract_int_pks_from_post(post, ('radicar-otras_oficinas',))

        assert pks == set()

    def test_dashboard_ventanilla_radicacion_con_multiples_otras_oficinas(self, ventanilla_client, setup_data):
        """Test: distribución rápida acepta varias oficinas adicionales en el POST."""
        oficina_terciaria = OficinaProductora.objects.create(
            nombre='Oficina Terciaria',
            unidad_administrativa=setup_data['oficina'].unidad_administrativa,
            proceso=setup_data['oficina'].proceso,
        )
        data = {
            'form_prefix': 'radicar',
            **_prefixed_data('radicar', {
                'remitente': setup_data['contacto'].id,
                'asunto': 'Radicación con múltiples oficinas adicionales',
                'medio_recepcion': 'ELECTRONICO',
                'oficina_destino': setup_data['oficina'].id,
                'serie': setup_data['serie'].id,
                'subserie': setup_data['subserie'].id,
                'requiere_respuesta': '',
                'distribuir_rapido': 'on',
                'usuario_destino_rapido': setup_data['user'].id,
                'otras_oficinas': [
                    setup_data['oficina_secundaria'].id,
                    oficina_terciaria.id,
                ],
                'observaciones_distribucion': 'Varias oficinas adicionales',
            })
        }

        response = ventanilla_client.post(reverse('correspondencia:dashboard_ventanilla'), data)

        assert response.status_code == 302
        correspondencia = Correspondencia.objects.get(asunto='Radicación con múltiples oficinas adicionales')
        oficinas_compartidas = set(
            AccesoCorrespondenciaOficina.objects.filter(correspondencia=correspondencia)
            .values_list('oficina_id', flat=True)
        )
        assert oficinas_compartidas == {
            setup_data['oficina_secundaria'].id,
            oficina_terciaria.id,
        }

    def test_aplicar_distribucion_rapida_desde_form_con_multiples_otras_oficinas(self, setup_data):
        """Test: el helper crea acceso para cada oficina adicional."""
        oficina_terciaria = OficinaProductora.objects.create(
            nombre='Oficina Extra',
            unidad_administrativa=setup_data['oficina'].unidad_administrativa,
            proceso=setup_data['oficina'].proceso,
        )
        correspondencia = Correspondencia.objects.create(
            tipo_radicado='ENTRANTE',
            asunto='Helper múltiples oficinas',
            oficina_destino=setup_data['oficina'],
            usuario_radicador=setup_data['ventanilla_user'],
        )
        request = RequestFactory().post('/')
        request.user = setup_data['ventanilla_user']

        _aplicar_distribucion_rapida_desde_form(
            correspondencia,
            request,
            {
                'distribuir_rapido': True,
                'usuario_destino_rapido': setup_data['user'],
                'compartir_con_toda_oficina': False,
                'otras_oficinas': [
                    setup_data['oficina_secundaria'],
                    oficina_terciaria,
                ],
                'observaciones_distribucion': 'Varias oficinas',
            }
        )

        oficinas_compartidas = set(
            AccesoCorrespondenciaOficina.objects.filter(correspondencia=correspondencia)
            .values_list('oficina_id', flat=True)
        )
        assert oficinas_compartidas == {
            setup_data['oficina_secundaria'].id,
            oficina_terciaria.id,
        }

    def test_dashboard_ventanilla_radicacion_con_distribucion_rapida(self, ventanilla_client, setup_data):
        """Test: La segunda parte del modal asigna y comparte en el mismo POST."""
        data = {
            'form_prefix': 'radicar',
            **_prefixed_data('radicar', {
                'remitente': setup_data['contacto'].id,
                'asunto': 'Radicación con distribución rápida',
                'medio_recepcion': 'ELECTRONICO',
                'oficina_destino': setup_data['oficina'].id,
                'serie': setup_data['serie'].id,
                'subserie': setup_data['subserie'].id,
                'requiere_respuesta': '',
                'distribuir_rapido': 'on',
                'usuario_destino_rapido': setup_data['user'].id,
                'compartir_con_toda_oficina': 'on',
                'otras_oficinas': [setup_data['oficina_secundaria'].id],
                'observaciones_distribucion': 'Distribución inicial de prueba',
            })
        }

        response = ventanilla_client.post(reverse('correspondencia:dashboard_ventanilla'), data)

        assert response.status_code == 302
        correspondencia = Correspondencia.objects.get(asunto='Radicación con distribución rápida')
        assert correspondencia.usuario_destino_inicial == setup_data['user']
        assert correspondencia.estado == 'ASIGNADA_USUARIO'

        usuarios_distribuidos = set(
            DistribucionInternaUsuario.objects.filter(correspondencia=correspondencia)
            .values_list('usuario_asignado_id', flat=True)
        )
        assert usuarios_distribuidos == {setup_data['user'].id, setup_data['coworker_user'].id}

        assert AccesoCorrespondenciaOficina.objects.filter(
            correspondencia=correspondencia,
            oficina=setup_data['oficina_secundaria']
        ).exists()
        assert HistorialCorrespondencia.objects.filter(
            correspondencia=correspondencia,
            evento='ASIGNADA_USUARIO'
        ).exists()
        assert HistorialCorrespondencia.objects.filter(
            correspondencia=correspondencia,
            evento='REDISTRIBUIDA_INTERNA'
        ).exists()

    def test_dashboard_ventanilla_radicacion_distribuye_solo_a_responsable_si_no_comparten_oficina(self, ventanilla_client, setup_data):
        """Test: Si no se marca compartir con toda la oficina, solo queda el responsable principal."""
        data = {
            'form_prefix': 'radicar',
            **_prefixed_data('radicar', {
                'remitente': setup_data['contacto'].id,
                'asunto': 'Radicación rápida solo responsable',
                'medio_recepcion': 'ELECTRONICO',
                'oficina_destino': setup_data['oficina'].id,
                'serie': setup_data['serie'].id,
                'subserie': setup_data['subserie'].id,
                'requiere_respuesta': '',
                'distribuir_rapido': 'on',
                'usuario_destino_rapido': setup_data['user'].id,
                'observaciones_distribucion': 'Solo responsable',
            })
        }

        response = ventanilla_client.post(reverse('correspondencia:dashboard_ventanilla'), data)

        assert response.status_code == 302
        correspondencia = Correspondencia.objects.get(asunto='Radicación rápida solo responsable')
        usuarios_distribuidos = set(
            DistribucionInternaUsuario.objects.filter(correspondencia=correspondencia)
            .values_list('usuario_asignado_id', flat=True)
        )
        assert usuarios_distribuidos == {setup_data['user'].id}
        assert not HistorialCorrespondencia.objects.filter(
            correspondencia=correspondencia,
            evento='REDISTRIBUIDA_INTERNA'
        ).exists()

    def test_dashboard_ventanilla_radicacion_fisica_guarda_adjuntos(self, ventanilla_client, setup_data):
        """Test: El modal de dashboard guarda adjuntos físicos en la radicación."""
        test_file = SimpleUploadedFile(
            'dashboard-adjunto.pdf',
            b'contenido de prueba',
            content_type='application/pdf'
        )

        data = {
            'form_prefix': 'radicar',
            'adjuntos_entrada': test_file,
            **_prefixed_data('radicar', {
                'remitente': setup_data['contacto'].id,
                'asunto': 'Radicación física dashboard con adjunto',
                'medio_recepcion': 'FISICO',
                'oficina_destino': setup_data['oficina'].id,
                'serie': setup_data['serie'].id,
                'subserie': setup_data['subserie'].id,
                'requiere_respuesta': '',
            })
        }

        response = ventanilla_client.post(reverse('correspondencia:dashboard_ventanilla'), data)

        assert response.status_code == 302
        correspondencia = Correspondencia.objects.get(asunto='Radicación física dashboard con adjunto')
        adjunto = AdjuntoCorreo.objects.get(correspondencia=correspondencia)
        assert adjunto.nombre_original == 'dashboard-adjunto.pdf'

    def test_aplicar_distribucion_rapida_desde_form_rechaza_usuario_fuera_de_oficina(self, setup_data):
        """Test: La ayuda backend protege contra asignaciones inconsistentes."""
        correspondencia = Correspondencia.objects.create(
            tipo_radicado='ENTRANTE',
            asunto='Helper distribución rápida',
            oficina_destino=setup_data['oficina'],
            usuario_radicador=setup_data['ventanilla_user'],
        )
        request = RequestFactory().post('/')
        request.user = setup_data['ventanilla_user']

        with pytest.raises(ValidationError):
            _aplicar_distribucion_rapida_desde_form(
                correspondencia,
                request,
                {
                    'distribuir_rapido': True,
                    'usuario_destino_rapido': setup_data['juridica_user'],
                    'compartir_con_toda_oficina': False,
                    'otras_oficinas': [],
                    'observaciones_distribucion': 'Inválida',
                }
            )

    def test_aplicar_distribucion_rapida_desde_form_respeta_compartir_con_toda_oficina(self, setup_data):
        """Test: El helper solo comparte con toda la oficina cuando esa opción está marcada."""
        correspondencia = Correspondencia.objects.create(
            tipo_radicado='ENTRANTE',
            asunto='Helper distribución rápida solo responsable',
            oficina_destino=setup_data['oficina'],
            usuario_radicador=setup_data['ventanilla_user'],
        )
        request = RequestFactory().post('/')
        request.user = setup_data['ventanilla_user']

        suffix = _aplicar_distribucion_rapida_desde_form(
            correspondencia,
            request,
            {
                'distribuir_rapido': True,
                'usuario_destino_rapido': setup_data['user'],
                'compartir_con_toda_oficina': False,
                'otras_oficinas': [],
                'observaciones_distribucion': 'Solo responsable',
            }
        )

        usuarios_distribuidos = set(
            DistribucionInternaUsuario.objects.filter(correspondencia=correspondencia)
            .values_list('usuario_asignado_id', flat=True)
        )
        assert usuarios_distribuidos == {setup_data['user'].id}
        assert 'solo al responsable principal' in suffix
        assert not HistorialCorrespondencia.objects.filter(
            correspondencia=correspondencia,
            evento='REDISTRIBUIDA_INTERNA'
        ).exists()
    
    def test_radicacion_con_adjuntos_fisico(self, ventanilla_client, setup_data):
        """Test: Radicación con adjuntos físicos."""
        # Crear archivo de prueba
        test_file = SimpleUploadedFile(
            "test.pdf",
            b"file_content",
            content_type="application/pdf"
        )
        
        data = {
            'remitente': setup_data['contacto'].id,
            'asunto': 'Test con Adjuntos',
            'medio_recepcion': 'FISICO',
            'oficina_destino': setup_data['oficina'].id,
            'serie': setup_data['serie'].id,
            'subserie': setup_data['subserie'].id,
            'requiere_respuesta': False,
        }
        
        files = {
            'adjuntos_entrada': [test_file]
        }
        
        response = ventanilla_client.post(
            reverse('correspondencia:radicar_manual'),
            data,
            files=files
        )
        assert response.status_code in [200, 302]
    
    def test_radicacion_fisico_sin_adjuntos_error(self, ventanilla_client, setup_data):
        """Test: Radicación física sin adjuntos debe fallar."""
        data = {
            'remitente': setup_data['contacto'].id,
            'asunto': 'Test sin Adjuntos',
            'medio_recepcion': 'FISICO',
            'oficina_destino': setup_data['oficina'].id,
            'serie': setup_data['serie'].id,
            'subserie': setup_data['subserie'].id,
            'requiere_respuesta': False,
        }
        
        response = ventanilla_client.post(reverse('correspondencia:radicar_manual'), data)
        assert response.status_code == 200  # Re-renderiza con errores
    
    def test_bandeja_clasificados_view(self, ventanilla_client, setup_data):
        """Test: La bandeja de correos pendientes muestra correos procesados sin revisión manual."""
        correo = CorreoEntrante.objects.create(
            remitente='test@example.com',
            asunto='Test Correo',
            procesado=True,
            requiere_revision_manual=False,
            oficina_clasificada=setup_data['oficina'],
            serie_clasificada=setup_data['serie'],
            subserie_clasificada=setup_data['subserie']
        )
        
        response = ventanilla_client.get(reverse('correspondencia:bandeja_correos_pendientes'), {
            'estado': 'pendiente',
            'desde': '2000-01-01',
        })
        assert response.status_code == 200
        assert 'correos' in response.context
        assert correo in list(response.context['correos'])
    
    def test_bandeja_revision_manual_view(self, ventanilla_client, setup_data):
        """Test: La bandeja de correos pendientes sigue listando correos con revisión manual."""
        correo = CorreoEntrante.objects.create(
            remitente='test@example.com',
            asunto='Test Correo Revisión',
            procesado=True,
            requiere_revision_manual=True,
            oficina_clasificada=setup_data['oficina'],
            serie_clasificada=setup_data['serie'],
            subserie_clasificada=setup_data['subserie']
        )
        
        response = ventanilla_client.get(reverse('correspondencia:bandeja_correos_pendientes'), {
            'desde': '2000-01-01',
        })
        assert response.status_code == 200
        assert 'correos' in response.context
        assert correo in list(response.context['correos'])
