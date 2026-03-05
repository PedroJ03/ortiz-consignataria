import os
import sys
import pytest

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from data_pipeline.main import ejecutar_pipeline_diario
import data_pipeline.main

def test_orquestador_flujo_completo(mocker):
    """
    Prueba el orquestador principal (main.py) simulando que todo (scrapers, DB, config, Email) funciona.
    """
    # 1. Mocks de la capa de extracción (Devuelven 1 registro falso)
    mock_faena = mocker.patch('data_pipeline.main.mag_scraper.scrape_mag_faena')
    mock_faena.return_value = [{'fake': 'faena'}]
    
    mock_invernada = mocker.patch('data_pipeline.main.cac_scraper.scrape_invernada_diario')
    mock_invernada.return_value = [{'fake': 'invernada'}]

    # 2. Mocks Capa BBDD
    mock_db = mocker.patch('data_pipeline.main.db_manager')
    mock_conn = mocker.Mock()
    mock_db.get_db_connection.return_value = mock_conn
    mock_db.insertar_datos_faena.return_value = 1
    mock_db.insertar_datos_invernada.return_value = 1

    # 3. Mocks Reportes y Emails
    mock_report = mocker.patch('data_pipeline.main.report_generator.generate_pdf_report')
    mock_report.return_value = "/fake/path.pdf"
    
    mock_email = mocker.patch('data_pipeline.main.email_sender.send_report_email')
    mock_email.return_value = True

    # Asegurar que hay lista de emails para que entre al flujo de envío
    mocker.patch('data_pipeline.main.LISTA_DESTINATARIOS', ['test@test.com'])

    # Ejecutar Pipeline (Permitiendo envío de email)
    ejecutar_pipeline_diario(enviar_email=True)

    # Asserts - Comprobar coreografía de funciones
    mock_db.get_db_connection.assert_called_once()
    mock_db.crear_tablas_market.assert_called_once_with(mock_conn)
    mock_db.crear_tablas_precios.assert_called_once_with(mock_conn)
    
    mock_faena.assert_called_once()
    mock_invernada.assert_called_once()
    
    mock_db.insertar_datos_faena.assert_called_once_with(mock_conn, [{'fake': 'faena'}])
    
    # Verifica que el generador de PDF se llamó dos veces (Faena + Invernada)
    assert mock_report.call_count == 2
    
    # Verifica envío de mail
    mock_email.assert_called_once()

def test_orquestador_sin_email(mocker):
    """
    Asegura que la bandera enviar_email=False (Modo Silencioso / Cron Parcial) se respeta.
    """
    mocker.patch('data_pipeline.main.mag_scraper.scrape_mag_faena', return_value=[{'fake': 1}])
    mocker.patch('data_pipeline.main.cac_scraper.scrape_invernada_diario', return_value=[{'fake': 2}])
    mocker.patch('data_pipeline.main.db_manager')
    mocker.patch('data_pipeline.main.report_generator.generate_pdf_report', return_value="/f.pdf")
    
    mock_email = mocker.patch('data_pipeline.main.email_sender.send_report_email')

    ejecutar_pipeline_diario(enviar_email=False)

    # El email NO debió ser enviado, aunque haya reportes generados.
    mock_email.assert_not_called()