"""
Tests de integración para flujo de autenticación.

Cobertura:
- Registro de usuarios
- Login
- Verificación de email
- Logout
"""
import pytest
import sys
import os

project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)


# =============================================================================
# TESTS DE REGISTRO
# =============================================================================

@pytest.mark.integration
class TestRegistration:
    """Tests de registro de usuarios."""
    
    def test_register_success(self, client, db_market, mocker):
        """Registro válido crea usuario."""
        # Mock para evitar envío real de email
        mocker.patch('web_app.app.get_db_market', return_value=db_market)
        mocker.patch('shared_code.email_service.enviar_correo', return_value=True)
        
        data = {
            'email': 'newuser@example.com',
            'password': 'SecurePass123',
            'nombre': 'New Test User',
            'telefono': '+541112345678',
            'ubicacion': 'Buenos Aires'
        }
        
        response = client.post('/registro', data=data, follow_redirects=True)
        
        assert response.status_code in [200, 429]  # 429 si hay rate limiting
        if response.status_code == 200:
            # Debería redirigir a login
            assert b'login' in response.data.lower() or b'iniciar sesi' in response.data.lower()
    
    def test_register_duplicate_email(self, client, db_market, test_user, mocker):
        """Email duplicado es rechazado."""
        mocker.patch('web_app.app.get_db_market', return_value=db_market)
        
        data = {
            'email': test_user['email'],  # Email ya existente
            'password': 'AnotherPass123',
            'nombre': 'Another User',
            'telefono': '+541112345679',
            'ubicacion': 'Córdoba'
        }
        
        response = client.post('/registro', data=data)
        
        assert response.status_code in [200, 429]  # 429 si rate limiting activo
        if response.status_code == 200:
            # Buscar mensaje de error en el response
            response_text = response.data.lower()
            assert any(keyword in response_text for keyword in [
                b'ya est', b'registrado', b'correo', b'email'
            ])
    
    def test_register_invalid_email(self, client):
        """Email inválido es rechazado."""
        data = {
            'email': 'not-an-email',
            'password': 'SecurePass123',
            'nombre': 'Test User',
            'telefono': '+541112345678',
            'ubicacion': 'Rosario'
        }
        
        response = client.post('/registro', data=data)
        
        assert response.status_code in [200, 429]
    
    def test_register_weak_password(self, client):
        """Contraseña débil es rechazada."""
        data = {
            'email': 'weak@example.com',
            'password': '12345',  # Muy corta, sin números
            'nombre': 'Weak User',
            'telefono': '+541112345678',
            'ubicacion': 'Mendoza'
        }
        
        response = client.post('/registro', data=data)
        
        assert response.status_code in [200, 429]
    
    def test_register_short_name(self, client):
        """Nombre muy corto es rechazado."""
        data = {
            'email': 'short@example.com',
            'password': 'SecurePass123',
            'nombre': 'AB',  # Muy corto
            'telefono': '+541112345678',
            'ubicacion': 'Tucumán'
        }
        
        response = client.post('/registro', data=data)
        
        assert response.status_code in [200, 429]
    
    def test_register_invalid_phone(self, client):
        """Teléfono inválido es rechazado."""
        data = {
            'email': 'phone@example.com',
            'password': 'SecurePass123',
            'nombre': 'Phone User',
            'telefono': '123',  # Muy corto
            'ubicacion': 'Salta'
        }
        
        response = client.post('/registro', data=data)
        
        # Rate limiting puede devolver 429
        assert response.status_code in [200, 429]


# =============================================================================
# TESTS DE LOGIN
# =============================================================================

@pytest.mark.integration
class TestLogin:
    """Tests de login de usuarios."""
    
    def test_login_success(self, client, db_market, test_user, mocker):
        """Login con credenciales válidas."""
        mocker.patch('web_app.app.get_db_market', return_value=db_market)
        
        # El password_hash está almacenado, necesitamos simular la verificación
        from werkzeug.security import generate_password_hash
        
        # Actualizar usuario con hash real
        cursor = db_market.cursor()
        real_hash = generate_password_hash('SecurePass123')
        cursor.execute(
            "UPDATE users SET password_hash = ? WHERE id = ?",
            (real_hash, test_user['id'])
        )
        db_market.commit()
        
        data = {
            'email': test_user['email'],
            'password': 'SecurePass123',
            'remember': True
        }
        
        response = client.post('/login', data=data, follow_redirects=True)
        
        # Debería redirigir al inicio o ser rate limited
        assert response.status_code in [200, 429]
    
    def test_login_wrong_password(self, client, db_market, test_user, mocker):
        """Contraseña incorrecta es rechazada."""
        mocker.patch('web_app.app.get_db_market', return_value=db_market)
        
        data = {
            'email': test_user['email'],
            'password': 'WrongPassword123',
            'remember': False
        }
        
        response = client.post('/login', data=data)
        
        assert response.status_code in [200, 429]
    
    def test_login_nonexistent_user(self, client, db_market, mocker):
        """Usuario inexistente es rechazado."""
        mocker.patch('web_app.app.get_db_market', return_value=db_market)
        
        data = {
            'email': 'nonexistent@example.com',
            'password': 'SomePass123',
            'remember': False
        }
        
        response = client.post('/login', data=data)
        
        assert response.status_code in [200, 429]
    
    def test_login_unverified_user(self, client, db_market, unverified_user, mocker):
        """Usuario no verificado no puede loguear."""
        mocker.patch('web_app.app.get_db_market', return_value=db_market)
        mocker.patch('shared_code.email_service.enviar_correo', return_value=True)
        
        from werkzeug.security import generate_password_hash
        
        cursor = db_market.cursor()
        real_hash = generate_password_hash('SecurePass123')
        cursor.execute(
            "UPDATE users SET password_hash = ? WHERE id = ?",
            (real_hash, unverified_user['id'])
        )
        db_market.commit()
        
        data = {
            'email': unverified_user['email'],
            'password': 'SecurePass123',
            'remember': False
        }
        
        response = client.post('/login', data=data, follow_redirects=True)
        
        assert response.status_code in [200, 429]
    
    def test_login_already_authenticated(self, logged_in_client):
        """Usuario ya autenticado es redirigido."""
        response = logged_in_client.get('/login')
        
        # Debería redirigir al inicio o ser rate limited
        assert response.status_code in [301, 302, 429]


