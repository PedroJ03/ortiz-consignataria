import sys
import os
from flask import Flask, jsonify, request, render_template, abort, g
from flask_cors import CORS
from datetime import datetime
import sqlite3

# --- Configuración de sys.path ---
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

# --- LISTA NEGRA DE CATEGORÍAS (Para ocultar en el dashboard) ---
CATEGORIAS_EXCLUIDAS = [
    # Invernada
    "Ternera Holando",
    "Vacas CUT con cría",
    # Faena
    "TERNERAS", # (Ojo: en BBDD suele estar en mayúsculas para Faena)
    "NOVILLOS + CRUZA CEBU", # Verificar nombre exacto en BBDD
    "NOVILLOS + CRUZA EUROPEA" # Verificar nombre exacto en BBDD
]

# --- Manejo de Conexión de BBDD ---
def get_db():
    if 'db' not in g:
        g.db = db_manager.get_db_connection()
    return g.db

@app.teardown_appcontext
def close_db(e=None):
    db = g.pop('db', None)
    if db is not None:
        db.close()

# --- Rutas de Navegación ---
@app.route('/')
def inicio():
    return render_template('inicio.html') 

@app.route('/precios')
def dashboard():
    return render_template('dashboard.html') 

# --- Endpoints de API ---

@app.route('/api/faena')
def api_faena():
    # ... (Sin cambios) ...
    start_date_iso = request.args.get('start')
    end_date_iso = request.args.get('end')
    categoria = request.args.get('categoria')
    raza = request.args.get('raza')
    rango_peso = request.args.get('rango_peso')

    if not start_date_iso or not end_date_iso:
        return jsonify({"error": "Parámetros 'start' y 'end' (YYYY-MM-DD) son requeridos."}), 400

    try:
        conn = get_db()
        datos = db_manager.get_faena_historico(
            conn, start_date_iso, end_date_iso, categoria, raza, rango_peso
        )
        return jsonify(datos) 
    except Exception as e:
        print(f"Error en api_faena: {e}")
        return jsonify({"error": "Error interno."}), 500

@app.route('/api/invernada')
def api_invernada():
    # ... (Sin cambios) ...
    start_date_iso = request.args.get('start')
    end_date_iso = request.args.get('end')
    categoria = request.args.get('categoria')

    if not start_date_iso or not end_date_iso:
        return jsonify({"error": "Parámetros requeridos."}), 400
        
    try:
        conn = get_db()
        datos = db_manager.get_invernada_historico(conn, start_date_iso, end_date_iso, categoria)
        return jsonify(datos)
    except Exception as e:
        print(f"Error en api_invernada: {e}")
        return jsonify({"error": "Error interno."}), 500
        
# --- API ACTUALIZADA: Filtrado de Categorías ---
@app.route('/api/categorias')
def api_categorias():
    """Endpoint de API para categorías (filtrando las excluidas)."""
    try:
        conn = get_db()
        if not conn: abort(500, "No DB connection.") 
            
        cursor = conn.cursor()
        
        # Faena
        cursor.execute("SELECT DISTINCT categoria_original FROM faena ORDER BY categoria_original")
        all_faena = [row['categoria_original'] for row in cursor.fetchall()]
        
        # Invernada
        cursor.execute("SELECT DISTINCT categoria_original FROM invernada ORDER BY categoria_original")
        all_invernada = [row['categoria_original'] for row in cursor.fetchall()]
        
        # --- Filtrado en Python (Case Insensitive para seguridad) ---
        excluidas_lower = [c.lower() for c in CATEGORIAS_EXCLUIDAS]
        
        # Verificar si el nombre exacto O alguna parte coincide (opcional)
        # Aquí usamos coincidencia exacta o parcial según prefieras. 
        # Usaré coincidencia exacta insensible a mayúsculas/minúsculas para ser preciso.
        
        categorias_faena = [
            c for c in all_faena 
            if c.lower() not in excluidas_lower 
            and not any(ex in c.lower() for ex in ["cruza cebu", "cruza europea"]) # Filtro especial para tus combinaciones
        ]
        
        categorias_invernada = [
            c for c in all_invernada 
            if c.lower() not in excluidas_lower
        ]
        
        return jsonify({ 'faena': categorias_faena, 'invernada': categorias_invernada })
    except Exception as e:
        print(f"Error en api_categorias: {e}")
        return jsonify({"error": "Error interno."}), 500

@app.route('/api/subcategorias')
def api_subcategorias():
    # ... (Sin cambios) ...
    categoria = request.args.get('categoria')
    raza_filtro = request.args.get('raza')
    if not categoria: return jsonify({"error": "Parámetro 'categoria' es requerido."}), 400

    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT raza FROM faena WHERE categoria_original = ? AND raza IS NOT NULL AND raza != '' ORDER BY raza", (categoria,))
        razas = [row['raza'] for row in cursor.fetchall()]

        if raza_filtro:
            cursor.execute("SELECT DISTINCT rango_peso FROM faena WHERE categoria_original = ? AND raza = ? AND rango_peso IS NOT NULL AND rango_peso != '' ORDER BY rango_peso", (categoria, raza_filtro))
        else:
            cursor.execute("SELECT DISTINCT rango_peso FROM faena WHERE categoria_original = ? AND rango_peso IS NOT NULL AND rango_peso != '' ORDER BY rango_peso", (categoria,))
            
        pesos = [row['rango_peso'] for row in cursor.fetchall()]
        
        return jsonify({ 'razas': razas, 'pesos': pesos })
    except Exception as e:
        print(f"Error en api_subcategorias: {e}")
        return jsonify({"error": "Error interno."}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)