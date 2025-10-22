import pytest
from scrapers import mag_scraper
import requests # Necesario para simular errores de red

# Ya no necesitamos modificar sys.path, __init__.py lo soluciona.

# --- PRUEBAS INDIVIDUALES ---
# Cada función que empieza con "test_" es una prueba que pytest ejecutará.

def test_caso_normal_dia_habil():
    """
    Prueba el scraper en un día hábil donde esperamos encontrar datos.
    """
    print("Ejecutando: test_caso_normal_dia_habil")
    fecha = "17/10/2025" # Viernes
    datos = mag_scraper.scrape_mag(fecha, tipo_hacienda='TODOS')
    
    # Aserción: Afirmamos que la lista de datos NO debe estar vacía.
    assert datos, "El scraper no debería devolver una lista vacía en un día hábil."
    assert len(datos) > 0, "El scraper debería encontrar más de 0 registros."
    print(f"✅ ÉXITO: Se encontraron {len(datos)} registros.")

def test_caso_extremo_dia_sin_operaciones():
    """
    Prueba el scraper en un día no hábil (lunes) donde esperamos cero datos.
    """
    print("Ejecutando: test_caso_extremo_dia_sin_operaciones")
    fecha = "20/10/2025" # Lunes
    datos = mag_scraper.scrape_mag(fecha, tipo_hacienda='TODOS')
    
    # Aserción: Afirmamos que la lista de datos SÍ debe estar vacía.
    assert not datos, "El scraper debería devolver una lista vacía en un día sin operaciones."
    print("✅ ÉXITO ESPERADO: No se encontraron registros.")


def test_caso_curioso_filtro_invernada():
    """
    Prueba que el filtro por tipo de hacienda específico funciona.
    """
    print("Ejecutando: test_caso_curioso_filtro_invernada")
    fecha = "17/10/2025"
    datos = mag_scraper.scrape_mag(fecha, tipo_hacienda='INVERNADA')
    
    # Puede que haya o no datos de Invernada, pero no debe fallar.
    # Aserción: El resultado debe ser una lista (aunque esté vacía).
    assert isinstance(datos, list), "El scraper debe devolver una lista, incluso si está vacía."
    print(f"✅ ÉXITO: La búsqueda por INVERNADA finalizó con {len(datos)} registros.")

def test_caso_extremo_fecha_futura():
    """
    Prueba que el scraper no falla y devuelve una lista vacía para fechas futuras.
    """
    print("Ejecutando: test_caso_extremo_fecha_futura")
    fecha = "01/01/2099"
    datos = mag_scraper.scrape_mag(fecha, tipo_hacienda='TODOS')
    
    # Aserción: El resultado debe ser una lista vacía.
    assert not datos
    print("✅ ÉXITO ESPERADO: No se encontraron registros para una fecha futura.")

def test_manejo_de_timeout(monkeypatch):
    """
    Simula un timeout de red para verificar que el scraper no se cuelga
    y devuelve una lista vacía.
    """
    print("\nEjecutando: test_manejo_de_timeout")
    
    # "monkeypatch" nos permite reemplazar una función por otra durante la prueba.
    # Aquí, reemplazamos 'requests.Session.post' para que siempre lance un error de Timeout.
    def mock_post(*args, **kwargs):
        raise requests.exceptions.Timeout
    
    monkeypatch.setattr(requests.Session, "post", mock_post)
    
    datos = mag_scraper.scrape_mag("17/10/2025")
    assert not datos, "El scraper debería devolver una lista vacía en caso de timeout."
    print("✅ ÉXITO: El scraper manejó correctamente el timeout.")

def test_manejo_de_error_http(monkeypatch):
    """
    Simula un error del servidor (ej. 500 Internal Server Error) para verificar
    que el scraper no falla y devuelve una lista vacía.
    """
    print("\nEjecutando: test_manejo_de_error_http")

    # Simulamos una respuesta de error del servidor.
    class MockResponse:
        status_code = 500
        text = "Error interno del servidor"
        encoding = 'utf-8'

    def mock_post(*args, **kwargs):
        return MockResponse()

    monkeypatch.setattr(requests.Session, "post", mock_post)

    datos = mag_scraper.scrape_mag("17/10/2025")
    assert not datos, "El scraper debería devolver una lista vacía ante un error HTTP."
    print("✅ ÉXITO: El scraper manejó correctamente un error 500 del servidor.")