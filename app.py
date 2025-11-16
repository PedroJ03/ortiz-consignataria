import sys
import os
from flask import Flask, jsonify, request, render_template, abort
from flask_cors import CORS
from datetime import datetime

# Añadir la raíz del proyecto al sys.path para encontrar módulos
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

try:
    from database import db_manager
except ModuleNotFoundError:
    print("Error: No se pudo encontrar el módulo 'database'.")
    print("Asegúrate de que 'database/db_manager.py' y '__init__.py' existan.")
    sys.exit(1)

# --- Configuración de Flask ---
app = Flask(__name__, 
            template_folder='templates',
            static_folder='static')
CORS(app) 

# --- ========================================== ---
# --- RUTAS DE NAVEGACIÓN ACTUALIZADAS ---
# --- ========================================== ---

@app.route('/')
def inicio():
    """
    NUEVO: Sirve la página de inicio (landing page).
    """
    print("Sirviendo inicio.html...")
    return render_template('inicio.html') 

@app.route('/precios')
def dashboard():
    """
    ACTUALIZADO: El dashboard de precios ahora vive en /precios
    """
    print("Sirviendo dashboard.html...")
    return render_template('dashboard.html') 

# --- ========================================== ---
# --- ENDPOINTS DE API (Sin Cambios) ---
# --- ========================================== ---

@app.route('/api/faena')
def api_faena():
    """
    Endpoint de API para obtener datos históricos de Faena.
    (Recibe fechas YYYY-MM-DD desde app.py)
    """
    start_date_iso = request.args.get('start')
    end_date_iso = request.args.get('end')
    categoria = request.args.get('categoria')
    raza = request.args.get('raza')
    rango_peso = request.args.get('rango_peso')

    if not start_date_iso or not end_date_iso:
        return jsonify({"error": "Parámetros 'start' y 'end' (YYYY-MM-DD) son requeridos."}), 400

    try:
        datos = db_manager.get_faena_historico(
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
    """
    Endpoint de API para obtener datos históricos de Invernada.
    """
    start_date_iso = request.args.get('start')
    end_date_iso = request.args.get('end')
    categoria = request.args.get('categoria')

    if not start_date_iso or not end_date_iso:
        return jsonify({"error": "Parámetros 'start' y 'end' (YYYY-MM-DD) son requeridos."}), 400
        
    try:
        datos = db_manager.get_invernada_historico(
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
    # ... (Sin cambios) ...
    conn = None
    try:
        conn = db_manager.get_db_connection()
        if not conn: abort(500, "No se pudo conectar a la base de datos.") 
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT categoria_original FROM faena ORDER BY categoria_original")
        categorias_faena = [row['categoria_original'] for row in cursor.fetchall()]
        cursor.execute("SELECT DISTINCT categoria_original FROM invernada ORDER BY categoria_original")
        categorias_invernada = [row['categoria_original'] for row in cursor.fetchall()]
        conn.close()
        return jsonify({ 'faena': categorias_faena, 'invernada': categorias_invernada })
    except Exception as e:
        print(f"Error en api_categorias: {e}")
        if conn: conn.close()
        return jsonify({"error": "Error interno del servidor al consultar categorías."}), 500

@app.route('/api/subcategorias')
def api_subcategorias():
    # ... (Sin cambios) ...
    categoria = request.args.get('categoria')
    tipo_hacienda = request.args.get('tipo', 'faena')
    if not categoria: return jsonify({"error": "Parámetro 'categoria' es requerido."}), 400
    if tipo_hacienda != 'faena': return jsonify({'razas': [], 'pesos': []})
    conn = None
    try:
        conn = db_manager.get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT raza FROM faena WHERE categoria_original = ? AND raza IS NOT NULL ORDER BY raza", (categoria,))
        razas = [row['raza'] for row in cursor.fetchall()]
        cursor.execute("SELECT DISTINCT rango_peso FROM faena WHERE categoria_original = ? AND rango_peso IS NOT NULL ORDER BY rango_peso", (categoria,))
        pesos = [row['rango_peso'] for row in cursor.fetchall()]
        conn.close()
        return jsonify({ 'razas': razas, 'pesos': pesos })
    except Exception as e:
        print(f"Error en api_subcategorias: {e}")
        if conn: conn.close()
        return jsonify({"error": "Error interno del servidor al consultar subcategorías."}), 500

# --- Bloque para ejecutar el servidor de desarrollo ---
if __name__ == '__main__':
    # ... (Sin cambios) ...
    print("--- Iniciando servidor de desarrollo Flask ---")
    print("Visita la página de INICIO en: http://127.0.0.1:5000/")
    print("Visita el Dashboard en: http://127.0.0.1:5000/precios")
    app.run(debug=True, port=5000)