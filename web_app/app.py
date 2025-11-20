import sys
import os
from flask import Flask, jsonify, request, render_template, abort, g, send_from_directory
from flask_cors import CORS
from datetime import datetime
import sqlite3

# --- CONFIGURACIÓN DE LOGGING Y RUTAS ---
# Subimos dos niveles para llegar a la raíz del proyecto y encontrar 'shared_code'
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

template_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates')
static_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static')

try:
    from shared_code.database import db_manager
    from shared_code.logger_config import setup_logger
except ModuleNotFoundError as e:
    # Si falla esto, usamos un print de emergencia porque el logger no cargó
    print(f"CRITICAL ERROR: No se pudieron cargar módulos compartidos: {e}")
    sys.exit(1)

# Inicializar Logger para este módulo
logger = setup_logger('Web_App')

# --- CONFIGURACIÓN FLASK ---
app = Flask(__name__, template_folder=template_dir, static_folder=static_dir)
CORS(app)

logger.info("Iniciando aplicación web Flask...")

# --- LISTA NEGRA DE CATEGORÍAS ---
# Nota: Mantener actualizada si cambian los nombres en el scraper
CATEGORIAS_EXCLUIDAS = [
    "Ternera Holando",
    "Vacas CUT con cría",
    "TERNERAS", 
    "NOVILLOS + CRUZA CEBU", 
    "NOVILLOS + CRUZA EUROPEA" 
]

# --- GESTIÓN DE BASE DE DATOS ---
def get_db():
    if 'db' not in g:
        g.db = db_manager.get_db_connection()
        if g.db is None:
            logger.critical("No se pudo establecer conexión con la base de datos.")
            abort(500, "Error de conexión a base de datos.")
    return g.db

@app.teardown_appcontext
def close_db(e=None):
    db = g.pop('db', None)
    if db is not None:
        db.close()

# --- RUTAS DE NAVEGACIÓN (FRONTEND) ---
@app.route('/')
def inicio():
    logger.info(f"Acceso a Inicio desde {request.remote_addr}")
    return render_template('inicio.html') 

@app.route('/precios')
def dashboard():
    logger.info(f"Acceso a Dashboard desde {request.remote_addr}")
    return render_template('dashboard.html') 

# --- API ENDPOINTS (BACKEND JSON) ---

@app.route('/api/faena')
def api_faena():
    start_date = request.args.get('start') # Espera YYYY-MM-DD
    end_date = request.args.get('end')     # Espera YYYY-MM-DD
    categoria = request.args.get('categoria')
    raza = request.args.get('raza')
    rango_peso = request.args.get('rango_peso')

    if not start_date or not end_date:
        logger.warning("Solicitud API Faena fallida: Faltan fechas.")
        return jsonify({"error": "Parámetros 'start' y 'end' son requeridos."}), 400

    try:
        conn = get_db()
        logger.debug(f"Consultando Faena: {start_date} a {end_date} | Cat: {categoria}")
        
        datos = db_manager.get_faena_historico(
            conn, start_date, end_date, categoria, raza, rango_peso
        )
        return jsonify(datos) 

    except Exception as e:
        logger.error(f"Error en endpoint /api/faena: {e}")
        return jsonify({"error": "Error interno del servidor."}), 500

@app.route('/api/invernada')
def api_invernada():
    start_date = request.args.get('start')
    end_date = request.args.get('end')
    categoria = request.args.get('categoria')

    if not start_date or not end_date:
        logger.warning("Solicitud API Invernada fallida: Faltan fechas.")
        return jsonify({"error": "Parámetros requeridos."}), 400
        
    try:
        conn = get_db()
        logger.debug(f"Consultando Invernada: {start_date} a {end_date} | Cat: {categoria}")
        
        datos = db_manager.get_invernada_historico(conn, start_date, end_date, categoria)
        return jsonify(datos)

    except Exception as e:
        logger.error(f"Error en endpoint /api/invernada: {e}")
        return jsonify({"error": "Error interno del servidor."}), 500
        
