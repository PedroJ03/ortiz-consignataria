import sys
import os
from flask import Flask, jsonify, request, render_template, abort, g, send_from_directory, redirect, url_for, flash
from flask_cors import CORS
import sqlite3
import uuid 
from werkzeug.utils import secure_filename
import re
from email_validator import validate_email, EmailNotValidError

# --- SEGURIDAD Y AUTH ---
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash

# --- CONFIGURACIÓN DE RUTAS ---
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

template_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates')
static_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static')

try:
    from shared_code.database import db_manager
    from shared_code.logger_config import setup_logger
except ModuleNotFoundError as e:
    print(f"CRITICAL ERROR: No se pudieron cargar módulos compartidos: {e}")
    sys.exit(1)

logger = setup_logger('Web_App')

app = Flask(__name__, template_folder=template_dir, static_folder=static_dir)
CORS(app)

# --- CONFIGURACIÓN DE UPLOADS ---
UPLOAD_FOLDER = os.path.join(static_dir, 'uploads', 'lotes')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024 # Límite 16MB por archivo

# Crear carpeta si no existe
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# --- CONFIGURACIÓN DE SEGURIDAD ---
# En producción, esto debe venir del .env
app.secret_key = os.environ.get('SECRET_KEY', 'clave_desarrollo_ortiz_2025')

# Inicializar Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login' # Si alguien intenta entrar a zona privada, va aquí

# --- LISTA NEGRA (Filtros Visuales) ---
CATEGORIAS_EXCLUIDAS = ["Ternera Holando", "Vacas CUT con cría", "TERNERAS", "NOVILLOS + CRUZA CEBU", "NOVILLOS + CRUZA EUROPEA"]

# --- GESTIÓN DE DOBLE BASE DE DATOS ---

def get_db_precios():
    """Conexión a la DB Analítica (Historial de Precios)."""
    if 'db_precios' not in g:
        g.db_precios = db_manager.get_conn_precios()
        if g.db_precios is None:
            logger.critical("Fallo conexión DB Precios.")
            abort(500)
    return g.db_precios

def get_db_market():
    """Conexión a la DB Transaccional (Usuarios y Lotes)."""
    if 'db_market' not in g:
        g.db_market = db_manager.get_conn_market()
        if g.db_market is None:
            logger.critical("Fallo conexión DB Marketplace.")
            abort(500)
    return g.db_market

@app.teardown_appcontext
def close_dbs(e=None):
    """Cierra ambas conexiones al terminar la petición."""
    db_p = g.pop('db_precios', None)
    if db_p is not None: db_p.close()
    
    db_m = g.pop('db_market', None)
    if db_m is not None: db_m.close()

# --- MODELO DE USUARIO (Flask-Login) ---
class User(UserMixin):
    def __init__(self, id, email, nombre, es_admin=False):
        self.id = id
        self.email = email
        self.nombre = nombre
        self.es_admin = es_admin

@login_manager.user_loader
def load_user(user_id):
    conn = get_db_market() # Usamos la DB nueva
    if not conn: return None
    cursor = conn.cursor()
    cursor.execute("SELECT id, email, nombre_completo, es_admin FROM users WHERE id = ?", (user_id,))
    u = cursor.fetchone()
    if u:
        return User(id=u['id'], email=u['email'], nombre=u['nombre_completo'], es_admin=bool(u['es_admin']))
    return None

# --- RUTAS PÚBLICAS ---

@app.route('/')
def inicio():
    # 1. Conectar a la base de Marketplace
    conn = get_db_market()
    
    # 2. Buscar el último lote
    lote_destacado = db_manager.obtener_ultima_publicacion(conn)
    
    # 3. Pasarlo al template
    return render_template('inicio.html', lote=lote_destacado)

@app.route('/precios')
def dashboard():
    return render_template('dashboard.html') 

@app.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(app.root_path, 'static', 'images'), 'logo_blanco_circular.png', mimetype='image/png')

# --- RUTAS DE AUTENTICACIÓN (Login/Registro) ---

