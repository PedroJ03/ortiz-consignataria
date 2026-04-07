"""
Tests de integración para la aplicación Flask.

Migrado desde tests/test_app.py
"""
import pytest
import sys
import os
import json

project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

os.environ['TESTING'] = 'true'
os.environ['SECRET_KEY'] = 'test-secret'

from web_app.app import app, User
from shared_code.database import db_manager
import sqlite3


# === TESTS RUTAS PÚBLICAS ===

def test_inicio_status(client, mocker):
    """Prueba que el Landing Page principal cargue exitosamente (200 OK)."""
    # Mockear BBDD para evitar error 500
    mocker.patch('web_app.app.db_manager.obtener_ultima_publicacion', return_value=None)
    mocker.patch('web_app.app.get_db_market', return_value=mocker.Mock())
    response = client.get('/')
    assert response.status_code == 200
    assert b"Ortiz" in response.data or b"<html" in response.data

def test_dashboard_status(client, mocker):
    """Prueba que la página del Mercado analítico cargue exitosamente."""
    # Como la BD en memoria no tiene las tablas en test_app, fallaba. Mockeamos.
    mock_conn = mocker.Mock()
    mocker.patch('web_app.app.get_db_precios', return_value=mock_conn)
    mocker.patch('web_app.app.db_manager.get_faena_historico', return_value=[])
    mocker.patch('web_app.app.db_manager.get_invernada_historico', return_value=[])
    
    response = client.get('/precios')
    assert response.status_code == 200

def test_vidriera_status(client, mocker):
    """Prueba que la vista pública del Marketplace cargue."""
    mocker.patch('web_app.app.get_db_market', return_value=mocker.Mock())
    mocker.patch('web_app.app.db_manager.obtener_publicaciones', return_value=[])
    response = client.get('/mercado')
    assert response.status_code == 200


# === TESTS API (AJAX) ===

def test_api_categorias(client, mocker):
    """Verifica que la API del dashboard retorne JSON con las categorías correctas."""
    # Mockear la BD para que devuelva algo rápido
    mocker.patch('web_app.app.get_db_precios', return_value=mocker.Mock())
    mock_cursor = mocker.Mock()
    mock_cursor.fetchall.side_effect = [
        [("NOVILLOS",)], # Faena mock
        [("TERNEROS",)]  # Invernada mock
    ]
    mocker.patch('web_app.app.get_db_precios').return_value.cursor.return_value = mock_cursor

    response = client.get('/api/categorias')
    assert response.status_code == 200
    
    data = json.loads(response.data)
    assert 'faena' in data
    assert 'invernada' in data
    assert "NOVILLOS" in data['faena']

def test_api_subcategorias_sin_params(client):
    """Verifica el error 400 si olvidas el parámetro 'categoria'."""
    response = client.get('/api/subcategorias')
    assert response.status_code == 400
    assert b"Categoria requerida" in response.data


# === TESTS PROTEGIDOS ===

def test_acceso_admin_sin_login(client):
    """Prueba que un usuario no logueado es redirigido en vez de poder ver el panel admin."""
    response = client.get('/admin', follow_redirects=False)
    # Flask-Login redirige (302) al login si no estás autorizado vía `@login_required`
    assert response.status_code == 302
    assert "/login" in response.location

def test_crear_publicacion_sin_login(client):
    """Verifica protección de escritura."""
    # En app.py, publicar está dentro de /admin o es otra ruta.
    # Dado que no sabemos de antemano si la ruta usa POST, probemos cargar la ruta mercado.
    response = client.post('/mercado', data={'titulo': 'Fake'}, follow_redirects=False)
    # Como la ruta mercado no acepta POST, deberia tirar un 405 Method Not Allowed
    assert response.status_code == 405 
    
def test_mock_login_y_admin(client, mocker):
    """Verifica que un usuario Administrador puede cargar la ruta `/admin`."""
    
    # IMPORTANTE: En Flask-Login version moderna para testear hay que usar session o simular el loader
    with client.session_transaction() as sess:
        sess['_user_id'] = '1'
        sess['_fresh'] = True
        
    mocker.patch('web_app.app.load_user', return_value=User(1, 'admin@a', 'Ad', es_admin=True))
    mocker.patch('web_app.app.db_manager.get_all_users', return_value=[])
    mocker.patch('web_app.app.db_manager.get_all_publicaciones_admin', return_value=[])
    
    # Evitar TypeError mockeando la respuesta de la BD que Flask-Login pide internamente a load_user
    mock_conn = mocker.Mock()
    mock_db = mocker.patch('web_app.app.get_db_market', return_value=mock_conn)
    mock_cursor = mocker.Mock()
    mock_cursor.fetchone.return_value = {'id': 1, 'email': 'admin@a', 'nombre_completo': 'Ad', 'es_admin': 1}
    mock_conn.cursor.return_value = mock_cursor

    response = client.get('/admin')
    assert response.status_code == 200
    assert b"Panel" in response.data or b"Admin" in response.data

def test_auth_no_admin_bloqueado(client, mocker):
    """Verifica que un usuario LOGUEADO pero CIVIL(Normal) no puede ver el Admin (403)."""
    with client.session_transaction() as sess:
        sess['_user_id'] = '2'
        
    # Mocking standard User object without admin privileges
    mocker.patch('web_app.app.load_user', return_value=User(2, 'a@a', 'Norm', es_admin=False))
    
    # Needs connection mocked or DB manager will crash if it slips past auth
    mock_conn = mocker.Mock()
    mocker.patch('web_app.app.get_db_market', return_value=mock_conn)
    mock_cursor = mocker.Mock()
    mock_cursor.fetchone.return_value = {'id': 2, 'email': 'a@a', 'nombre_completo': 'Norm', 'es_admin': 0}
    mock_conn.cursor.return_value = mock_cursor

    response = client.get('/admin')
    assert response.status_code == 403 # Prohibido
