import pytest
import main
from datetime import datetime
import sqlite3
import requests # Necesario para simular el error de red

# --- Práctica Profesional: Mocking (Simulación) ---
# Usamos 'monkeypatch' de pytest para simular (mockear) funciones.
# No queremos que nuestras pruebas de 'main' llamen al scraper real
# (lento y depende de internet) ni a la BBDD real.

# Mock: Datos de prueba que simula devolver el scraper
MOCK_SCRAPER_DATA = [{
    'fecha_consulta': '20/10/2025', 'fuente': 'MAG_Mock', 'tipo_hacienda': 'TODOS',
    'categoria_original': 'NOVILLOS MOCK', 'raza': 'MESTIZO', 'rango_peso': '400-430',
    'precio_max_kg': 3000.0, 'precio_min_kg': 2800.0, 'precio_promedio_kg': 2900.0,
    'cabezas': 50, 'kilos_total': 21000, 'importe_total': 60900000.0
}]

# --- Pruebas del Orquestador (main.py) ---

def test_ejecutar_proceso_exitoso(monkeypatch, capsys):
    """
    Prueba el "camino feliz": el scraper devuelve datos y la BBDD los guarda.
    'capsys' es un fixture de pytest que captura los 'print'.
    """
    print("Ejecutando: test_ejecutar_proceso_exitoso")

    # 1. Simular (mock) la función scrape_mag
    def mock_scrape_mag(*args, **kwargs):
        print("Mock scrape_mag llamado")
        return MOCK_SCRAPER_DATA

    # 2. Simular (mock) la función insertar_datos
    def mock_insertar_datos(*args, **kwargs):
        print("Mock insertar_datos llamado")
        # Aseguramos que reciba la conexión simulada (aunque no la usemos aquí)
        assert args[0] is not None, "insertar_datos no recibió la conexión"
        return len(MOCK_SCRAPER_DATA)

    # 3. Simular (mock) la función crear_tabla
    def mock_crear_tabla(*args, **kwargs):
        print("Mock crear_tabla llamado")
        assert args[0] is not None, "crear_tabla no recibió la conexión"
        pass # No hace nada

    # 4. Simular (mock) la conexión a BBDD para que no haga nada
    class MockConnection:
        def close(self): print("Mock connection closed")
    def mock_get_connection():
        print("Mock get_connection llamado")
        return MockConnection()

    # 5. Aplicar los mocks
    monkeypatch.setattr("scrapers.mag_scraper.scrape_mag", mock_scrape_mag)
    monkeypatch.setattr("database.db_manager.get_db_connection", mock_get_connection)
    monkeypatch.setattr("database.db_manager.crear_tabla", mock_crear_tabla)
    monkeypatch.setattr("database.db_manager.insertar_datos", mock_insertar_datos)

    # 6. Ejecutar la función principal
    main.ejecutar_proceso_completo("20/10/2025")

    # 7. Verificar la salida
    captured = capsys.readouterr()
    assert "PROCESO COMPLETO FINALIZADO" in captured.out
    assert "Registros insertados: 1" in captured.out
    assert "Conexión a la base de datos cerrada." in captured.out # Verificar cierre

def test_ejecutar_proceso_scraper_falla(monkeypatch, capsys):
    """
    Prueba el "camino triste": el scraper falla con una excepción.
    """
    print("Ejecutando: test_ejecutar_proceso_scraper_falla")

    # 1. Simular (mock) que el scraper lanza un error
    def mock_scrape_mag_falla(*args, **kwargs):
        print("Mock scrape_mag (falla) llamado")
        raise requests.RequestException("Error de red simulado")

    monkeypatch.setattr("scrapers.mag_scraper.scrape_mag", mock_scrape_mag_falla)

    # 2. Simular funciones de BBDD
    class MockConnection:
        def close(self): print("Mock connection closed")
    def mock_get_connection(): return MockConnection()
    def mock_crear_tabla(*args, **kwargs): pass

    monkeypatch.setattr("database.db_manager.get_db_connection", mock_get_connection)
    monkeypatch.setattr("database.db_manager.crear_tabla", mock_crear_tabla)

    # 3. Ejecutar la función
    main.ejecutar_proceso_completo("20/10/2025")

    # 4. Verificar que se capturó el error
    captured = capsys.readouterr()
    assert "ERROR CRÍTICO (Scraper/Red)" in captured.out
    assert "Error de red simulado" in captured.out
    assert "PROCESO FINALIZADO (CON ERRORES)" in captured.out
    assert "Conexión a la base de datos cerrada." in captured.out # Verificar cierre

def test_ejecutar_proceso_db_falla(monkeypatch, capsys):
    """
    Prueba el "camino triste": la BBDD falla al insertar.
    """
    print("Ejecutando: test_ejecutar_proceso_db_falla")

    # 1. Simular que el scraper funciona
    def mock_scrape_mag(*args, **kwargs):
        return MOCK_SCRAPER_DATA

    # 2. Simular que la BBDD lanza un error al insertar
    def mock_insertar_datos_falla(*args, **kwargs):
        print("Mock insertar_datos (falla) llamado")
        raise sqlite3.Error("Error de BBDD simulado")

    # 3. Simular el resto de funciones de BBDD
    class MockConnection:
        def close(self): print("Mock connection closed")
    def mock_get_connection(): return MockConnection()
    def mock_crear_tabla(*args, **kwargs): pass

    monkeypatch.setattr("scrapers.mag_scraper.scrape_mag", mock_scrape_mag)
    monkeypatch.setattr("database.db_manager.get_db_connection", mock_get_connection)
    monkeypatch.setattr("database.db_manager.crear_tabla", mock_crear_tabla)
    monkeypatch.setattr("database.db_manager.insertar_datos", mock_insertar_datos_falla)

    # 4. Ejecutar la función
    main.ejecutar_proceso_completo("20/10/2025")

    # 5. Verificar que se capturó el error
    captured = capsys.readouterr()
    assert "ERROR CRÍTICO (Base de Datos)" in captured.out
    assert "Error de BBDD simulado" in captured.out
    assert "PROCESO FINALIZADO (CON ERRORES)" in captured.out
    assert "Conexión a la base de datos cerrada." in captured.out # Verificar cierre

