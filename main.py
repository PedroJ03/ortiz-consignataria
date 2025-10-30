import requests # Importar requests para el manejo de excepciones
import sys
from datetime import datetime
import os
from dotenv import load_dotenv

# Cargar variables de entorno desde .env (si existe)
load_dotenv()

# Asegurar que los módulos del proyecto sean encontrables
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

# Importar nuestros módulos
try:
    from scrapers import mag_scraper, cac_scraper # Importar ambos scrapers
    # Ya no necesitamos db_manager
    from reports import report_generator
    from utils import email_sender
except ModuleNotFoundError:
    print("Error: No se pudieron encontrar los módulos. Revisa __init__.py.")
    sys.exit(1)

# Configuración (Leer destinatario desde .env)
RECIPIENT_EMAIL = os.environ.get('REPORT_RECIPIENT_EMAIL', "destinatario_por_defecto@ejemplo.com")

def ejecutar_proceso_completo(fecha_consulta_str, debug=False):
    """
    Orquesta scraping de MAG (Faena) y DeCampoACampo (Invernada),
    generación de reportes PDF separados y envío por email.
    """
    print(f"\n--- INICIANDO PROCESO COMPLETO PARA FECHA: {fecha_consulta_str} ---")

    datos_mag_faena = []
    datos_campo_invernada = []
    pdf_paths_generados = [] # Lista para guardar rutas de PDFs

    try:
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
        datos_campo_invernada = cac_scraper.scrape_invernada_campo(debug=debug)
        if datos_campo_invernada:
            print(f"Scraper DeCampoACampo (Invernada) finalizado. Se encontraron {len(datos_campo_invernada)} registros.")
        else:
            print("Scraper DeCampoACampo (Invernada) no encontró datos.")

        # --- FASE 2: GENERACIÓN DE REPORTES (Sin BBDD) ---
        print("\n[FASE 2: GENERACIÓN DE REPORTES PDF]")
        reportes_generados = 0
        fecha_archivo = fecha_consulta_str.replace('/', '-') # Usar la fecha consultada en MAG como referencia

        # 2a. Generar reporte MAG (Faena)
        if datos_mag_faena:
            print("\n--- Generando reporte para MAG (Faena) ---")
            filename_pdf_mag = f"reporte_MAG_Faena_{fecha_archivo}.pdf"
            # Usamos la plantilla existente 'report_template.html'
            pdf_path_mag = report_generator.generate_pdf_report(
                datos_mag_faena,
                filename=filename_pdf_mag,
                template_name="report_template.html" # Plantilla para Faena
            )
            if pdf_path_mag:
                print(f"Reporte PDF para MAG (Faena) generado en '{pdf_path_mag}'.")
                pdf_paths_generados.append(pdf_path_mag)
                reportes_generados += 1
            else:
                print("FALLO al generar reporte PDF para MAG (Faena).")
        else:
            print("No hay datos de MAG (Faena) para generar reporte.")

        # 2b. Generar reporte DeCampoACampo (Invernada)
        if datos_campo_invernada:
            print("\n--- Generando reporte para DeCampoACampo (Invernada) ---")
            filename_pdf_campo = f"reporte_Campo_Invernada_{fecha_archivo}.pdf"
            pdf_path_campo = report_generator.generate_pdf_report(
                datos_campo_invernada,
                filename=filename_pdf_campo,
                template_name="invernada_template.html"
            )
            if pdf_path_campo:
                print(f"Reporte PDF para Campo (Invernada) generado en '{pdf_path_campo}'.")
                pdf_paths_generados.append(pdf_path_campo)
                reportes_generados += 1
            else:
                print("FALLO al generar reporte PDF para Campo (Invernada).")
        else:
            print("No hay datos de Campo (Invernada) para generar reporte.")

        print(f"\nGeneración de reportes finalizada. Se crearon {reportes_generados} archivos PDF.")

        # --- FASE 3: ENVÍO DE EMAIL ---
        print("\n[FASE 3: ENVÍO DE EMAIL]")
        if pdf_paths_generados: # Solo enviar si se generó al menos un PDF
            if not RECIPIENT_EMAIL or RECIPIENT_EMAIL == "destinatario_por_defecto@ejemplo.com":
                 print("ADVERTENCIA: No se configuró REPORT_RECIPIENT_EMAIL en el archivo .env.")
                 print("El email NO será enviado.")
            else:
                subject = f"Reporte de Precios Consignataria - {fecha_consulta_str}"
                body = f"Adjunto se encuentran los reportes de precios para el día {fecha_consulta_str}:\n\n"
                body += f"- MAG (Faena): {len(datos_mag_faena)} registros encontrados.\n"
                body += f"- DeCampoACampo (Invernada): {len(datos_campo_invernada)} registros encontrados.\n\n"
                body += "Este es un correo generado automáticamente."

                email_sent = email_sender.send_report_email(RECIPIENT_EMAIL, subject, body, pdf_paths_generados)

                if email_sent:
                    print(f"Email con reportes enviado exitosamente a {RECIPIENT_EMAIL}.")
                else:
                    print("FALLO el envío del email.")
        else:
            print("No se generaron PDFs válidos, no se enviará email.")

    except requests.RequestException as e: print(f"\n--- ERROR CRÍTICO (Scraper/Red) ---\nError: {e}"); print("PROCESO FINALIZADO (CON ERRORES)")
    except Exception as e: print(f"\n--- ERROR CRÍTICO (Inesperado) ---\nError: {e}"); import traceback; traceback.print_exc(); print("PROCESO FINALIZADO (CON ERRORES)")
    finally:
        # Ya no hay conexión de BBDD que cerrar
        print("\n--- LIMPIEZA FINALIZADA ---")


    print(f"\n--- PROCESO COMPLETO FINALIZADO PARA FECHA: {fecha_consulta_str} ---")
    print(f"Total registros MAG (Faena): {len(datos_mag_faena)}")
    print(f"Total registros Campo (Invernada): {len(datos_campo_invernada)}")


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

