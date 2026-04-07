"""
Fixtures de usuarios para tests.
"""
import pytest
import sys
import os

project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from shared_code.database import db_manager


@pytest.fixture
def user_data_factory():
    """Factory para crear datos de usuario válidos."""
    def factory(**overrides):
        defaults = {
            'email': 'test@example.com',
            'password': 'SecurePass123',
            'nombre': 'Test User',
            'telefono': '+541234567890',
            'ubicacion': 'Buenos Aires'
        }
        defaults.update(overrides)
        return defaults
    return factory


@pytest.fixture
def valid_registration_data():
    """Datos válidos para registro de usuario."""
    return {
        'email': 'newuser@example.com',
        'password': 'SecurePass123',
        'nombre': 'New Test User',
        'telefono': '+541112345678',
        'ubicacion': 'Córdoba'
    }


@pytest.fixture
def weak_password_data():
    """Datos con contraseña débil."""
    return {
        'email': 'weak@example.com',
        'password': '123',  # Muy corta
        'nombre': 'Weak User',
        'telefono': '+541112345678',
        'ubicacion': 'Rosario'
    }


@pytest.fixture
def invalid_email_data():
    """Datos con email inválido."""
    return {
        'email': 'not-an-email',
        'password': 'SecurePass123',
        'nombre': 'Invalid Email User',
        'telefono': '+541112345678',
        'ubicacion': 'Mendoza'
    }


@pytest.fixture
def valid_login_data():
    """Datos válidos para login."""
    return {
        'email': 'test@example.com',
        'password': 'SecurePass123',
        'remember': True
    }
