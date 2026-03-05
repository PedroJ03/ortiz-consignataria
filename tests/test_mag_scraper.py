import pytest
import os
import sys

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from data_pipeline.scrapers import mag_scraper, cac_scraper

# Simulación de respuesta HTML básica
HTML_MOCK = """
<html>
    <table id='tableMain'>
        <tr>
            <td>TERNEROS</td>
            <td>180-200</td>
            <td>150</td>
            <td>1600.00</td>
            <td>1800.00</td>
            <td>1700.00</td>
        </tr>
    </table>
</html>
"""

def test_mag_faena_scraper_vacio(mocker):
    """
    Simula que el Scraper MAG se conecta, pero no encuentra filas válidas.
    """
    # Mockear Session.get y Session.post
    mock_session = mocker.patch('data_pipeline.scrapers.mag_scraper.requests.Session')
    
    mock_resp = mocker.Mock()
    mock_resp.status_code = 200
    mock_resp.text = "<html><table></table></html>" # Tabla vacía
    
    # Ambas solicitudes (GET del Form y POST de datos) devuelven el HTML vacío
    mock_session.return_value.get.return_value = mock_resp
    mock_session.return_value.post.return_value = mock_resp

    datos = mag_scraper.scrape_mag_faena("15/11/2025", "15/11/2025")
    
    assert isinstance(datos, list)
    assert len(datos) == 0

def test_mag_faena_html_cambiado(mocker):
    """
    Simula que Mercado Agroganadero cambia su estructura HTML repentinamente.
    """
    mock_session = mocker.patch('data_pipeline.scrapers.mag_scraper.requests.Session')
    
    mock_resp = mocker.Mock()
    mock_resp.status_code = 200
    mock_resp.text = "<html><div class='error'>No data</div></html>" 
    
    mock_session.return_value.get.return_value = mock_resp
    mock_session.return_value.post.return_value = mock_resp

    datos = mag_scraper.scrape_mag_faena("17/11/2025", "17/11/2025")
    assert datos == [] # No debe crashear, sino retornar vacío y loggear

def test_mag_timeout_resilience(mocker):
    """
    Verifica que el sistema no se caiga si el Mercado Agroganadero no responde.
    """
    import requests
    mock_session = mocker.patch('data_pipeline.scrapers.mag_scraper.requests.Session')
    
    # Forzar un timeout
    mock_session.return_value.get.side_effect = requests.Timeout("Connection timed out")

    datos = mag_scraper.scrape_mag_faena("17/11/2025", "17/11/2025")
    assert len(datos) == 0

# === CAC SCRAPER (Invernada) ===
def test_cac_invernada_timeout(mocker):
    import requests
    # cac_scraper.py usa una capa de sesión requests.Session()
    mock_session = mocker.patch('data_pipeline.scrapers.cac_scraper.requests.Session')
    mock_session.return_value.get.side_effect = requests.Timeout("CAC down")
    
    datos = cac_scraper.scrape_invernada_diario()
    assert datos == []