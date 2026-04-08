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

# Si no existe CLIENT_EMAILS, usamos ALERT_RECIPIENT como fallback
RAW_RECIPIENTS = os.getenv('CLIENT_EMAILS', os.getenv('ALERT_RECIPIENT'))

# Convertimos el string "mail1, mail2" en lista ['mail1', 'mail2']
LISTA_DESTINATARIOS = [email.strip() for email in RAW_RECIPIENTS.split(',') if email.strip()]

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

def _calcular_variacion_faena(conn, datos_faena):
    """
    Enriquece los datos de faena con la variación semanal calculada.
    Consulta el precio más cercano disponible a 7 días atrás para cada registro.
    Si no hay datos exactos de -7 días, busca el último dato disponible anterior.
    """
    from datetime import datetime, timedelta
    
    cursor = conn.cursor()
    datos_enriquecidos = []
    
    for item in datos_faena:
        # Calcular fecha de hace 7 días
        fecha_actual = datetime.strptime(item['fecha_consulta_inicio'], '%d/%m/%Y')
        fecha_7dias_atras = (fecha_actual - timedelta(days=7)).strftime('%Y-%m-%d')
        
        # Consultar el precio más reciente disponible antes o en la fecha de hace 7 días
        # Esto maneja casos donde no hay datos exactos (fin de semana, feriado)
        cursor.execute("""
            SELECT precio_promedio_kg, fecha_consulta
            FROM faena 
            WHERE fecha_consulta <= ? 
            AND categoria_original = ? 
            AND (raza = ? OR (raza IS NULL AND ? IS NULL))
            AND (rango_peso = ? OR (rango_peso IS NULL AND ? IS NULL))
            ORDER BY fecha_consulta DESC
            LIMIT 1
        """, (
            fecha_7dias_atras,
            item['categoria_original'],
            item.get('raza', ''), item.get('raza', ''),
            item.get('rango_peso', ''), item.get('rango_peso', '')
        ))
        
        row = cursor.fetchone()
        if row and row[0] and row[0] > 0:
            precio_referencia = row[0]
            fecha_referencia = row[1]
            precio_actual = item['precio_promedio_kg']
            variacion = round(((precio_actual - precio_referencia) / precio_referencia) * 100, 2)
            item['variacion_semanal_precio'] = variacion
            # Guardamos la fecha de referencia para debugging
            item['fecha_referencia_variacion'] = fecha_referencia
        else:
            item['variacion_semanal_precio'] = None
            item['fecha_referencia_variacion'] = None
        
        datos_enriquecidos.append(item)
    
    return datos_enriquecidos


def ejecutar_pipeline_diario(enviar_email=True):
    logger.info(f"--- INICIANDO PIPELINE (Email: {enviar_email}) ---")
    
    hoy = datetime.now()
    hoy_str = hoy.strftime("%d/%m/%Y")
    
    conn = db_manager.get_db_connection()
    if not conn:
        logger.critical("Abortando pipeline: Sin conexión a BBDD.")
        return

    # Asegurar tablas
    db_manager.crear_tablas_market(conn)
    db_manager.crear_tablas_precios(conn)

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
            
            # Enriquecer datos con variación semanal antes de generar PDF
            logger.info("   -> Calculando variación semanal para el reporte...")
            datos_faena_con_variacion = _calcular_variacion_faena(conn, datos_faena)
            
            # Generar PDF
            try:
                path_pdf = report_generator.generate_pdf_report(
                    datos_faena_con_variacion,
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
                if not LISTA_DESTINATARIOS:
                    logger.warning("No hay destinatarios configurados en CLIENT_EMAILS.")
                else:
                    logger.info(f"3. Enviando reportes a {len(LISTA_DESTINATARIOS)} destinatarios...")
                    
                    asunto = f"Reporte de Precios Hacienda - {hoy_str}"
                    cuerpo = (f"Consignataria Ortiz y Cia. le acerca los reportes del día:\n\n"
                              f"- Faena: {resumen_faena} registros.\n"
                              f"- Invernada: {resumen_invernada} registros.\n\n"
                              f"Adjuntos encontrará los documentos PDF detallados.")

                    # Pasamos la LISTA, el sender ya sabe manejar el BCC
                    exito = email_sender.send_report_email(
                        LISTA_DESTINATARIOS,
                        asunto,
                        cuerpo,
                        reportes_generados
                    )
                    
                    if exito:
                        logger.info("   -> Email enviado correctamente a la lista de distribución.")
                    else:
                        logger.error("   -> Falló el envío del email.")
            else:
                logger.info("3. Omitiendo envío de email (Modo silencioso).")

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