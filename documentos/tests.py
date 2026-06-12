from django.contrib.auth.models import User
from django.test import SimpleTestCase, TestCase
from django.urls import reverse
from django.utils import timezone

from documentos.models import EntidadProductora, HistorialDescargaPrestamo, MacroProceso, OficinaProductora, PerfilUsuario, PrestamoDocumental, Proceso, UnidadAdministrativa
from documentos.oficinas_autoritativas import OFICINAS_RADICADO_DEFINIDAS, codigo_dependencia_esperado, normalizar


class OficinasAutoritativasTests(SimpleTestCase):
	def _crear_oficina_no_persistida(self, definicion):
		entidad = EntidadProductora(nombre='Hospital del Sarare')
		unidad = UnidadAdministrativa(nombre='Unidad de prueba', entidad_productora=entidad)
		macro = MacroProceso(numero=1, nombre='Macroproceso de prueba')
		proceso = Proceso(
			numero=definicion['proceso_numero'],
			nombre=f"Proceso {definicion['sigla']}",
			sigla=definicion['sigla'],
			macroproceso=macro,
		)
		return OficinaProductora(
			nombre=definicion['nombre'],
			codigo=definicion['codigo'],
			codigo_trd=definicion['codigo_trd'],
			unidad_administrativa=unidad,
			proceso=proceso,
		)

	def test_las_definiciones_autoritativas_generan_codigo_dependencia_esperado(self):
		for definicion in OFICINAS_RADICADO_DEFINIDAS:
			oficina = self._crear_oficina_no_persistida(definicion)
			self.assertEqual(oficina.codigo_dependencia, definicion['codigo_dependencia'])

	def test_los_codigos_dependencia_definidos_son_unicos(self):
		codigos = [definicion['codigo_dependencia'] for definicion in OFICINAS_RADICADO_DEFINIDAS]
		self.assertEqual(len(codigos), len(set(codigos)))

	def test_los_aliases_normalizados_no_generan_colisiones_internas(self):
		alias_map = {}
		for definicion in OFICINAS_RADICADO_DEFINIDAS:
			for alias in definicion['aliases']:
				normalizado = normalizar(alias)
				previo = alias_map.get(normalizado)
				self.assertIn(previo, (None, definicion['nombre']))
				alias_map[normalizado] = definicion['nombre']

	def test_helper_de_codigo_dependencia_formatea_con_ceros(self):
		self.assertEqual(codigo_dependencia_esperado('SIS', 14, '2'), 'SIS-14-002')
		self.assertEqual(codigo_dependencia_esperado('DIR', 1, '0'), 'DIR-01-000')

	def test_codigo_sis_explicito_tiene_prioridad(self):
		oficina = self._crear_oficina_no_persistida(OFICINAS_RADICADO_DEFINIDAS[0])
		oficina.codigo_sis = 'SUC-00'
		self.assertEqual(oficina.get_codigo_sis(), 'SUC-00')
		self.assertEqual(oficina.codigo_dependencia, 'SUC-00')


