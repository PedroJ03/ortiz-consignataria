"""
Tests unitarios para db_manager.py

Migrado desde tests/test_db_manager.py
"""
import sys
import os
import pytest
import sqlite3
from datetime import datetime

project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from shared_code.database import db_manager

# Las fixtures conn_precios y conn_market ahora vienen de conftest.py
# pero las dejamos aquí para backward compatibility

@pytest.fixture(scope="function")
def conn_precios():
    """Conexión en memoria para la BD de Precios."""
    conn = sqlite3.connect(":memory:") 
    conn.row_factory = sqlite3.Row
    db_manager.crear_tablas_precios(conn) 
    yield conn
    conn.close()

@pytest.fixture(scope="function")
def conn_market():
    """Conexión en memoria para la BD del Marketplace."""
    conn = sqlite3.connect(":memory:") 
    conn.row_factory = sqlite3.Row
    db_manager.crear_tablas_market(conn) 
    yield conn
    conn.close()


# === TESTS BASE DE DATOS ANALÍTICA (Precios) ===

def test_crear_tablas_precios(conn_precios):
    cursor = conn_precios.cursor()
    
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='faena'")
    assert cursor.fetchone() is not None, "Tabla 'faena' no fue creada"
    
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='invernada'")
    assert cursor.fetchone() is not None, "Tabla 'invernada' no fue creada"

def test_insertar_y_obtener_faena(conn_precios):
    datos_ejemplo = [{
        'fecha_consulta_inicio': '17/11/2025', 
        'categoria_original': 'NOVILLOS', 
        'precio_promedio_kg': 1000
    }]
    count = db_manager.insertar_datos_faena(conn_precios, datos_ejemplo)
    assert count == 1
    
    # Probar que el parser de fecha funciona ('17/11/2025' -> '2025-11-17')
    cursor = conn_precios.cursor()
    cursor.execute("SELECT * FROM faena WHERE fecha_consulta = '2025-11-17'")
    fila = cursor.fetchone()
    
    assert fila is not None
    assert fila['categoria_original'] == 'NOVILLOS'
    assert fila['precio_promedio_kg'] == 1000.0
    
    # Probar la lectura mediante la API interna
    data_historica = db_manager.get_faena_historico(conn_precios, '2025-11-01', '2025-11-30')
    assert len(data_historica) == 1
    assert data_historica[0]['precio_promedio_kg'] == 1000.0


# === TESTS BASE DE DATOS TRANSACCIONAL (Marketplace) ===

def test_crear_tablas_market(conn_market):
    cursor = conn_market.cursor()
    tablas = ['users', 'publicaciones', 'media_lotes']
    for t in tablas:
        cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{t}'")
        assert cursor.fetchone() is not None, f"Tabla '{t}' no fue creada"

def test_gestion_usuarios(conn_market):
    # Crear usuario
    user_id = db_manager.crear_usuario(conn_market, "test@mail.com", "hashedpass", "Juan", "123", "PBA")
    assert user_id > 0
    
    # Leer usuario por email
    user = db_manager.get_usuario_por_email(conn_market, "test@mail.com")
    assert user is not None
    assert user['nombre_completo'] == "Juan"
    assert user['es_admin'] == 0 # Por defecto no es admin
    
    # Toggle Admin
    exito = db_manager.toggle_user_admin(conn_market, user_id)
    assert exito is True
    
    user_admin = db_manager.get_usuario_por_id(conn_market, user_id)
    assert user_admin['es_admin'] == 1

def test_gestion_publicaciones(conn_market):
    user_id = db_manager.crear_usuario(conn_market, "pub@mail.com", "pass", "Pub", "123", "PBA")
    
    pub_id = db_manager.crear_publicacion(
        conn_market, user_id, "Lote Terneros", "Test desc", "Terneros",
        "Aberdeen", 50, 200, "Macho", "Buenos Aires", "Olavarría", "YouTube"
    )
    assert pub_id > 0
    
    # Obtener Publicación Activa
    activos = db_manager.obtener_publicaciones(conn_market, activo=True)
    assert len(activos) == 1
    assert activos[0]['titulo'] == "Lote Terneros"
    
    # Toggle (Desactivar)
    db_manager.toggle_publicacion_activa(conn_market, pub_id)
    activos_vacios = db_manager.obtener_publicaciones(conn_market, activo=True)
    assert len(activos_vacios) == 0
    
    # Verificar desde Admin (Puede ver inactivos)
    admin_view = db_manager.get_all_publicaciones_admin(conn_market)
    assert len(admin_view) == 1
    assert admin_view[0]['activo'] == 0
    
    # Probar eliminación
    db_manager.eliminar_publicacion(conn_market, pub_id)
    assert len(db_manager.get_all_publicaciones_admin(conn_market)) == 0

def test_guardar_media(conn_market):
    user_id = db_manager.crear_usuario(conn_market, "media@mail.com", "pass", "Media", "123", "PBA")
    pub_id = db_manager.crear_publicacion(conn_market, user_id, "Lote", "D", "C", "R", 1, 1, "M", "P", "L", "")
    
    # Insertar 2 Archivos (Video e Imagen)
    db_manager.guardar_archivo_media(conn_market, pub_id, "video.mp4", "video")
    db_manager.guardar_archivo_media(conn_market, pub_id, "foto.jpg", "image")
    
    # Recuperar Media
    galeria = db_manager.obtener_media_por_publicacion(conn_market, pub_id)
    assert len(galeria) == 2
    
    archivos = [m['filename'] for m in galeria]
    assert "video.mp4" in archivos
    assert "foto.jpg" in archivos
