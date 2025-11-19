import os
import pathlib
from datetime import datetime
from jinja2 import Environment, FileSystemLoader
from weasyprint import HTML


# 1. Directorio de este script (.../data_pipeline/reports)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# 2. Raíz del Proyecto (.../ortiz-consignataria)
# Subimos 2 niveles: reports -> data_pipeline -> RAÍZ
PROJECT_ROOT = os.path.dirname(os.path.dirname(BASE_DIR))
# 3. Rutas Específicas
TEMPLATE_DIR = os.path.join(BASE_DIR, 'templates')
# CORRECCIÓN: Los logos ahora están en web_app/static
STATIC_DIR = os.path.join(PROJECT_ROOT, 'web_app', 'static')
# La salida se guarda en data_pipeline/output
OUTPUT_DIR = os.path.join(PROJECT_ROOT, 'data_pipeline', 'output')

# Asegurarse de que la carpeta de salida exista
os.makedirs(OUTPUT_DIR, exist_ok=True)


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
        
        logo_filename = "logo_blanco.jpeg" 
        logo_abs_path = os.path.join(STATIC_DIR, 'images', logo_filename)
        
        logo_uri = None
        if os.path.exists(logo_abs_path):
            # Convertir a URI para que WeasyPrint lo entienda
            logo_uri = pathlib.Path(logo_abs_path).as_uri()
        else:
            print(f"ADVERTENCIA: No se encontró el logo en: {logo_abs_path}")

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
                'tipo_hacienda': 'INVERNADA' # Título principal del header
            })
        else: # Asumir es la plantilla del MAG (report_template.html)
            context.update({
                'fecha_reporte': first_row.get('fecha_consulta_inicio', 'N/A'),
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
    
  

