"""
Configuración global de pytest y fixtures compartidos.
"""
import pytest
import tempfile
import os
import sys
import sqlite3
from unittest.mock import MagicMock

# --- Configuración de paths ---
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Setear variables de entorno para testing antes de importar app
os.environ['TESTING'] = 'true'
os.environ['SECRET_KEY'] = 'test-secret-key-for-testing-only'
os.environ['CLIENT_EMAILS'] = 'test@example.com'

from web_app.app import app as flask_app, User
from shared_code.database import db_manager


# =============================================================================
# FIXTURES DE APLICACIÓN FLASK
# =============================================================================

@pytest.fixture
def app():
    """Crea la aplicación Flask configurada para testing."""
    flask_app.config.update({
        'TESTING': True,
        'WTF_CSRF_ENABLED': False,  # Deshabilitar CSRF para tests
        'UPLOAD_FOLDER': tempfile.mkdtemp(),
        'MAX_CONTENT_LENGTH': 100 * 1024 * 1024,  # 100MB
    })
    
    # Crear directorio de uploads
    os.makedirs(flask_app.config['UPLOAD_FOLDER'], exist_ok=True)
    
    yield flask_app
    
    # Cleanup
    if os.path.exists(flask_app.config['UPLOAD_FOLDER']):
        import shutil
        shutil.rmtree(flask_app.config['UPLOAD_FOLDER'])


@pytest.fixture
def client(app):
    """Crea un cliente de test para la aplicación Flask."""
    return app.test_client()


@pytest.fixture
def app_context(app):
    """Provee el contexto de aplicación Flask."""
    with app.app_context():
        yield app


# =============================================================================
# FIXTURES DE BASE DE DATOS
# =============================================================================

@pytest.fixture(scope="function")
def db_precios():
    """Crea una base de datos de precios en memoria para cada test."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    db_manager.crear_tablas_precios(conn)
    yield conn
    conn.close()


@pytest.fixture(scope="function")
def db_market():
    """Crea una base de datos de marketplace en memoria para cada test."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    db_manager.crear_tablas_market(conn)
    yield conn
    conn.close()


@pytest.fixture
def mock_db_precios(mocker):
    """Mock para la conexión a la base de datos de precios."""
    mock_conn = mocker.Mock()
    mock_conn.cursor.return_value = mocker.Mock()
    mocker.patch('web_app.app.get_db_precios', return_value=mock_conn)
    return mock_conn


@pytest.fixture
def mock_db_market(mocker):
    """Mock para la conexión a la base de datos de marketplace."""
    mock_conn = mocker.Mock()
    mock_cursor = mocker.Mock()
    mock_conn.cursor.return_value = mock_cursor
    mocker.patch('web_app.app.get_db_market', return_value=mock_conn)
    return mock_conn


# =============================================================================
# FIXTURES DE USUARIOS
# =============================================================================

@pytest.fixture
def test_user(db_market):
    """Crea un usuario de prueba verificado."""
    user_id = db_manager.crear_usuario(
        db_market,
        email="test@example.com",
        password_hash="hashed_password_test",
        nombre="Test User",
        telefono="1234567890",
        ubicacion="Buenos Aires"
    )
    # Marcar como verificado
    cursor = db_market.cursor()
    cursor.execute("UPDATE users SET is_verified = 1 WHERE id = ?", (user_id,))
    db_market.commit()
    
    return {
        'id': user_id,
        'email': 'test@example.com',
        'password_hash': 'hashed_password_test',
        'nombre': 'Test User',
        'telefono': '1234567890',
        'ubicacion': 'Buenos Aires',
        'is_verified': 1,
        'es_admin': 0
    }


@pytest.fixture
def unverified_user(db_market):
    """Crea un usuario de prueba NO verificado."""
    user_id = db_manager.crear_usuario(
        db_market,
        email="unverified@example.com",
        password_hash="hashed_password_test",
        nombre="Unverified User",
        telefono="0987654321",
        ubicacion="Córdoba"
    )
    
    return {
        'id': user_id,
        'email': 'unverified@example.com',
        'password_hash': 'hashed_password_test',
        'nombre': 'Unverified User',
        'telefono': '0987654321',
        'ubicacion': 'Córdoba',
        'is_verified': 0,
        'es_admin': 0
    }


