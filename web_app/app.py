import sys
import os
from flask import Flask, jsonify, request, render_template, abort, g, send_from_directory, redirect, url_for, flash
from flask_cors import CORS
import sqlite3
import uuid 
from werkzeug.utils import secure_filename
import re
from email_validator import validate_email, EmailNotValidError
from web_app.utils.video_optimizer import optimizar_video

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

# SEPARAR EXTENSIONES
ALLOWED_IMAGE_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp'}
ALLOWED_VIDEO_EXTENSIONS = {'mp4', 'mov', 'avi', 'webm'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024 # Límite 100MB por archivo

# Crear carpeta si no existe
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def allowed_file(filename, type='image'):
    if '.' not in filename: return False
    ext = filename.rsplit('.', 1)[1].lower()
    if type == 'image':
        return ext in ALLOWED_IMAGE_EXTENSIONS
    elif type == 'video':
        return ext in ALLOWED_VIDEO_EXTENSIONS
    return False

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
@login_required
def publicar():
    if request.method == 'POST':
        # 1. Obtener lista de archivos (input multiple)
        files = request.files.getlist('archivos')
        
        # Validar que al menos uno no esté vacío
        if not files or files[0].filename == '':
             flash('Debe seleccionar al menos una foto o video.', 'error')
             return render_template('marketplace/publicar.html')

        # Variables para definir la portada (la primera que encontremos)
        portada_filename = None     # Para la tabla publicaciones (columna imagen_filename)
        video_portada = None        # Para la tabla publicaciones (columna video_filename)
        
        media_procesada = []        # Lista para guardar en la tabla media_lotes luego

        # 2. Procesar todos los archivos en bucle
        for file in files:
            if file and '.' in file.filename:
                ext = file.filename.rsplit('.', 1)[1].lower()
                
                # --- ES IMAGEN ---
                if ext in ALLOWED_IMAGE_EXTENSIONS: # {'png', 'jpg', 'jpeg', 'webp'}
                    unique_name = f"{uuid.uuid4().hex}.{ext}"
                    path_completo = os.path.join(app.config['UPLOAD_FOLDER'], unique_name)
                    file.save(path_completo)
                    
                    final_name = f"uploads/lotes/{unique_name}"
                    media_procesada.append({'name': final_name, 'type': 'imagen'})
                    
                    # Si es la primera imagen, será la portada
                    if not portada_filename: 
                        portada_filename = final_name 
                
                # --- ES VIDEO ---
                elif ext in ALLOWED_VIDEO_EXTENSIONS: # {'mp4', 'mov', 'avi', 'webm'}
                    # Nombres
                    raw_name = f"raw_{uuid.uuid4().hex}.{ext}"
                    final_name = f"vid_{uuid.uuid4().hex}.mp4"
                    
                    path_raw = os.path.join(app.config['UPLOAD_FOLDER'], raw_name)
                    path_final = os.path.join(app.config['UPLOAD_FOLDER'], final_name)
                    
                    # Guardar y Optimizar
                    file.save(path_raw)
                    try:
                        # Asumo que importaste la funcion optimizar_video arriba
                        exito = optimizar_video(path_raw, path_final)
                        if exito:
                            final_name_video = f"uploads/lotes/{final_name}"
                            os.remove(path_raw)
                        else:
                            os.rename(path_raw, path_final)
                            final_name_video = f"uploads/lotes/{final_name}"
                        
                        media_procesada.append({'name': final_name_video, 'type': 'video'})
                        
                        # Si es el primer video, lo guardamos como referencia
                        if not video_portada: 
                            video_portada = final_name_video

                    except Exception as e:
                        print(f"Error procesando video {file.filename}: {e}")

        # 3. Guardar Publicación Principal (Tabla 'publicaciones')
        conn = get_db_market()
        
        # Lógica de portada: Priorizamos imagen. Si no hay, y hay video, dejamos vacío o nulo según tu lógica de index.
        # Aquí guardamos las referencias principales para que el 'index.html' no se rompa.
        
        nid = db_manager.crear_publicacion(
            conn=conn, 
            user_id=current_user.id, 
            titulo=request.form.get('titulo'), 
            categoria=request.form.get('categoria'),
            raza=request.form.get('raza'), 
            cantidad=request.form.get('cantidad'),
            peso=request.form.get('peso'), 
            precio=request.form.get('precio') or 0,
            descripcion=request.form.get('descripcion'), 
            ubicacion=request.form.get('ubicacion'),
            imagen_filename=portada_filename, # La foto de portada
            video_filename=video_portada      # El video principal
        )

        # 4. Guardar la Galería Completa (Tabla 'media_lotes')
        if nid:
            for item in media_procesada:
                # Esta función debe existir en db_manager (paso anterior)
                db_manager.guardar_archivo_media(conn, nid, item['name'], item['type'])
            
            flash('Lote publicado con éxito.', 'success')
            return redirect(url_for('mercado')) 
        else:
            flash('Error al guardar en base de datos.', 'error')

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

@app.route('/mercado/<int:lote_id>')
def detalle_lote(lote_id):
    conn = get_db_market()
    
    # 1. Obtener datos del lote
    lote = db_manager.obtener_publicacion_por_id(conn, lote_id)
    
    if not lote:
        flash('La publicación no existe.', 'error')
        return redirect(url_for('mercado'))
    
    # 2. NUEVO: Obtener la galería de archivos
    # Si la función retorna lista vacía [], la plantilla lo manejará
    galeria = db_manager.obtener_media_por_publicacion(conn, lote_id)
    
    return render_template('marketplace/detalle.html', lote=lote, galeria=galeria)


# --- MANEJO DE ERRORES ---
@app.errorhandler(404)
def page_not_found(e): return render_template('404.html'), 404

@app.errorhandler(500)
def server_error(e): return render_template('500.html'), 500

if __name__ == '__main__':
    logger.info("Servidor iniciado.")
    app.run(debug=True, host='0.0.0.0', port=5000)