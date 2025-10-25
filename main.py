import sys
import sqlite3
import requests
from datetime import datetime
import os

# Asegurar que los módulos del proyecto sean encontrables
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

# Importar nuestros módulos
try:
    from scrapers import mag_scraper
    from database import db_manager
    from reports import report_generator # <-- Importar el generador
except ModuleNotFoundError:
    print("Error: No se pudieron encontrar los módulos 'scrapers', 'database' o 'reports'.")
    print("Asegúrate de que los archivos '__init__.py' existen en esas carpetas.")
    sys.exit(1)

def ejecutar_proceso_completo(fecha_consulta_str, debug=False):
    """
    Orquesta todo el proceso: scraping para todos los tipos,
    almacenamiento y generación de reportes PDF separados.
    """
    print(f"\n--- INICIANDO PROCESO COMPLETO PARA FECHA: {fecha_consulta_str} ---")

    conn = None
    all_scraped_data = []
    tipos_hacienda = ['FAENA', 'INVERNADA', 'TODOS']
    registros_insertados = 0 # Inicializar contador

    try:
        # --- Obtener Conexión a BBDD ---
        conn = db_manager.get_db_connection()
        print("Conexión a la base de datos establecida.")

        # --- Crear tabla si no existe ---
        db_manager.crear_tabla(conn)

        # --- FASE 1: SCRAPING (Iterar por cada tipo) ---
        print("\n[FASE 1: SCRAPING MAG]")
        for tipo in tipos_hacienda:
            print(f"\n--- Ejecutando scraper para tipo: {tipo} ---")
            datos_tipo = mag_scraper.scrape_mag(fecha_consulta_str, tipo_hacienda=tipo, debug=debug)
            if datos_tipo:
                all_scraped_data.extend(datos_tipo)
                print(f"Scraper {tipo} finalizado. Se encontraron {len(datos_tipo)} registros.")
            else:
                print(f"Scraper {tipo} no encontró datos.")
        print(f"\nScraping completado. Total de registros extraídos: {len(all_scraped_data)}")

        # --- FASE 2: ALMACENAMIENTO ---
        print("\n[FASE 2: ALMACENAMIENTO]")
        if all_scraped_data:
            registros_insertados = db_manager.insertar_datos(conn, all_scraped_data)
            if registros_insertados > 0:
                print(f"Éxito: Se insertaron {registros_insertados} registros en la base de datos.")
            else:
                print("No se insertaron nuevos registros.")
        else:
            print("No hay datos extraídos para almacenar.")

        # --- FASE 3: GENERACIÓN DE REPORTES (Integrado) ---
        print("\n[FASE 3: GENERACIÓN DE REPORTES PDF]")

        # 3a. Obtener TODOS los datos del día desde la BBDD (usando la función del generador)
        datos_dia_completo = report_generator.fetch_latest_data(fecha_consulta_str)

        if not datos_dia_completo:
            print(f"No se encontraron datos en la BBDD para la fecha {fecha_consulta_str}. No se generarán reportes.")
        else:
            # 3b. Filtrar y generar reporte para cada tipo
            reportes_generados = 0
            for tipo in tipos_hacienda:
                print(f"\n--- Generando reporte para tipo: {tipo} ---")
                datos_filtrados = [d for d in datos_dia_completo if d['tipo_hacienda'] == tipo]

                if datos_filtrados:
                    fecha_archivo = fecha_consulta_str.replace('/', '-')
                    filename_pdf = f"reporte_MAG_{tipo}_{fecha_archivo}.pdf"
                    pdf_path = report_generator.generate_pdf_report(datos_filtrados, filename=filename_pdf)
                    if pdf_path:
                        print(f"Reporte PDF para {tipo} generado en '{pdf_path}'.")
                        reportes_generados += 1
                    else:
                        print(f"FALLO al generar reporte PDF para {tipo}.")
                else:
                    print(f"No hay datos específicos para {tipo} en la BBDD para generar reporte.")
            print(f"\nGeneración de reportes finalizada. Se crearon {reportes_generados} archivos PDF.")

    except sqlite3.Error as e:
        print(f"\n--- ERROR CRÍTICO (Base de Datos) ---")
        print(f"Error de SQLite: {e}")
        print("PROCESO FINALIZADO (CON ERRORES)")
    except requests.RequestException as e:
        print(f"\n--- ERROR CRÍTICO (Scraper/Red) ---")
        print(f"Error de Red: {e}")
        print("PROCESO FINALIZADO (CON ERRORES)")
    except Exception as e:
        print(f"\n--- ERROR CRÍTICO (Inesperado) ---")
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        print("PROCESO FINALIZADO (CON ERRORES)")
    finally:
        if conn:
            conn.close()
            print("\nConexión a la base de datos cerrada.")

    print(f"\n--- PROCESO COMPLETO FINALIZADO PARA FECHA: {fecha_consulta_str} ---")
    print(f"Total registros extraídos: {len(all_scraped_data)}")
    print(f"Total registros insertados: {registros_insertados}")

# --- Bloque de Ejecución Principal ---
if __name__ == "__main__":
    """
    Punto de entrada principal. Por defecto, ejecuta para HOY.
    Argumentos: [fecha DD/MM/YYYY] [--debug]
    """
    fecha_hoy = datetime.now().strftime("%d/%m/%Y")
    fecha_a_ejecutar = fecha_hoy
    modo_debug = False

    if len(sys.argv) > 1:
        for arg in sys.argv[1:]:
            if arg == "--debug":
                modo_debug = True
            else:
                try:
                    datetime.strptime(arg, "%d/%m/%Y")
                    fecha_a_ejecutar = arg
                except ValueError:
                    print(f"Argumento '{arg}' no reconocido. Usando fecha de hoy.")

    print(f"Iniciando ejecución para la fecha: {fecha_a_ejecutar}")
    if modo_debug: print("Modo DEBUG activado.")

    #ejecutar_proceso_completo(fecha_a_ejecutar, debug=modo_debug)

    # --- Prueba manual ---
    print("\n--- EJECUTANDO PRUEBA MANUAL PARA EL 17/10/2025 ---")
    ejecutar_proceso_completo("17/10/2025", debug=True)