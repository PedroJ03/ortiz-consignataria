import sys
import os
import time
import argparse
from datetime import datetime
from dotenv import load_dotenv

# --- 1. CONFIGURACIÓN DE RUTAS ---
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Cargar variables
load_dotenv(os.path.join(project_root, '.env'))

# --- 2. IMPORTACIONES ---
try:
    from shared_code.database import db_manager
    from shared_code.logger_config import setup_logger
    from data_pipeline.scrapers import mag_scraper, cac_scraper
    from data_pipeline.reports import report_generator
    from data_pipeline.utils import email_sender
except ImportError as e:
    print(f"CRITICAL ERROR: Falló la importación de módulos: {e}")
    sys.exit(1)

# Inicializar Logger
logger = setup_logger('Pipeline_Orquestador')

# Configuración Email
RECIPIENT_EMAIL = os.getenv('ALERT_RECIPIENT') # O una variable específica CLIENT_EMAILS

def ejecutar_pipeline_diario(enviar_email=True):
    logger.info(f"--- INICIANDO PIPELINE (Email: {enviar_email}) ---")
    
    hoy = datetime.now()
    hoy_str = hoy.strftime("%d/%m/%Y")
    
    conn = db_manager.get_db_connection()
    if not conn:
        logger.critical("Abortando pipeline: Sin conexión a BBDD.")
        return

    # Asegurar tablas
    db_manager.crear_tablas(conn)

    reportes_generados = []
    resumen_faena = 0
    resumen_invernada = 0

    try:
        # ---------------------------------------------------------
        # PASO 1: FAENA (MAG)
        # ---------------------------------------------------------
        logger.info(f"1. Procesando FAENA para fecha: {hoy_str}")
        datos_faena = mag_scraper.scrape_mag_faena(hoy_str, hoy_str)
        
        if datos_faena:
            # Insertar
            count = db_manager.insertar_datos_faena(conn, datos_faena)
            resumen_faena = len(datos_faena)
            logger.info(f"   -> Faena: {count} registros insertados/actualizados.")
            
            # Generar PDF
            try:
                # Usamos la función genérica o específica según tu report_generator
                path_pdf = report_generator.generate_pdf_report(
                    datos_faena,
                    filename=f"reporte_Faena_{hoy.strftime('%Y-%m-%d')}.pdf",
                    template_name="report_template.html"
                )
                if path_pdf:
                    reportes_generados.append(path_pdf)
                    logger.info(f"   -> PDF Faena generado: {os.path.basename(path_pdf)}")
            except Exception as e:
                logger.error(f"Error generando PDF Faena: {e}")
        else:
            logger.warning("   -> No hubo datos de Faena hoy.")

        # ---------------------------------------------------------
        # PASO 2: INVERNADA (DeCampoACampo)
        # ---------------------------------------------------------
        logger.info("2. Procesando INVERNADA (Datos Diarios/Semanales)")
        datos_invernada = cac_scraper.scrape_invernada_diario()
        
        if datos_invernada:
            # Insertar
            count_inv = db_manager.insertar_datos_invernada(conn, datos_invernada)
            resumen_invernada = len(datos_invernada)
            logger.info(f"   -> Invernada: {count_inv} registros insertados/actualizados.")
            
            # Generar PDF
            try:
                path_pdf = report_generator.generate_pdf_report(
                    datos_invernada,
                    filename=f"reporte_Invernada_{hoy.strftime('%Y-%m-%d')}.pdf",
                    template_name="invernada_template.html"
                )
                if path_pdf:
                    reportes_generados.append(path_pdf)
                    logger.info(f"   -> PDF Invernada generado: {os.path.basename(path_pdf)}")
            except Exception as e:
                logger.error(f"Error generando PDF Invernada: {e}")
        else:
            logger.warning("   -> No se obtuvieron datos de Invernada.")

        # ---------------------------------------------------------
        # PASO 3: ENVÍO DE EMAIL
        # ---------------------------------------------------------
        if reportes_generados:
            if enviar_email:
                if not RECIPIENT_EMAIL:
                    logger.warning("No se configuró destinatario de email. Omitiendo envío.")
                else:
                    logger.info(f"3. Enviando {len(reportes_generados)} reportes a {RECIPIENT_EMAIL}...")
                    
                    asunto = f"Reporte de Precios Hacienda - {hoy_str}"
                    cuerpo = (f"Consignataria Ortiz y Cia. le acerca los reportes del día:\n\n"
                              f"- Faena: {resumen_faena} registros procesados.\n"
                              f"- Invernada: {resumen_invernada} registros procesados.\n\n"
                              f"Adjuntos encontrará los documentos PDF detallados.")

                    exito = email_sender.send_report_email(
                        RECIPIENT_EMAIL,
                        asunto,
                        cuerpo,
                        reportes_generados
                    )
                    
                    if exito:
                        logger.info("   -> Email enviado correctamente.")
                    else:
                        logger.error("   -> Falló el envío del email.")
            else:
                logger.info("3. Omitiendo envío de email (Modo silencioso --no-email).")
        else:
            logger.info("3. No hay reportes nuevos para enviar hoy.")

    except Exception as e:
        logger.exception("Excepción CRÍTICA no controlada en el Pipeline Principal.")
    
    finally:
        if conn: conn.close()
        logger.info("--- PIPELINE FINALIZADO ---")

if __name__ == "__main__":
    # Configurar argumentos de línea de comandos para el Cron Job
    parser = argparse.ArgumentParser(description="Orquestador del Pipeline de Datos")
    
    # Argumento opcional: --no-email
    # Si se pasa, la variable args.no_email será True.
    parser.add_argument("--no-email", action="store_true", help="Ejecutar sin enviar reportes por correo (Solo actualización DB)")
    
    args = parser.parse_args()
    
    # Si args.no_email es True, entonces enviar_email debe ser False
    ejecutar_pipeline_diario(enviar_email=not args.no_email)