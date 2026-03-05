import os
import resend

# Utilizamos el mismo logger que el resto de bases
from shared_code.logger_config import setup_logger
logger = setup_logger('Email_Service')

def enviar_correo(destinatario, asunto, cuerpo_html):
    """
    Envía un correo usando la API de Resend (para evadir bloqueos SMTP en la nube).
    Requiere la variable de entorno RESEND_API_KEY.
    Si no está configurada, hace 'fallback' y falla ordenadamente simulando el correo.
    """
    resend.api_key = os.environ.get('RESEND_API_KEY')
    
    # Utilizamos el dominio oficial ya verificado en Resend
    remitente = "Sistema Ortiz <no-reply@ortizconsignatarios.com.ar>"

    if not resend.api_key:
        logger.warning(f"No hay RESEND_API_KEY activa. Correo retenido para {destinatario}: Asunto: {asunto}")
        return False

    try:
        params = {
            "from": remitente,
            "to": [destinatario],
            "subject": asunto,
            "html": cuerpo_html
        }
        
        email = resend.Emails.send(params)
        logger.info(f"Correo enviado exitosamente a {destinatario} via Resend. ID: {email['id']}")
        return True
    
    except Exception as e:
        error_msg = f"Error eviando correo a {destinatario} vía Resend: {str(e)}"
        print(f"CRITICAL RESEND ERROR: {error_msg}")
        logger.error(error_msg)
        return False
