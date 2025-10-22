import pytest
import sqlite3
from database import db_manager
from datetime import datetime
import os

# --- Práctica Profesional: Fixtures ---
# Un "fixture" es una función que pytest ejecuta ANTES de cada prueba
# que la pida. Es perfecto para configurar una BBDD limpia.

@pytest.fixture
def db_conn():
    """
    Fixture de Pytest para crear una BBDD en memoria para cada prueba.
    """
    # Usamos ":memory:" para crear una BBDD temporal solo en RAM
    conn = sqlite3.connect(":memory:")
    
    # 1. Configuración: Creamos la tabla
    db_manager.crear_tabla(conn)
    
    # 2. "yield" entrega la conexión a la función de prueba
    yield conn
    
    # 3. Desmontaje: Cerramos la conexión después de la prueba
    conn.close()

# --- Pruebas del Gestor de Base de Datos ---

def test_crear_tabla(db_conn):
    """
    Prueba que la función crear_tabla realmente crea la tabla 'precios'.
    """
    print("Ejecutando: test_crear_tabla")
    cursor = db_conn.cursor()
    
    # Intentamos consultar el esquema de la tabla 'precios'
    try:
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='precios'")
        tabla = cursor.fetchone()
        assert tabla is not None, "La tabla 'precios' no fue creada."
        assert tabla[0] == "precios"
        
        # Verificamos que se creó el índice
        cursor.execute("SELECT name FROM sqlite_master WHERE type='index' AND name='idx_fecha_consulta'")
        indice = cursor.fetchone()
        assert indice is not None, "El índice 'idx_fecha_consulta' no fue creado."

    except sqlite3.Error as e:
        pytest.fail(f"La consulta de la tabla falló: {e}")

def test_insertar_datos_exitoso(db_conn):
    """
    Prueba que insertar_datos funciona y guarda los datos correctamente.
    """
    print("Ejecutando: test_insertar_datos_exitoso")
    datos_prueba = [{
        'fecha_consulta': '20/10/2025', 'fuente': 'Prueba', 'tipo_hacienda': 'TODOS',
        'categoria_original': 'NOVILLOS TEST', 'raza': 'MESTIZO', 'rango_peso': '400-430',
        'precio_max_kg': 3000.0, 'precio_min_kg': 2800.0, 'precio_promedio_kg': 2900.0,
        'cabezas': 50, 'kilos_total': 21000, 'importe_total': 60900000.0
    }]
    
    registros_insertados = db_manager.insertar_datos(db_conn, datos_prueba)
    
    # Afirmamos que la función reportó 1 inserción
    assert registros_insertados == 1
    
    # Verificamos que los datos están realmente en la BBDD
    cursor = db_conn.cursor()
    cursor.execute("SELECT * FROM precios WHERE categoria_original = 'NOVILLOS TEST'")
    fila = cursor.fetchone()
    
    assert fila is not None, "No se encontró el registro insertado."
    assert fila[5] == "NOVILLOS TEST" # Columna categoria_original
    assert fila[11] == 50 # Columna cabezas

def test_insertar_datos_vacios(db_conn):
    """
    Prueba que la función maneja correctamente una lista vacía.
    """
    print("Ejecutando: test_insertar_datos_vacios")
    registros_insertados = db_manager.insertar_datos(db_conn, [])
    
    # Afirmamos que no se insertó nada
    assert registros_insertados == 0

