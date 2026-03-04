import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os

# Utilizamos el mismo logger que el resto de bases
from shared_code.logger_config import setup_logger
logger = setup_logger('Email_Service')

def enviar_correo(destinatario, asunto, cuerpo_html):
    """
    Envía un correo usando SMTP de manera síncrona.
    Requiere las variables de entorno SMTP configuradas (.env o entorno de prod).
    Si no están configuradas, hace 'fallback' y falla ordenadamente simulando el correo.
    """
    smtp_server = os.environ.get('SMTP_SERVER')
    smtp_port = os.environ.get('SMTP_PORT', '587') # 587 por defecto (TLS)
    smtp_user = os.environ.get('SMTP_USER')
    smtp_password = os.environ.get('SMTP_PASSWORD')
    smtp_from = os.environ.get('SMTP_FROM', smtp_user) # Puede ser "No Responder <no-reply@ortiz.com>"
    
    # Tratamos de castear el puerto
    try:
        smtp_port = int(smtp_port)
    except:
        smtp_port = 587

    # Si no hay config SMTP en entorno local, fallamos silenciosamente
    if not smtp_server or not smtp_user or not smtp_password:
        logger.warning(f"No hay configuración SMTP activa. Correo retenido para {destinatario}: Asunto: {asunto}")
        return False

    msg = MIMEMultipart("alternative")
    msg["Subject"] = asunto
    msg["From"] = smtp_from
    msg["To"] = destinatario

    mensaje_html = MIMEText(cuerpo_html, "html")
    msg.attach(mensaje_html)

    try:
        # Añadido timeout de 5 segundos para que la página web no se quede colgada.
        # FIX [Errno 101] Network is unreachable en Railway: forzamos explícitamente IPv4 mediante el kwarg local_hostname o definiendo un source_address.
        import socket
        server = smtplib.SMTP(timeout=5)
        # Hack para forzar IPv4, resolvemos explícitamente el DNS en ipv4 y conectamos por esa IP
        try:
            ipv4_ip = socket.gethostbyname(smtp_server)
        except socket.gaierror:
            ipv4_ip = smtp_server # fallback
        
        server.connect(ipv4_ip, smtp_port)
        server.ehlo()
        server.starttls() # Asegura la conexión
        server.login(smtp_user, smtp_password)
        # El comando SMTP MAIL FROM requiere sólo la dirección de correo (smtp_user)
        # El nombre para mostrar se envía únicamente en las cabeceras del msg (msg["From"])
        server.sendmail(smtp_user, destinatario, msg.as_string())
        server.quit()
        logger.info(f"Correo enviado exitosamente a {destinatario}")
        return True
    except Exception as e:
        error_msg = f"Error enviando correo a {destinatario}: {str(e)}"
        print(f"CRITICAL SMTP ERROR: {error_msg}")  # Failsafe console print
        logger.error(error_msg)
        return False
