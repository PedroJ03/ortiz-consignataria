import logging
import logging.handlers
import os
import sys
from dotenv import load_dotenv

# Cargar entorno si no está cargado
load_dotenv()

# Configuración
LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'logs')
LOG_FILE = 'app.log'
SMTP_SERVER = os.getenv('SMTP_SERVER')
SMTP_PORT = int(os.getenv('SMTP_PORT', 587))
SMTP_USER = os.getenv('SMTP_USER')
SMTP_PASSWORD = os.getenv('SMTP_PASSWORD')
ALERT_RECIPIENT = os.getenv('ALERT_RECIPIENT')

# --- CLASE ESPECIAL PARA GMAIL/TLS ---
class TlsSMTPHandler(logging.handlers.SMTPHandler):
    """
    Manejador SMTP personalizado que fuerza el inicio de TLS (Seguridad)
    necesario para servidores modernos como Gmail.
    """
    def emit(self, record):
        try:
            import smtplib
            from email.message import EmailMessage
            import email.utils

            port = self.mailport
            if not port:
                port = smtplib.SMTP_PORT
            
            smtp = smtplib.SMTP(self.mailhost, port, timeout=10)
            
            # Identificación y TLS
            smtp.ehlo()
            if self.secure is not None:
                smtp.starttls(*self.secure)
                smtp.ehlo()
            
            # Login
            if self.username:
                smtp.login(self.username, self.password)
            
            # Construir Mensaje
            msg = EmailMessage()
            msg['Subject'] = self.getSubject(record)
            msg['From'] = self.fromaddr
            msg['To'] = ",".join(self.toaddrs)
            msg['Date'] = email.utils.formatdate()
            
            # Formatear el contenido del log
            content = self.format(record)
            msg.set_content(f"ALERTA DEL SISTEMA ORTIZ & CIA:\n\n{content}")

            smtp.send_message(msg)
            smtp.quit()
            
        except Exception:
            self.handleError(record)

def setup_logger(name):
    """
    Configura un logger con 3 salidas:
    1. Consola (INFO)
    2. Archivo Rotativo (INFO) - Guarda historial
    3. Email (ERROR/CRITICAL) - Avisa emergencias
    """
    # Crear directorio de logs si no existe
    if not os.path.exists(LOG_DIR):
        os.makedirs(LOG_DIR)

    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG) # Capturamos todo, los handlers filtran

    # Evitar duplicar logs si se llama varias veces
    if logger.hasHandlers():
        return logger

    # Formato profesional
    formatter_file = logging.Formatter('%(asctime)s | %(levelname)-8s | %(name)s | %(message)s')
    formatter_console = logging.Formatter('%(asctime)s | %(levelname)s | %(message)s', datefmt='%H:%M:%S')

    # 1. HANDLER DE ARCHIVO (Rotativo: 5MB x 5 archivos de backup)
    file_handler = logging.handlers.RotatingFileHandler(
        os.path.join(LOG_DIR, LOG_FILE), 
        maxBytes=5*1024*1024, 
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(formatter_file)
    logger.addHandler(file_handler)

    # 2. HANDLER DE CONSOLA
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter_console)
    logger.addHandler(console_handler)

    # 3. HANDLER DE EMAIL (Solo si hay credenciales)
    if SMTP_SERVER and SMTP_USER and SMTP_PASSWORD:
        mail_handler = TlsSMTPHandler(
            mailhost=(SMTP_SERVER, SMTP_PORT),
            fromaddr=SMTP_USER,
            toaddrs=[ALERT_RECIPIENT],
            subject=f"Sistema Consignataria Ortiz🚨 ALERTA CRÍTICA: {name}",
            credentials=(SMTP_USER, SMTP_PASSWORD),
            secure=() # Tupla vacía activa TLS
        )
        # Solo enviar email si es ERROR o CRITICAL
        mail_handler.setLevel(logging.ERROR) 
        mail_handler.setFormatter(formatter_file)
        logger.addHandler(mail_handler)
        # logger.info("Sistema de Alertas por Email: ACTIVO")
    else:
        logger.warning("Sistema de Alertas por Email: DESACTIVADO (Faltan credenciales en .env)")

    return logger