@app.route('/api/categorias')
def api_categorias():
    """Devuelve listas limpias de categorías para los selectores."""
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        # Faena
        cursor.execute("SELECT DISTINCT categoria_original FROM faena ORDER BY categoria_original")
        all_faena = [row['categoria_original'] for row in cursor.fetchall()]
        
        # Invernada
        cursor.execute("SELECT DISTINCT categoria_original FROM invernada ORDER BY categoria_original")
        all_invernada = [row['categoria_original'] for row in cursor.fetchall()]
        
        # Filtrado (Case Insensitive)
        excluidas_lower = [c.lower() for c in CATEGORIAS_EXCLUIDAS]
        
        categorias_faena = [
            c for c in all_faena 
            if c.lower() not in excluidas_lower 
            and not any(ex in c.lower() for ex in ["cruza cebu", "cruza europea"])
        ]
        
        categorias_invernada = [
            c for c in all_invernada 
            if c.lower() not in excluidas_lower
        ]
        
        return jsonify({ 'faena': categorias_faena, 'invernada': categorias_invernada })

    except Exception as e:
        logger.critical(f"Error crítico recuperando categorías: {e}")
        return jsonify({"error": "No se pudieron cargar las categorías."}), 500

@app.route('/api/subcategorias')
def api_subcategorias():
    categoria = request.args.get('categoria')
    raza_filtro = request.args.get('raza')
    
    if not categoria: 
        return jsonify({"error": "Categoría requerida."}), 400

    try:
        conn = get_db()
        cursor = conn.cursor()
        
        # Obtener Razas disponibles para esa categoría
        cursor.execute(
            "SELECT DISTINCT raza FROM faena WHERE categoria_original = ? AND raza IS NOT NULL AND raza != '' ORDER BY raza", 
            (categoria,)
        )
        razas = [row['raza'] for row in cursor.fetchall()]

        # Obtener Pesos (filtrados por raza si se seleccionó una)
        if raza_filtro:
            cursor.execute(
                "SELECT DISTINCT rango_peso FROM faena WHERE categoria_original = ? AND raza = ? AND rango_peso IS NOT NULL AND rango_peso != '' ORDER BY rango_peso", 
                (categoria, raza_filtro)
            )
        else:
            cursor.execute(
                "SELECT DISTINCT rango_peso FROM faena WHERE categoria_original = ? AND rango_peso IS NOT NULL AND rango_peso != '' ORDER BY rango_peso", 
                (categoria,)
            )
            
        pesos = [row['rango_peso'] for row in cursor.fetchall()]
        
        return jsonify({ 'razas': razas, 'pesos': pesos })

    except Exception as e:
        logger.error(f"Error obteniendo subcategorías para '{categoria}': {e}")
        return jsonify({"error": "Error interno."}), 500

@app.route('/favicon.ico')
def favicon():
    return send_from_directory(
        os.path.join(app.root_path, 'static', 'images'),
        'logo_blanco_circular.png',
        mimetype='image/png'
    )

@app.errorhandler(404)
def page_not_found(e):
    # Logueamos como WARNING para que NO envíe email, pero quede registro
    logger.warning(f"404 Not Found: {request.url}")
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_server_error(e):
    # Este SI es crítico, logueamos como ERROR (envía email)
    logger.error(f"Error 500 Servidor: {e}")
    return render_template('500.html'), 500

# Manejador de errores global (para atrapar lo que se nos escape)
@app.errorhandler(Exception)
def handle_exception(e):
    # Importamos HTTPException para filtrar errores HTTP comunes
    from werkzeug.exceptions import HTTPException
    
    # Si es un error HTTP conocido (como 404, 405, etc) que se nos pasó
    if isinstance(e, HTTPException):
        logger.warning(f"HTTP Exception: {e}")
        return e

    # Si es un error de Python real (código roto), enviamos ALERTA
    logger.exception(f"Excepción NO manejada en Flask: {e}")
    return render_template("500.html"), 500

if __name__ == '__main__':
    # En desarrollo (debug=True), Flask recarga y duplica logs a veces, es normal.
    # En producción, usar Gunicorn.
    logger.info("Servidor Flask iniciado en puerto 5000.")
    app.run(debug=True, host='0.0.0.0', port=5000)