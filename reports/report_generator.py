import sqlite3
import pandas as pd
from jinja2 import Environment, FileSystemLoader
from weasyprint import HTML, CSS
import os
from datetime import datetime
import pathlib # Importar pathlib para manejar rutas como URI

# Rutas relativas al script actual
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_DIR = os.path.join(BASE_DIR, 'templates')
PROJECT_ROOT = os.path.dirname(BASE_DIR) # Raíz del proyecto
OUTPUT_DIR = os.path.join(PROJECT_ROOT, 'output') # Carpeta 'output' en la raíz
STATIC_DIR = os.path.join(PROJECT_ROOT, 'static') # Carpeta 'static' en la raíz

# Asegurarse de que la carpeta de salida exista
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Ruta a la base de datos
DB_PATH = os.path.join(PROJECT_ROOT, 'database', 'precios.db')

def fetch_latest_data(fecha_consulta_str):
    """
    Consulta la base de datos y devuelve los registros más recientes
    para la fecha de consulta especificada, como una lista de diccionarios.
    """
    print(f"Buscando datos en la BBDD para la fecha: {fecha_consulta_str}")
    conn = None
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row 
        cursor = conn.cursor()

        cursor.execute("""
            SELECT * FROM precios 
            WHERE fecha_consulta = ? 
            ORDER BY id DESC 
        """, (fecha_consulta_str,))
        
        rows = cursor.fetchall()
        data = [dict(row) for row in rows]
        print(f"Se encontraron {len(data)} registros en la BBDD.")
        return data

    except sqlite3.Error as e:
        print(f"Error al leer datos de la BBDD: {e}")
        return []
    finally:
        if conn:
            conn.close()

def generate_pdf_report(data, filename="reporte_precios.pdf", template_name="report_template.html"):
    """
    Genera un archivo PDF a partir de los datos usando una plantilla HTML.
    """
    if not data:
        print("No hay datos para generar el reporte PDF.")
        return None

    try:
        env = Environment(loader=FileSystemLoader(TEMPLATE_DIR))
        template = env.get_template(template_name)
        
        # --- CORRECCIÓN RUTA LOGO ---
        logo_filename = "logo_blanco.jpeg" 
        logo_abs_path = os.path.join(STATIC_DIR, 'images', logo_filename)
        logo_uri = None
        if os.path.exists(logo_abs_path):
            logo_uri = pathlib.Path(logo_abs_path).as_uri()
            print(f"DEBUG: URI del logo encontrado: {logo_uri}")
        else:
            print(f"ADVERTENCIA: No se encontró el archivo del logo en: {logo_abs_path}")

        # --- AÑADIR TIPO HACIENDA AL CONTEXTO ---
        context = {
            'fecha_reporte': data[0]['fecha_consulta'], 
            'fuente': 'Mercado Agroganadero (MAG)', 
            'tipo_hacienda': data[0]['tipo_hacienda'], 
            'datos': data,
            'logo_path': logo_uri, 
            'consignataria_nombre': 'Ortiz y Cía. Consignatarios' 
        }
        
        html_out = template.render(context)
        
        output_path = os.path.join(OUTPUT_DIR, filename)
        
        HTML(string=html_out, base_url=PROJECT_ROOT).write_pdf(output_path) 
        
        print(f"Reporte PDF generado exitosamente en: {output_path}")
        return output_path
        
    except Exception as e:
        print(f"Error al generar el reporte PDF: {e}")
        import traceback
        traceback.print_exc()
        return None

# --- Bloque para probar este script individualmente ---
if __name__ == "__main__":
    print("--- Ejecutando prueba del generador de reportes ---")
    fecha_a_buscar = "17/10/2025" 
    datos_recientes = fetch_latest_data(fecha_a_buscar)
    
    if datos_recientes:
        # generate_excel_report(datos_recientes, filename=f"reporte_{fecha_a_buscar.replace('/', '-')}.xlsx") # Comentado
        generate_pdf_report(datos_recientes, filename=f"reporte_{fecha_a_buscar.replace('/', '-')}.pdf")
    else:
        print(f"No se encontraron datos para la fecha {fecha_a_buscar} en la base de datos.")
        
    print("\n--- Prueba finalizada ---")

