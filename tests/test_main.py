import sys
import os
import pytest
from unittest.mock import patch, MagicMock

# --- ========================================== ---
# --- INICIO DE CORRECCIÓN DE ARQUITECTURA ---
# --- ========================================== ---
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)
# --- FIN DE CORRECCIÓN DE ARQUITECTURA ---

# Ahora importamos la función real que queremos probar
from data_pipeline.main import ejecutar_proceso_completo

@patch('data_pipeline.main.email_sender')
@patch('data_pipeline.main.report_generator')
@patch('data_pipeline.main.cac_scraper')
@patch('data_pipeline.main.mag_scraper')
@patch('data_pipeline.main.db_manager')
def test_ejecutar_proceso_exitoso(mock_db_manager, mock_mag_scraper, 
                                   mock_cac_scraper, mock_report_gen, 
                                   mock_email_sender):
    """
    Prueba el "camino feliz" completo, simulando que todos los
    módulos importados funcionan.
    """
    print("\nEjecutando: test_ejecutar_proceso_exitoso (corregido)")
    
    # 1. Configurar los mocks (simulaciones)
    
    # Datos de scraper realistas
    datos_reales_faena = [{
        'fecha_consulta_inicio': '17/11/2025', 
        'categoria_original': 'NOVILLOS', 
        'precio_promedio_kg': 1000
    }]
    datos_reales_invernada = [{
        'fecha_consulta_inicio': '16/11/2025', 
        'fecha_consulta_fin': '17/11/2025', 
        'categoria_original': 'TERNEROS', 
        'precio_promedio_kg': 1200
    }]
    
    # Simular los valores de retorno de las *funciones dentro* de los módulos
    mock_db_manager.get_db_connection.return_value = MagicMock()
    mock_mag_scraper.scrape_mag_faena.return_value = datos_reales_faena
    mock_cac_scraper.scrape_invernada_campo.return_value = datos_reales_invernada
    mock_db_manager.insertar_datos_faena.return_value = 1
    mock_db_manager.insertar_datos_invernada.return_value = 1
    mock_report_gen.generate_pdf_report.return_value = "dummy/path.pdf"
    mock_email_sender.send_report_email.return_value = True

    # 2. Ejecutar la función
    ejecutar_proceso_completo("17/11/2025", debug=True)

    # 3. Verificar que las funciones clave fueron llamadas
    mock_db_manager.get_db_connection.assert_called_once()
    mock_db_manager.crear_tablas.assert_called_once()
    mock_mag_scraper.scrape_mag_faena.assert_called_once()
    
    # --- ¡ESTA ES LA LÍNEA QUE FALLABA! ---
    mock_db_manager.insertar_datos_faena.assert_called_once_with(
        mock_db_manager.get_db_connection.return_value, 
        datos_reales_faena
    )
    
    mock_report_gen.generate_pdf_report.assert_called()
    mock_email_sender.send_report_email.assert_called_once()
    print("Test exitoso completado.")

# --- (El resto de los tests se corrigen de forma similar) ---

@patch('data_pipeline.main.mag_scraper')
@patch('data_pipeline.main.db_manager')
def test_ejecutar_proceso_scraper_falla(mock_db_manager, mock_mag_scraper):
    """Prueba qué pasa si el scraper de MAG falla."""
    print("\nEjecutando: test_ejecutar_proceso_scraper_falla (corregido)")
    
    mock_db_manager.get_db_connection.return_value = MagicMock()
    mock_mag_scraper.scrape_mag_faena.side_effect = Exception("Error de red simulado")

    ejecutar_proceso_completo("17/11/2025", debug=True)

    mock_db_manager.crear_tablas.assert_called_once()
    # Verificar que NO se intentó insertar
    mock_db_manager.insertar_datos_faena.assert_not_called()
    print("Test de fallo de scraper completado.")

@patch('data_pipeline.main.db_manager')
def test_ejecutar_proceso_db_falla(mock_db_manager):
    """Prueba qué pasa si la conexión a la BBDD falla."""
    print("\nEjecutando: test_ejecutar_proceso_db_falla (corregido)")
    
    mock_db_manager.get_db_connection.return_value = None
    ejecutar_proceso_completo("17/11/2025", debug=True)
    
    # Verificar que el proceso se detuvo
    mock_db_manager.crear_tablas.assert_not_called()
    print("Test de fallo de BBDD completado.")