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
        import socket
        
        # Hack para forzar IPv4
        try:
            ipv4_ip = socket.gethostbyname(smtp_server)
        except socket.gaierror:
            ipv4_ip = smtp_server # fallback
            
        if smtp_port == 465:
            # Port 465 requiere conexión SSL implícita desde el inicio
            server = smtplib.SMTP_SSL(timeout=5)
            server.connect(ipv4_ip, smtp_port)
            server.ehlo()
        else:
            # Port 587 requiere conexión estándar y luego STARTTLS
            server = smtplib.SMTP(timeout=5)
            server.connect(ipv4_ip, smtp_port)
            server.ehlo()
            server.starttls() # Asegura la conexión con TLS
            
        server.login(smtp_user, smtp_password)
        server.sendmail(smtp_user, destinatario, msg.as_string())
        server.quit()
        logger.info(f"Correo enviado exitosamente a {destinatario}")
        return True
    except Exception as e:
        error_msg = f"Error enviando correo a {destinatario}: {str(e)}"
        print(f"CRITICAL SMTP ERROR: {error_msg}")  # Failsafe console print
        logger.error(error_msg)
        return False