class PrestamosDocumentalesFlowTests(TestCase):
	def setUp(self):
		entidad = EntidadProductora.objects.create(nombre='Hospital del Sarare')
		unidad = UnidadAdministrativa.objects.create(nombre='Unidad principal', entidad_productora=entidad)
		macro = MacroProceso.objects.create(numero=1, nombre='Macroproceso de prueba')
		proceso = Proceso.objects.create(numero=1, nombre='Proceso de prueba', sigla='PRU', macroproceso=macro)

		self.oficina_solicitante = OficinaProductora.objects.create(
			nombre='Talento Humano',
			codigo='1',
			codigo_trd='321',
			unidad_administrativa=unidad,
			proceso=proceso,
		)
		self.oficina_archivo = OficinaProductora.objects.create(
			nombre='Archivo Central',
			codigo='2',
			codigo_trd='320',
			unidad_administrativa=unidad,
			proceso=proceso,
		)

		self.solicitante = User.objects.create_user(username='solicitante', password='test123')
		PerfilUsuario.objects.create(user=self.solicitante, oficina=self.oficina_solicitante)

		self.gestor_archivo = User.objects.create_user(username='archivo', password='test123')
		PerfilUsuario.objects.create(user=self.gestor_archivo, oficina=self.oficina_archivo)

	def _crear_prestamo(self, **overrides):
		data = {
			'solicitante': self.solicitante,
			'oficina_solicitante': self.oficina_solicitante,
			'oficina_responsable': self.oficina_archivo,
			'descripcion_documento': 'Historia clínica de prueba',
			'tipo_prestamo': 'FISICO',
			'estado': 'SOLICITADO',
		}
		data.update(overrides)
		return PrestamoDocumental.objects.create(**data)

	def test_archivo_entrega_y_usuario_confirma_en_pasos_separados(self):
		prestamo = self._crear_prestamo()

		self.client.force_login(self.gestor_archivo)
		respuesta_entrega = self.client.post(
			reverse('procesar_prestamo', args=[prestamo.id]),
			{'accion': 'cargar_evidencia'},
			follow=True,
		)

		self.assertEqual(respuesta_entrega.status_code, 200)
		prestamo.refresh_from_db()
		self.assertEqual(prestamo.estado, 'ENTREGADO')
		self.assertFalse(prestamo.confirmado_por_usuario)
		self.assertIsNone(prestamo.fecha_confirmacion)
		self.assertIsNotNone(prestamo.fecha_entrega)
		self.assertIsNotNone(prestamo.fecha_aprobacion)
		self.assertEqual(prestamo.historial.first().evento, 'Entrega física registrada por Archivo')

		self.client.force_login(self.solicitante)
		respuesta_confirmacion = self.client.post(
			reverse('confirmar_recepcion', args=[prestamo.id]),
			{'accion': 'confirmar'},
			follow=True,
		)

		self.assertEqual(respuesta_confirmacion.status_code, 200)
		prestamo.refresh_from_db()
		self.assertEqual(prestamo.estado, 'PRESTAMO_ACTIVO')
		self.assertTrue(prestamo.confirmado_por_usuario)
		self.assertIsNotNone(prestamo.fecha_confirmacion)
		self.assertEqual(prestamo.historial.first().evento, 'Recepción confirmada por usuario')

	def test_solicitud_de_devolucion_solo_aplica_a_prestamos_fisicos(self):
		prestamo = self._crear_prestamo(tipo_prestamo='VIRTUAL', estado='PRESTAMO_ACTIVO')

		self.client.force_login(self.solicitante)
		respuesta = self.client.post(
			reverse('solicitar_devolucion', args=[prestamo.id]),
			follow=True,
		)

		self.assertEqual(respuesta.status_code, 200)
		prestamo.refresh_from_db()
		self.assertEqual(prestamo.estado, 'PRESTAMO_ACTIVO')

	def test_archivo_puede_registrar_devolucion_despues_de_solicitud(self):
		prestamo = self._crear_prestamo(estado='DEVOLUCION_SOLICITADA')

		self.client.force_login(self.gestor_archivo)
		respuesta = self.client.post(
			reverse('procesar_prestamo', args=[prestamo.id]),
			{'finalizar_prestamo': 'on'},
			follow=True,
		)

		self.assertEqual(respuesta.status_code, 200)
		prestamo.refresh_from_db()
		self.assertEqual(prestamo.estado, 'DEVUELTO')
		self.assertTrue(prestamo.documento_devuelto)
		self.assertIsNotNone(prestamo.fecha_devolucion)
		self.assertEqual(prestamo.historial.first().evento, 'Documento recibido por Archivo')

	def test_solicitar_devolucion_registra_evento_de_historial(self):
		prestamo = self._crear_prestamo(estado='PRESTAMO_ACTIVO')

		self.client.force_login(self.solicitante)
		respuesta = self.client.post(
			reverse('solicitar_devolucion', args=[prestamo.id]),
			follow=True,
		)

		self.assertEqual(respuesta.status_code, 200)
		prestamo.refresh_from_db()
		self.assertEqual(prestamo.estado, 'DEVOLUCION_SOLICITADA')
		self.assertEqual(prestamo.historial.first().evento, 'Devolución solicitada por usuario')

	def test_exporte_mensual_crea_auditoria(self):
		prestamo = self._crear_prestamo(estado='DEVUELTO')
		prestamo.documento_devuelto = True
		prestamo.save(update_fields=['documento_devuelto'])
		PrestamoDocumental.objects.filter(pk=prestamo.pk).update(
			fecha_solicitud=timezone.datetime(2026, 4, 3, 10, 0, tzinfo=timezone.get_current_timezone())
		)

		self.client.force_login(self.gestor_archivo)
		respuesta = self.client.get(reverse('exportar_prestamos_excel_mensual'), {
			'year': 2026,
			'month': 4,
			'alerta': 'pendientes_reintegracion',
		})

		self.assertEqual(respuesta.status_code, 200)
		self.assertEqual(
			respuesta['Content-Type'],
			'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
		)
		auditoria = HistorialDescargaPrestamo.objects.latest('fecha_descarga')
		self.assertEqual(auditoria.anio, 2026)
		self.assertEqual(auditoria.mes, 4)
		self.assertEqual(auditoria.filtro_alerta, 'pendientes_reintegracion')
		self.assertEqual(auditoria.total_registros, 1)
