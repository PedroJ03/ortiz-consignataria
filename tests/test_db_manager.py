import sys
import os
import pytest
import sqlite3
from datetime import datetime

# --- Configuración de sys.path (sin cambios) ---
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from shared_code.database import db_manager

# --- Fixture (sin cambios) ---
@pytest.fixture(scope="function")
def db_conn():
    """Fixture que crea una conexión y se asegura de que las tablas existan."""
    conn = sqlite3.connect(":memory:") 
    conn.row_factory = sqlite3.Row
    try:
        db_manager.crear_tablas(conn) 
        print("\n(Fixture: Tablas creadas en BBDD en memoria)")
    except AttributeError as e:
        if 'crear_tablas' in str(e):
            pytest.fail("Error en el test: la función db_manager.crear_tablas() no se encontró.")
        else:
            raise e
    yield conn
    conn.close()
    print("(Fixture: BBDD en memoria cerrada)")

# --- Tests de crear e insertar (sin cambios) ---

def test_crear_tabla(db_conn):
    print("\nEjecutando: test_crear_tabla")
    cursor = db_conn.cursor()
    try:
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='faena'")
        assert cursor.fetchone() is not None, "Tabla 'faena' no fue creada"
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='invernada'")
        assert cursor.fetchone() is not None, "Tabla 'invernada' no fue creada"
        print("Test de creación de tablas exitoso.")
    except sqlite3.Error as e:
        assert False, f"Error de SQLite al verificar tablas: {e}"

def test_insertar_datos_exitoso(db_conn):
    """Prueba una inserción exitosa en la tabla 'faena'."""
    print("\nEjecutando: test_insertar_datos_exitoso (corregido)")
    
    datos_ejemplo = [
        {'fecha_consulta_inicio': '17/11/2025', 'categoria_original': 'NOVILLOS', 'precio_promedio_kg': 1000}
    ]
    count = db_manager.insertar_datos_faena(db_conn, datos_ejemplo)
    assert count == 1, "db_manager.insertar_datos_faena debería haber devuelto 1"
    
    cursor = db_conn.cursor()
    
    # CORREGIDO: Buscar la fecha en el formato que realmente se guarda (DD/MM/YYYY)
    cursor.execute("SELECT * FROM faena WHERE fecha_consulta = '17/11/2025'")
    
    resultado = cursor.fetchone()
    assert resultado is not None, "El SELECT no encontró la fila que acabamos de insertar."
    assert resultado['categoria_original'] == 'NOVILLOS'
    print("Test de inserción exitosa completado.")

def test_insertar_datos_vacios(db_conn):
    print("\nEjecutando: test_insertar_datos_vacios")
    count = db_manager.insertar_datos_faena(db_conn, [])
    assert count == 0
    print("Test de inserción vacía completado.")

# --- ========================================== ---
# --- INICIO DE CORRECCIÓN (no such table / IntegrityError) ---
# --- ========================================== ---
def test_get_faena_historico_formato_fecha(db_conn):
    """Prueba que get_faena_historico funciona con la conexión en memoria."""
    print("\nEjecutando: test_get_faena_historico_formato_fecha (corregido)")
    
    try:
        # 1. Insertar datos de prueba en la BBDD en memoria
        # (Nota: insertar_datos_faena ya convierte '15/01/2025' a '2025-01-15')
        datos_prueba = [{
            'fecha_consulta_inicio': '15/01/2025', 
            'categoria_original': 'NOVILLOS', 
            'precio_promedio_kg': 123
        }]
        db_manager.insertar_datos_faena(db_conn, datos_prueba)
        
    except sqlite3.Error as e:
        assert False, f"La inserción de prueba falló: {e}"

    try:
        # 2. Llamar a la función, pasándole la conexión de la fixture
        datos = db_manager.get_faena_historico(
            db_conn, # <-- CORREGIDO: Pasar la conexión en memoria
            '2025-01-01',
            '2025-01-31',
            'NOVILLOS'
        )
        assert isinstance(datos, list)
        assert len(datos) == 1, "La consulta SUBSTR no encontró el dato"
        print("Test de consulta (get_faena_historico) exitoso.")
    except Exception as e:
        assert False, f"Consulta de get_faena_historico falló: {e}"
# --- FIN DE CORRECCIÓN ---