@app.route('/registro', methods=['GET', 'POST'])
def registro():
    if current_user.is_authenticated:
        return redirect(url_for('inicio'))

    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        nombre = request.form.get('nombre')
        telefono = request.form.get('telefono')
        ubicacion = request.form.get('ubicacion')

        # --- 1. VALIDACIONES DE SEGURIDAD ---
        
        # A. Validar Email Real
        try:
            valid = validate_email(email)
            email = valid.email # Normalizado
        except EmailNotValidError as e:
            flash(f'Email inválido: {str(e)}', 'error')
            return render_template('auth/registro.html')

        # B. Validar Contraseña Fuerte (Mínimo 8 caracteres, 1 número)
        if len(password) < 8 or not re.search(r"\d", password):
            flash('La contraseña debe tener al menos 8 caracteres y contener un número.', 'error')
            return render_template('auth/registro.html')

        # C. Validar Teléfono (Solo números, guiones o más, min 8 dígitos)
        # Limpiamos caracteres no numéricos para chequear longitud
        nums_telefono = re.sub(r'\D', '', telefono) 
        if len(nums_telefono) < 8:
            flash('Por favor ingrese un número de teléfono válido (con código de área).', 'error')
            return render_template('auth/registro.html')

        # D. Validar Nombre (Mínimo 3 letras)
        if len(nombre.strip()) < 3:
            flash('El nombre es muy corto.', 'error')
            return render_template('auth/registro.html')

        # --- 2. LÓGICA DE GUARDADO ---
        conn = get_db_market()
        
        # Verificar duplicados
        if db_manager.get_usuario_por_email(conn, email):
            flash('Este correo electrónico ya está registrado.', 'error')
            return render_template('auth/registro.html')

        # Crear usuario
        hashed_pw = generate_password_hash(password, method='pbkdf2:sha256')
        nuevo_id = db_manager.crear_usuario(conn, email, hashed_pw, nombre, telefono, ubicacion)
        
        if nuevo_id:
            user_obj = User(id=nuevo_id, email=email, nombre=nombre)
            login_user(user_obj)
            flash(f'¡Cuenta creada exitosamente! Bienvenido, {nombre}.', 'success')
            return redirect(url_for('inicio'))
        else:
            flash('Error interno al registrar. Intente nuevamente.', 'error')

    return render_template('auth/registro.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('inicio'))

    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        remember = True if request.form.get('remember') else False

        conn = get_db_market()
        user_data = db_manager.get_usuario_por_email(conn, email)

        if user_data and check_password_hash(user_data['password_hash'], password):
            user = User(id=user_data['id'], email=user_data['email'], nombre=user_data['nombre_completo'], es_admin=bool(user_data['es_admin']))
            login_user(user, remember=remember)
            next_page = request.args.get('next')
            return redirect(next_page or url_for('inicio'))
        else:
            flash('Credenciales inválidas.', 'error')

    return render_template('auth/login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Sesión cerrada.', 'info')
    return redirect(url_for('inicio'))

# --- API ENDPOINTS (Usan DB Precios) ---

@app.route('/api/faena')
def api_faena():
    try:
        conn = get_db_precios() # DB Precios
        start, end = request.args.get('start'), request.args.get('end')
        if not start or not end: return jsonify({"error": "Fechas requeridas"}), 400
        
        data = db_manager.get_faena_historico(conn, start, end, request.args.get('categoria'), request.args.get('raza'), request.args.get('rango_peso'))
        return jsonify(data)
    except Exception as e:
        logger.error(f"API Faena Error: {e}")
        return jsonify({"error": "Error interno"}), 500

@app.route('/api/invernada')
def api_invernada():
    try:
        conn = get_db_precios() # DB Precios
        start, end = request.args.get('start'), request.args.get('end')
        if not start or not end: return jsonify({"error": "Fechas requeridas"}), 400
        
        data = db_manager.get_invernada_historico(conn, start, end, request.args.get('categoria'))
        return jsonify(data)
    except Exception as e:
        logger.error(f"API Invernada Error: {e}")
        return jsonify({"error": "Error interno"}), 500

@app.route('/api/categorias')
def api_categorias():
    try:
        conn = get_db_precios()
        cursor = conn.cursor()
        
        cursor.execute("SELECT DISTINCT categoria_original FROM faena ORDER BY categoria_original")
        all_faena = [r[0] for r in cursor.fetchall()]
        
        cursor.execute("SELECT DISTINCT categoria_original FROM invernada ORDER BY categoria_original")
        all_inv = [r[0] for r in cursor.fetchall()]
        
        excl = [c.lower() for c in CATEGORIAS_EXCLUIDAS]
        
        return jsonify({
            'faena': [c for c in all_faena if c.lower() not in excl and "cruza" not in c.lower()],
            'invernada': [c for c in all_inv if c.lower() not in excl]
        })
    except Exception as e:
        logger.error(f"API Categorias Error: {e}")
        return jsonify({"error": "Error interno"}), 500

@app.route('/api/subcategorias')
def api_subcategorias():
    cat = request.args.get('categoria')
    if not cat: return jsonify({"error": "Categoria requerida"}), 400
    try:
        conn = get_db_precios()
        cursor = conn.cursor()
        
        cursor.execute("SELECT DISTINCT raza FROM faena WHERE categoria_original = ? AND raza != '' ORDER BY raza", (cat,))
        razas = [r[0] for r in cursor.fetchall()]
        
        query_peso = "SELECT DISTINCT rango_peso FROM faena WHERE categoria_original = ? AND rango_peso != ''"
        params_peso = [cat]
        if request.args.get('raza'):
            query_peso += " AND raza = ?"
            params_peso.append(request.args.get('raza'))
        query_peso += " ORDER BY rango_peso"
        
        cursor.execute(query_peso, tuple(params_peso))
        pesos = [r[0] for r in cursor.fetchall()]
        
        return jsonify({'razas': razas, 'pesos': pesos})
    except Exception as e:
        logger.error(f"API Subcat Error: {e}")
        return jsonify({"error": "Error interno"}), 500
    

# --- RUTAS DE MARKETPLACE ---

@app.route('/publicar', methods=['GET', 'POST'])
@login_required # ¡Solo usuarios logueados!
def publicar():
    if request.method == 'POST':
        # 1. Obtener datos de texto
        titulo = request.form.get('titulo')
        categoria = request.form.get('categoria')
        raza = request.form.get('raza')
        cantidad = request.form.get('cantidad')
        peso = request.form.get('peso')
        precio = request.form.get('precio') # Puede ser vacío
        ubicacion = request.form.get('ubicacion')
        descripcion = request.form.get('descripcion')

        # 2. Manejo de la Imagen
        file = request.files.get('imagen')
        filename_final = None

        if file and allowed_file(file.filename):
            # Generar nombre seguro y único (ej: a1b2-c3d4.jpg)
            ext = file.filename.rsplit('.', 1)[1].lower()
            unique_name = f"{uuid.uuid4().hex}.{ext}"
            
            # Guardar archivo físico
            path_completo = os.path.join(app.config['UPLOAD_FOLDER'], unique_name)
            file.save(path_completo)
            
            # Guardar ruta relativa para la DB (static/uploads/lotes/foto.jpg)
            filename_final = f"uploads/lotes/{unique_name}"
        
        # 3. Guardar en Base de Datos
        conn = get_db_market()
        
        nuevo_id = db_manager.crear_publicacion(
            conn, 
            user_id=current_user.id,
            titulo=titulo,
            categoria=categoria,
            raza=raza,
            cantidad=cantidad,
            peso=peso,
            precio=precio if precio else 0,
            descripcion=descripcion,
            ubicacion=ubicacion,
            imagen=filename_final
        )

        if nuevo_id:
            flash('Lote publicado', 'success')
            return redirect(url_for('dashboard')) # O ir a "Mis Publicaciones"
        else:
            flash('Error al guardar la publicación.', 'error')

    return render_template('marketplace/publicar.html')


# --- RUTA DE LA VIDRIERA (PÚBLICA) ---

@app.route('/mercado')
def mercado():
    conn = get_db_market()
    lotes = db_manager.obtener_publicaciones(conn)
    return render_template('marketplace/index.html', lotes=lotes)


# --- RUTAS DE ADMINISTRACIÓN ---

@app.route('/admin')
@login_required
def admin_panel():
    # Candado de seguridad: Solo admins
    if not current_user.es_admin:
        abort(403) # Prohibido
        
    conn = get_db_market()
    usuarios = db_manager.get_all_users(conn)
    publicaciones = db_manager.get_all_publicaciones_admin(conn)
    
    return render_template('admin/panel.html', usuarios=usuarios, publicaciones=publicaciones)

@app.route('/admin/borrar_lote/<int:id>', methods=['POST'])
@login_required
def admin_borrar_lote(id):
    if not current_user.es_admin:
        abort(403)
        
    conn = get_db_market()
    if db_manager.eliminar_publicacion(conn, id):
        flash('Publicación eliminada', 'success')
    else:
        flash('No se pudo eliminar la publicación.', 'error')
        
    return redirect(url_for('admin_panel'))

# --- EN WEB_APP/APP.PY ---

@app.route('/admin/toggle_lote/<int:id>', methods=['POST'])
@login_required
def admin_toggle_lote(id):
    if not current_user.es_admin: return jsonify({'success': False, 'msg': 'No autorizado'}), 403
    
    conn = get_db_market()
    # Obtenemos el estado ANTES de cambiarlo para saber el nuevo
    cursor = conn.cursor()
    cursor.execute("SELECT activo FROM publicaciones WHERE id = ?", (id,))
    row = cursor.fetchone()
    if not row: return jsonify({'success': False, 'msg': 'Lote no encontrado'}), 404
    
    if db_manager.toggle_publicacion_activa(conn, id):
        nuevo_estado = not row['activo'] # Invertimos el estado anterior
        return jsonify({'success': True, 'activo': nuevo_estado})
    
    return jsonify({'success': False, 'msg': 'Error en DB'}), 500

@app.route('/admin/toggle_user/<int:id>', methods=['POST'])
@login_required
def admin_toggle_user(id):
    if not current_user.es_admin: return jsonify({'success': False, 'msg': 'No autorizado'}), 403
    if id == current_user.id: return jsonify({'success': False, 'msg': 'No puedes quitarte admin a ti mismo'}), 400

    conn = get_db_market()
    # Ver estado actual
    cursor = conn.cursor()
    cursor.execute("SELECT es_admin FROM users WHERE id = ?", (id,))
    row = cursor.fetchone()
    
    if db_manager.toggle_user_admin(conn, id):
        nuevo_estado = not bool(row['es_admin'])
        return jsonify({'success': True, 'es_admin': nuevo_estado})
        
    return jsonify({'success': False, 'msg': 'Error en DB'}), 500


# --- MANEJO DE ERRORES ---
@app.errorhandler(404)
def page_not_found(e): return render_template('404.html'), 404

@app.errorhandler(500)
def server_error(e): return render_template('500.html'), 500

if __name__ == '__main__':
    logger.info("Servidor iniciado.")
    app.run(debug=True, host='0.0.0.0', port=5000)