import smtplib
import os
from email.message import EmailMessage
from dotenv import load_dotenv

# Cargar entorno para asegurar que las credenciales estén disponibles
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
load_dotenv(os.path.join(project_root, '.env'))

SMTP_SERVER = os.getenv('SMTP_SERVER')
SMTP_PORT = int(os.getenv('SMTP_PORT', 587))
SMTP_USER = os.getenv('SMTP_USER')
SMTP_PASSWORD = os.getenv('SMTP_PASSWORD')

def send_report_email(destinatarios, asunto, cuerpo, archivos_adjuntos=[]):
    """
    Envía un correo con adjuntos a una lista de destinatarios.
    Usa BCC (Copia Oculta) para proteger la privacidad de la lista.
    
    :param destinatarios: Puede ser una lista ['a@a.com', 'b@b.com'] o un string 'a@a.com'
    """
    if not SMTP_USER or not SMTP_PASSWORD:
        print("Error: Credenciales SMTP no configuradas.")
        return False

    # Normalizar destinatarios a lista si viene como string
    if isinstance(destinatarios, str):
        # Si viene separado por comas en un string, lo convertimos a lista
        if ',' in destinatarios:
            lista_destinatarios = [email.strip() for email in destinatarios.split(',')]
        else:
            lista_destinatarios = [destinatarios]
    else:
        lista_destinatarios = destinatarios

    msg = EmailMessage()
    msg['Subject'] = asunto
    msg['From'] = SMTP_USER
    
    # TÉCNICA PROFESIONAL:
    # 'To': Se pone el mismo remitente o un alias genérico.
    # 'Bcc': Aquí van los clientes. Ellos reciben el mail pero no ven a los otros.
    msg['To'] = SMTP_USER 
    msg['Bcc'] = ", ".join(lista_destinatarios)
    
    msg.set_content(cuerpo)

    # Adjuntar archivos PDF
    for archivo_path in archivos_adjuntos:
        if os.path.exists(archivo_path):
            try:
                with open(archivo_path, 'rb') as f:
                    file_data = f.read()
                    file_name = os.path.basename(archivo_path)
                
                msg.add_attachment(
                    file_data,
                    maintype='application',
                    subtype='pdf',
                    filename=file_name
                )
            except Exception as e:
                print(f"Error adjuntando {archivo_path}: {e}")
        else:
            print(f"Advertencia: El archivo {archivo_path} no existe.")

    # Enviar
    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as smtp:
            smtp.starttls()
            smtp.login(SMTP_USER, SMTP_PASSWORD)
            smtp.send_message(msg)
        return True
    except Exception as e:
        print(f"Error enviando email: {e}")
        return False