@pytest.fixture
def admin_user(db_market):
    """Crea un usuario administrador de prueba."""
    user_id = db_manager.crear_usuario(
        db_market,
        email="admin@example.com",
        password_hash="hashed_admin_password",
        nombre="Admin User",
        telefono="1111111111",
        ubicacion="Admin Location"
    )
    # Marcar como admin y verificado
    cursor = db_market.cursor()
    cursor.execute("UPDATE users SET es_admin = 1, is_verified = 1 WHERE id = ?", (user_id,))
    db_market.commit()
    
    return {
        'id': user_id,
        'email': 'admin@example.com',
        'password_hash': 'hashed_admin_password',
        'nombre': 'Admin User',
        'telefono': '1111111111',
        'ubicacion': 'Admin Location',
        'is_verified': 1,
        'es_admin': 1
    }


@pytest.fixture
def logged_in_client(client, mocker, test_user):
    """Cliente con un usuario logueado."""
    with client.session_transaction() as sess:
        sess['_user_id'] = str(test_user['id'])
        sess['_fresh'] = True
    
    # Mock load_user
    user_obj = User(
        id=test_user['id'],
        email=test_user['email'],
        nombre=test_user['nombre'],
        es_admin=bool(test_user['es_admin'])
    )
    mocker.patch('web_app.app.load_user', return_value=user_obj)
    
    return client


@pytest.fixture
def logged_in_admin_client(client, mocker, admin_user):
    """Cliente con un administrador logueado."""
    with client.session_transaction() as sess:
        sess['_user_id'] = str(admin_user['id'])
        sess['_fresh'] = True
    
    # Mock load_user
    user_obj = User(
        id=admin_user['id'],
        email=admin_user['email'],
        nombre=admin_user['nombre'],
        es_admin=True
    )
    mocker.patch('web_app.app.load_user', return_value=user_obj)
    
    return client


# =============================================================================
# FIXTURES DE DIRECTORIOS TEMPORALES
# =============================================================================

@pytest.fixture
def temp_dir():
    """Provee un directorio temporal para los tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def temp_upload_dir(temp_dir):
    """Crea un directorio de uploads temporal."""
    upload_dir = os.path.join(temp_dir, 'uploads')
    os.makedirs(upload_dir, exist_ok=True)
    return upload_dir


# =============================================================================
# FIXTURES DE VIDEO (MOCKS)
# =============================================================================

@pytest.fixture
def mock_video_clip(mocker):
    """Mock de VideoFileClip para tests de video."""
    mock_clip = mocker.Mock()
    mock_clip.duration = 30.0
    mock_clip.h = 480
    mock_clip.w = 640
    mock_clip.fps = 30
    mock_clip.audio = mocker.Mock()
    
    # Configurar subclipped para devolver otro mock
    mock_subclip = mocker.Mock()
    mock_subclip.duration = 60.0
    mock_subclip.h = 480
    mock_subclip.w = 640
    mock_subclip.audio = mocker.Mock()
    mock_clip.subclipped.return_value = mock_subclip
    
    # Configurar resized
    mock_resized = mocker.Mock()
    mock_resized.duration = 30.0
    mock_resized.h = 480
    mock_resized.w = 640
    mock_resized.audio = mocker.Mock()
    mock_clip.resized.return_value = mock_resized
    
    mock_video_class = mocker.patch('web_app.utils.video_optimizer_v2.VideoFileClip')
    mock_video_class.return_value = mock_clip
    
    return mock_clip


@pytest.fixture
def mock_subprocess(mocker):
    """Mock para subprocess.run."""
    mock_run = mocker.patch('web_app.utils.video_optimizer_v2.subprocess.run')
    return mock_run


# =============================================================================
# CONFIGURACIÓN DE PYTEST
# =============================================================================

def pytest_configure(config):
    """Configuración adicional de pytest."""
    config.addinivalue_line(
        "markers", "slow: marca tests que son lentos (ej. tests de video)"
    )
    config.addinivalue_line(
        "markers", "integration: marca tests de integración"
    )
    config.addinivalue_line(
        "markers", "unit: marca tests unitarios"
    )


# Plugins de pytest para fixtures adicionales
pytest_plugins = []
