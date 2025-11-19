import requests # Importar requests para el manejo de excepciones
import sys
from datetime import datetime
import os
from dotenv import load_dotenv
import sqlite3 # <-- RE-INTRODUCIDO

# Cargar variables de entorno desde .env (si existe)
load_dotenv()

# 1. Encontrar la raíz del proyecto (un nivel arriba de 'data_pipeline')
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 2. Añadir la raíz al sys.path para que Python pueda encontrar 'shared_code'
sys.path.insert(0, project_root)


# Importar nuestros módulos
try:
    from data_pipeline.scrapers import mag_scraper, cac_scraper # <-- NOMBRE CORREGIDO
    from shared_code.database import db_manager # <-- RE-INTRODUCIDO
    from data_pipeline.reports import report_generator
    from data_pipeline.utils import email_sender
except ModuleNotFoundError:
    print("Error: No se pudieron encontrar los módulos. Revisa __init__.py.")
    sys.exit(1)

# Configuración (Leer destinatario desde .env)
RECIPIENT_EMAIL = os.environ.get('REPORT_RECIPIENT_EMAIL', "destinatario_por_defecto@ejemplo.com")

def ejecutar_proceso_completo(fecha_consulta_str, debug=False):
    """
    Orquesta scraping, almacenamiento en BBDD separadas,
    generación de reportes PDF separados y envío por email.
    """
    print(f"\n--- INICIANDO PROCESO COMPLETO PARA FECHA: {fecha_consulta_str} ---")

    datos_mag_faena = []
    datos_campo_invernada = []
    pdf_paths_generados = [] # Lista para guardar rutas de PDFs
    
    # --- Contadores para el resumen ---
    total_registros_faena_insertados = 0
    total_registros_invernada_insertados = 0
    
    conn = None # Definir conn aquí para que exista en el bloque finally

    try:
        # --- (NUEVO) FASE 0: CONEXIÓN BBDD ---
        conn = db_manager.get_db_connection()
        if not conn:
            print("ERROR FATAL: No se pudo conectar a la base de datos.")
            return # Salir si no hay BBDD
            
        print(f"Conexión a la base de datos '{db_manager.DB_PATH}' establecida.")
        
        # --- (NUEVO) Crear tablas si no existen ---
        db_manager.crear_tablas(conn) # Pasamos la conexión

        # --- FASE 1: SCRAPING ---
        print("\n[FASE 1: SCRAPING]")

        # 1a. Scraper MAG (Solo Faena)
        print("\n--- Ejecutando scraper MAG (Faena) ---")
        datos_mag_faena = mag_scraper.scrape_mag_faena(fecha_consulta_str, fecha_consulta_str, debug=debug)
        if datos_mag_faena:
            print(f"Scraper MAG (Faena) finalizado. Se encontraron {len(datos_mag_faena)} registros.")
        else:
            print("Scraper MAG (Faena) no encontró datos.")

        # 1b. Scraper DeCampoACampo (Invernada)
        print("\n--- Ejecutando scraper DeCampoACampo (Invernada) ---")
        datos_campo_invernada = cac_scraper.scrape_invernada_diario(debug=debug)
        if datos_campo_invernada:
            print(f"Scraper DeCampoACampo (Invernada) finalizado. Se encontraron {len(datos_campo_invernada)} registros.")
        else:
            print("Scraper DeCampoACampo (Invernada) no encontró datos.")

        # --- FASE 2: ALMACENAMIENTO (MODIFICADO) ---
        print("\n[FASE 2: ALMACENAMIENTO]")
        
        if datos_mag_faena:
            total_registros_faena_insertados = db_manager.insertar_datos_faena(conn, datos_mag_faena)
            print(f"Éxito: Se insertaron {total_registros_faena_insertados} nuevos registros en 'faena'.")
        else:
            print("No hay datos de Faena para almacenar.")
            
        if datos_campo_invernada:
            total_registros_invernada_insertados = db_manager.insertar_datos_invernada(conn, datos_campo_invernada)
            print(f"Éxito: Se insertaron {total_registros_invernada_insertados} nuevos registros en 'invernada'.")
        else:
            print("No hay datos de Invernada para almacenar.")

        # --- FASE 3: GENERACIÓN DE REPORTES (Era tu FASE 2) ---
        print("\n[FASE 3: GENERACIÓN DE REPORTES PDF]")
        reportes_generados = 0
        fecha_archivo = fecha_consulta_str.replace('/', '-') 

        # 3a. Generar reporte MAG (Faena)
        if datos_mag_faena:
            print("\n--- Generando reporte para Faena ---")
            filename_pdf_mag = f"reporte_Faena_{fecha_archivo}.pdf"
            pdf_path_mag = report_generator.generate_pdf_report(
                datos_mag_faena,
                filename=filename_pdf_mag,
                template_name="report_template.html" 
            )
            if pdf_path_mag:
                print(f"Reporte PDF para Faena generado en '{pdf_path_mag}'.")
                pdf_paths_generados.append(pdf_path_mag)
                reportes_generados += 1
            else:
                print("FALLO al generar reporte PDF para Faena.")
        else:
            print("No hay datos de MAG Faena para generar reporte.")

        # 3b. Generar reporte DeCampoACampo (Invernada)
        if datos_campo_invernada:
            print("\n--- Generando reporte para Invernada ---")
            filename_pdf_campo = f"reporte_Invernada_{fecha_archivo}.pdf"
            pdf_path_campo = report_generator.generate_pdf_report(
                datos_campo_invernada,
                filename=filename_pdf_campo,
                template_name="invernada_template.html"
            )
            if pdf_path_campo:
                print(f"Reporte PDF para Invernada generado en '{pdf_path_campo}'.")
                pdf_paths_generados.append(pdf_path_campo)
                reportes_generados += 1
            else:
                print("FALLO al generar reporte PDF para Invernada.")
        else:
            print("No hay datos de Invernada para generar reporte.")

        print(f"\nGeneración de reportes finalizada. Se crearon {reportes_generados} archivos PDF.")

        # --- FASE 4: ENVÍO DE EMAIL (Era tu FASE 3) ---
        print("\n[FASE 4: ENVÍO DE EMAIL]")
        if pdf_paths_generados: 
            if not RECIPIENT_EMAIL or RECIPIENT_EMAIL == "destinatario_por_defecto@ejemplo.com": # <-- Condición de seguridad
                 print("ADVERTENCIA: No se configuró REPORT_RECIPIENT_EMAIL en el archivo .env.")
                 print("El email NO será enviado.")
            else:
                subject = f"Reporte de Precios Consignataria Ortiz y Cia - {fecha_consulta_str}"
                body = f"Consignataria Ortiz y Cia te acerca los reportes de precios del {fecha_consulta_str}:\n\n"
                body += f"- Faena: {len(datos_mag_faena)} registros.\n"
                body += f"- Invernada: {len(datos_campo_invernada)} registros.\n\n"
                body += "Este es un correo generado automáticamente."

                email_sent = email_sender.send_report_email(RECIPIENT_EMAIL, subject, body, pdf_paths_generados)

                if email_sent:
                    print(f"Email con reportes enviado exitosamente a {RECIPIENT_EMAIL}.")
                else:
                    print("FALLO el envío del email.")
        else:
            print("No se generaron PDFs válidos, no se enviará email.")

    # --- Manejo de Errores Actualizado ---
    except sqlite3.Error as e:
        print(f"\n--- ERROR CRÍTICO (Base de Datos) ---")
        print(f"Error de SQLite: {e}")
        print("PROCESO FINALIZADO (CON ERRORES)")
    except requests.RequestException as e: 
        print(f"\n--- ERROR CRÍTICO (Scraper/Red) ---\nError: {e}"); 
        print("PROCESO FINALIZADO (CON ERRORES)")
    except Exception as e: 
        print(f"\n--- ERROR CRÍTICO (Inesperado) ---\nError: {e}"); 
        import traceback; traceback.print_exc(); 
        print("PROCESO FINALIZADO (CON ERRORES)")
    finally:
        # --- (NUEVO) Cerrar la conexión ---
        if conn:
            conn.close()
            print("\nConexión a la base de datos cerrada.")


    print(f"\n--- PROCESO COMPLETO FINALIZADO PARA FECHA: {fecha_consulta_str} ---")
    print(f"Total registros Faena insertados: {total_registros_faena_insertados}")
    print(f"Total registros Invernada insertados: {total_registros_invernada_insertados}")


# --- Bloque de Ejecución Principal (Sin Cambios) ---
if __name__ == "__main__":
    fecha_hoy = datetime.now().strftime("%d/%m/%Y")
    fecha_a_ejecutar = fecha_hoy
    modo_debug = False

    if len(sys.argv) > 1:
        for arg in sys.argv[1:]:
            if arg == "--debug": modo_debug = True
            else:
                try: datetime.strptime(arg, "%d/%m/%Y"); fecha_a_ejecutar = arg
                except ValueError: print(f"Argumento '{arg}' no reconocido. Usando fecha de hoy.")

    print(f"Iniciando ejecución para la fecha: {fecha_a_ejecutar}")
    if modo_debug: print("Modo DEBUG activado.")

    ejecutar_proceso_completo(fecha_a_ejecutar, debug=modo_debug)

    # --- Prueba manual ---
    # print("\n--- EJECUTANDO PRUEBA MANUAL PARA EL 17/10/2025 ---")
    # ejecutar_proceso_completo("17/10/2025", debug=True)