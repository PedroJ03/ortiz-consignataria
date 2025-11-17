import sys
import os
from flask import Flask, jsonify, request, render_template, abort, g # <-- 'g' importado
from flask_cors import CORS
from datetime import datetime
import sqlite3

# --- Configuración de sys.path (1 nivel arriba de web_app) ---
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)
template_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates')
static_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static')

try:
    from shared_code.database import db_manager
except ModuleNotFoundError:
    print("Error: No se pudo encontrar 'shared_code.database.db_manager'")
    sys.exit(1)

# --- Configuración de Flask ---
app = Flask(__name__, template_folder=template_dir, static_folder=static_dir)
CORS(app) 

# --- ========================================== ---
# --- INICIO DE CORRECCIÓN (Manejo de Conexión) ---
# --- ========================================== ---

def get_db():
    """Abre una nueva conexión a la BBDD si no existe una para esta petición."""
    if 'db' not in g:
        # get_db_connection() usa la ruta de 3 niveles y encuentra el .db
        g.db = db_manager.get_db_connection()
    return g.db

@app.teardown_appcontext
def close_db(e=None):
    """Cierra la conexión a la BBDD al final de la petición."""
    db = g.pop('db', None)
    if db is not None:
        db.close()

# --- FIN DE CORRECCIÓN ---

# --- Rutas de Navegación (sin cambios) ---
@app.route('/')
def inicio():
    return render_template('inicio.html') 

@app.route('/precios')
def dashboard():
    return render_template('dashboard.html') 

# --- ========================================== ---
# --- ENDPOINTS DE API (ACTUALIZADOS) ---
# --- ========================================== ---

@app.route('/api/faena')
def api_faena():
    """Endpoint de API para Faena (ahora usa 'g.db')."""
    start_date_iso = request.args.get('start')
    end_date_iso = request.args.get('end')
    categoria = request.args.get('categoria')
    raza = request.args.get('raza')
    rango_peso = request.args.get('rango_peso')

    if not start_date_iso or not end_date_iso:
        return jsonify({"error": "Parámetros 'start' y 'end' (YYYY-MM-DD) son requeridos."}), 400

    try:
        conn = get_db() # <-- CORREGIDO: Obtiene la conexión de la petición
        datos = db_manager.get_faena_historico(
            conn, # <-- CORREGIDO: Pasa la conexión
            start_date_iso, 
            end_date_iso, 
            categoria or None,
            raza or None,
            rango_peso or None
        )
        return jsonify(datos) 
    except Exception as e:
        print(f"Error en api_faena: {e}")
        return jsonify({"error": "Error interno del servidor al consultar Faena."}), 500

@app.route('/api/invernada')
def api_invernada():
    """Endpoint de API para Invernada (ahora usa 'g.db')."""
    start_date_iso = request.args.get('start')
    end_date_iso = request.args.get('end')
    categoria = request.args.get('categoria')

    if not start_date_iso or not end_date_iso:
        return jsonify({"error": "Parámetros 'start' y 'end' (YYYY-MM-DD) son requeridos."}), 400
        
    try:
        conn = get_db() # <-- CORREGIDO
        datos = db_manager.get_invernada_historico(
            conn, # <-- CORREGIDO
            start_date_iso, 
            end_date_iso, 
            categoria or None
        )
        return jsonify(datos)
    except Exception as e:
        print(f"Error en api_invernada: {e}")
        return jsonify({"error": "Error interno del servidor al consultar Invernada."}), 500
        
@app.route('/api/categorias')
def api_categorias():
    """Endpoint de API para categorías (ahora usa 'g.db')."""
    try:
        conn = get_db() # <-- CORREGIDO
        if not conn:
            # Esta es la causa probable: si get_db() falla, conn es None
            print("Error en api_categorias: g.db no se pudo establecer.")
            abort(500, "No se pudo conectar a la base de datos.") 
            
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT categoria_original FROM faena ORDER BY categoria_original")
        categorias_faena = [row['categoria_original'] for row in cursor.fetchall()]
        cursor.execute("SELECT DISTINCT categoria_original FROM invernada ORDER BY categoria_original")
        categorias_invernada = [row['categoria_original'] for row in cursor.fetchall()]
        
        return jsonify({ 'faena': categorias_faena, 'invernada': categorias_invernada })
    except Exception as e:
        print(f"Error en api_categorias: {e}")
        return jsonify({"error": "Error interno del servidor al consultar categorías."}), 500

@app.route('/api/subcategorias')
def api_subcategorias():
    """Endpoint de API para subcategorías (ahora usa 'g.db')."""
    categoria = request.args.get('categoria')
    tipo_hacienda = request.args.get('tipo', 'faena')

    if not categoria:
        return jsonify({"error": "Parámetro 'categoria' es requerido."}), 400
    if tipo_hacienda != 'faena':
        return jsonify({'razas': [], 'pesos': []})

    try:
        conn = get_db() # <-- CORREGIDO
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT raza FROM faena WHERE categoria_original = ? AND raza IS NOT NULL ORDER BY raza", (categoria,))
        razas = [row['raza'] for row in cursor.fetchall()]
        cursor.execute("SELECT DISTINCT rango_peso FROM faena WHERE categoria_original = ? AND rango_peso IS NOT NULL ORDER BY rango_peso", (categoria,))
        pesos = [row['rango_peso'] for row in cursor.fetchall()]
        
        return jsonify({ 'razas': razas, 'pesos': pesos })
    except Exception as e:
        print(f"Error en api_subcategorias: {e}")
        return jsonify({"error": "Error interno del servidor al consultar subcategorías."}), 500

# --- Bloque para ejecutar el servidor de desarrollo (sin cambios) ---
if __name__ == '__main__':
    print("--- Iniciando servidor de desarrollo Flask ---")
    app.run(debug=True, port=5000)