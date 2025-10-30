import os
import pathlib
from datetime import datetime
from jinja2 import Environment, FileSystemLoader
from weasyprint import HTML
# Nota: Ya no importamos sqlite3 ni pandas

# Práctica Profesional: Definir rutas robustas
# __file__ es la ruta de este script (report_generator.py)
BASE_DIR = os.path.dirname(os.path.abspath(__file__)) # Carpeta /reports
TEMPLATE_DIR = os.path.join(BASE_DIR, 'templates')     # Carpeta /reports/templates
PROJECT_ROOT = os.path.dirname(BASE_DIR)              # Carpeta raíz /ortiz-consignataria
OUTPUT_DIR = os.path.join(PROJECT_ROOT, 'output')      # Carpeta /output
STATIC_DIR = os.path.join(PROJECT_ROOT, 'static')      # Carpeta /static

# Asegurarse de que la carpeta de salida exista
os.makedirs(OUTPUT_DIR, exist_ok=True)

# --- fetch_latest_data() fue eliminada (ya no usamos BBDD) ---

def generate_pdf_report(data, filename="reporte_precios.pdf", template_name="report_template.html"):
    """
    Genera un archivo PDF a partir de los datos usando una plantilla HTML.
    Maneja contextos diferentes para Faena (MAG) e Invernada (Campo).
    """
    if not data or len(data) == 0:
        print(f"ADVERTENCIA: No hay datos para generar el reporte PDF: {filename}")
        return None

    try:
        # Configurar Jinja2
        env = Environment(loader=FileSystemLoader(TEMPLATE_DIR))
        template = env.get_template(template_name)
        
        # --- Lógica de la Ruta del Logo ---
        logo_filename = "logo_blanco.jpeg" # El nombre de tu logo
        logo_abs_path = os.path.join(STATIC_DIR, 'images', logo_filename)
        logo_uri = None
        if os.path.exists(logo_abs_path):
            # Práctica Profesional: Convertir ruta de archivo a URI (file:///)
            logo_uri = pathlib.Path(logo_abs_path).as_uri()
            print(f"DEBUG: URI del logo encontrado: {logo_uri}")
        else:
            print(f"ADVERTENCIA: No se encontró el archivo del logo en: {logo_abs_path}")

        # --- Construcción del Contexto Dinámico ---
        first_row = data[0] # Usar el primer registro para datos comunes
        
        context = {
            'datos': data,
            'logo_path': logo_uri, 
            'consignataria_nombre': 'Ortiz y Cía. Consignatarios'
        }
        
        # Personalizar el contexto según la plantilla que se está usando
        if template_name == "invernada_template.html":
            context.update({
                'fecha_reporte': first_row.get('fecha_consulta_inicio', 'N/A'),
                'fecha_reporte_fin': first_row.get('fecha_consulta_fin', 'N/A'),
                'fuente': 'DeCampoACampo',
                'tipo_hacienda': 'INVERNADA' # Título principal del header
            })
        else: # Asumir es la plantilla del MAG (report_template.html)
            context.update({
                'fecha_reporte': first_row.get('fecha_consulta_inicio', 'N/A'),
                'fuente': 'Mercado Agroganadero (MAG)',
                'tipo_hacienda': first_row.get('tipo_hacienda', 'FAENA') # (ej. FAENA)
            })
        
        # Renderizar el HTML
        html_out = template.render(context)
        
        output_path = os.path.join(OUTPUT_DIR, filename)
        
        # Escribir el PDF
        # base_url es crucial para que WeasyPrint encuentre la ruta del logo (file:///)
        HTML(string=html_out, base_url=PROJECT_ROOT).write_pdf(output_path) 
        
        print(f"Reporte PDF generado exitosamente en: {output_path}")
        return output_path
        
    except Exception as e:
        print(f"Error al generar el reporte PDF ({filename}): {e}")
        import traceback
        traceback.print_exc()
        return None

# --- Bloque de prueba principal ---
if __name__ == "__main__":
    print("--- Este módulo (report_generator.py) no está diseñado para ejecutarse directamente ---")
    print("Genera reportes llamando a 'main.py' (que a su vez llama a los scrapers).")
    print("Para probar, ejecuta: python main.py --debug")
    
  

