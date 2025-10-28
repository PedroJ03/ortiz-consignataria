import sqlite3
import requests
from datetime import datetime
import sys
import os
from dotenv import load_dotenv # <-- Importar dotenv

# Cargar variables de entorno desde .env (si existe)
load_dotenv() 

# Asegurar que los módulos del proyecto sean encontrables
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

# Importar nuestros módulos
try:
    from scrapers import mag_scraper
    from database import db_manager
    from reports import report_generator
    from utils import email_sender # <-- NUEVA IMPORTACIÓN
except ModuleNotFoundError:
    print("Error: No se pudieron encontrar los módulos. Revisa __init__.py.")
    sys.exit(1)

# --- Configuración (Leer destinatario desde .env) ---
RECIPIENT_EMAIL = os.environ.get('REPORT_RECIPIENT_EMAIL', "destinatario_por_defecto@ejemplo.com") # Email del stakeholder

def ejecutar_proceso_completo(fecha_consulta_str, debug=False):
    """
    Orquesta scraping, almacenamiento, generación de reportes y envío por email.
    """
    print(f"\n--- INICIANDO PROCESO COMPLETO PARA FECHA: {fecha_consulta_str} ---")
    
    conn = None 
    all_scraped_data = []
    tipos_hacienda = ['FAENA', 'INVERNADA', 'TODOS'] 
    registros_insertados = 0
    pdf_paths_generados = [] # <-- NUEVO: Lista para guardar rutas de PDFs

    try:
        # --- Obtener Conexión a BBDD ---
        conn = db_manager.get_db_connection()
        print("Conexión a la base de datos establecida.")

        # --- Crear tabla si no existe ---
        db_manager.crear_tabla(conn)

        # --- FASE 1: SCRAPING ---
        print("\n[FASE 1: SCRAPING MAG]")
        for tipo in tipos_hacienda:
            print(f"\n--- Ejecutando scraper para tipo: {tipo} ---")
            # Corrección: Pasar fecha_inicio y fecha_fin
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
                print(f"Éxito: Se insertaron {registros_insertados} registros.")
            else:
                print("No se insertaron nuevos registros.")
        else:
            print("No hay datos extraídos para almacenar.")


        # --- FASE 3: GENERACIÓN DE REPORTES ---
        print("\n[FASE 3: GENERACIÓN DE REPORTES PDF]")
        datos_dia_completo = report_generator.fetch_latest_data(fecha_consulta_str)

        if not datos_dia_completo:
            print("No se encontraron datos en la BBDD. No se generarán reportes ni se enviará email.")
        else:
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
                        pdf_paths_generados.append(pdf_path) 
                        reportes_generados += 1
                    else:
                        print(f"FALLO al generar reporte PDF para {tipo}.")
                else:
                    print(f"No hay datos específicos para {tipo} para generar reporte.")
            print(f"\nGeneración de reportes finalizada. Se crearon {reportes_generados} archivos PDF.")

            # --- FASE 4: ENVÍO DE EMAIL (NUEVO) ---
            print("\n[FASE 4: ENVÍO DE EMAIL]")
            if pdf_paths_generados: # Solo enviar si se generó al menos un PDF
                if not RECIPIENT_EMAIL or RECIPIENT_EMAIL == "destinatario_por_defecto@ejemplo.com":
                     print("ADVERTENCIA: No se configuró REPORT_RECIPIENT_EMAIL en el archivo .env o variable de entorno.")
                     print("El email NO será enviado.")
                else:
                    subject = f"Reporte de Precios MAG - {fecha_consulta_str}"
                    body = f"Adjunto se encuentran los reportes de precios del Mercado Agroganadero para el día {fecha_consulta_str}, separados por tipo de hacienda.\n\n"
                    body += f"- Registros extraídos: {len(all_scraped_data)}\n"
                    #body += f"- Registros insertados en BBDD: {registros_insertados}\n\n"
                    body += "Este es un correo generado automáticamente."
                    
                    # Llamar al módulo de envío
                    email_sent = email_sender.send_report_email(RECIPIENT_EMAIL, subject, body, pdf_paths_generados)
                    
                    if email_sent:
                        print(f"Email con reportes enviado exitosamente a {RECIPIENT_EMAIL}.")
                    else:
                        print("FALLO el envío del email. Revisa los logs del módulo email_sender para más detalles.")
            else:
                print("No se generaron PDFs válidos, no se enviará email.")

    # ... (Manejo de Errores y Finally - Sin Cambios, pero ahora cubren el envío de email) ...
    except sqlite3.Error as e: print(f"\n--- ERROR CRÍTICO (Base de Datos) ---\nError: {e}"); print("PROCESO FINALIZADO (CON ERRORES)")
    except requests.RequestException as e: print(f"\n--- ERROR CRÍTICO (Scraper/Red) ---\nError: {e}"); print("PROCESO FINALIZADO (CON ERRORES)")
    except Exception as e: print(f"\n--- ERROR CRÍTICO (Inesperado) ---\nError: {e}"); import traceback; traceback.print_exc(); print("PROCESO FINALIZADO (CON ERRORES)")
    finally:
        if conn: conn.close(); print("\nConexión a la base de datos cerrada.")

    print(f"\n--- PROCESO COMPLETO FINALIZADO PARA FECHA: {fecha_consulta_str} ---")
    print(f"Total registros extraídos: {len(all_scraped_data)}")
    print(f"Total registros insertados: {registros_insertados}")


# --- Bloque de Ejecución Principal (Sin Cambios) ---
if __name__ == "__main__":
    fecha_hoy = datetime.now().strftime("%d/%m/%Y")
    #fecha_a_ejecutar = fecha_hoy
    fecha_a_ejecutar= "21/10/2025"
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