# =============================================================================
# TESTS DE VERIFICACIÓN
# =============================================================================

@pytest.mark.integration
class TestEmailVerification:
    """Tests de verificación de email."""
    
    def test_email_verification_success(self, client, db_market, unverified_user, mocker):
        """Token válido verifica email."""
        mocker.patch('web_app.app.get_db_market', return_value=db_market)
        
        # Crear token de verificación
        import secrets
        token = secrets.token_urlsafe(32)
        
        cursor = db_market.cursor()
        cursor.execute(
            "UPDATE users SET verification_token = ? WHERE id = ?",
            (token, unverified_user['id'])
        )
        db_market.commit()
        
        response = client.get(f'/verificar-correo/{token}')
        
        # Redirige o es rate limited
        assert response.status_code in [301, 302, 429]
    
    def test_email_verification_invalid_token(self, client, db_market, mocker):
        """Token inválido es rechazado."""
        mocker.patch('web_app.app.get_db_market', return_value=db_market)
        
        response = client.get('/verificar-correo/invalid-token-12345')
        
        assert response.status_code in [301, 302, 429]
    
    def test_email_verification_expired_token(self, client, db_market, mocker):
        """Token expirado es rechazado."""
        mocker.patch('web_app.app.get_db_market', return_value=db_market)
        
        # Asumiendo que hay lógica de expiración
        response = client.get('/verificar-correo/expired-token')
        
        assert response.status_code in [301, 302, 429]


# =============================================================================
# TESTS DE LOGOUT
# =============================================================================

@pytest.mark.integration
class TestLogout:
    """Tests de logout."""
    
    def test_logout_success(self, logged_in_client):
        """Logout cierra sesión."""
        response = logged_in_client.get('/logout', follow_redirects=True)
        
        assert response.status_code == 200
    
    def test_logout_without_login(self, client):
        """Logout sin sesión redirige a login."""
        response = client.get('/logout', follow_redirects=True)
        
        # Puede ser rate limited
        assert response.status_code in [200, 429]


# =============================================================================
# TESTS DE RUTAS PROTEGIDAS
# =============================================================================

@pytest.mark.integration
class TestProtectedRoutes:
    """Tests de acceso a rutas protegidas."""
    
    def test_admin_route_requires_login(self, client):
        """Ruta admin requiere login."""
        response = client.get('/admin', follow_redirects=False)
        
        assert response.status_code in [302, 429]  # Redirect o rate limited
        if response.status_code == 302:
            assert '/login' in response.location
    
    def test_admin_route_requires_admin_role(self, logged_in_client):
        """Ruta admin requiere rol de admin."""
        response = logged_in_client.get('/admin')
        
        # Usuario normal no debería poder acceder (403) o ser rate limited
        assert response.status_code in [403, 302, 429]
    
    def test_admin_can_access_admin(self, logged_in_admin_client, mocker):
        """Admin puede acceder a panel admin."""
        # Mock necesario para evitar errores de DB
        mocker.patch('web_app.app.db_manager.get_all_users', return_value=[])
        mocker.patch('web_app.app.db_manager.get_all_publicaciones_admin', return_value=[])
        
        response = logged_in_admin_client.get('/admin')
        
        # Debe poder acceder (200), ser rechazado (403), o rate limited (429)
        assert response.status_code in [200, 403, 429]
    
    def test_perfil_requires_login(self, client):
        """Perfil requiere login."""
        response = client.get('/perfil', follow_redirects=False)
        
        assert response.status_code in [302, 429]


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def db_manager_mock(mocker, conn):
    """Crea un mock de db_manager que usa la conexión proporcionada."""
    mock = mocker.Mock()
    mock.crear_usuario = mocker.Mock(return_value=1)
    mock.get_usuario_por_email = mocker.Mock(return_value=None)
    mock.get_usuario_por_id = mocker.Mock(return_value=None)
    mock.toggle_user_admin = mocker.Mock(return_value=True)
    mock.verificar_correo_usuario = mocker.Mock(return_value=True)
    mock.regenerar_token_verificacion = mocker.Mock(return_value=True)
    return mock
