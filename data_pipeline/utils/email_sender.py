import os
import base64
import resend
from dotenv import load_dotenv

# Cargar entorno para asegurar que las credenciales estén disponibles
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
load_dotenv(os.path.join(project_root, '.env'))

def send_report_email(destinatarios, asunto, cuerpo, archivos_adjuntos=[]):
    """
    Envía un correo con adjuntos a una lista de destinatarios usando la API de Resend.
    Usa BCC (Copia Oculta) para proteger la privacidad de la lista.
    
    :param destinatarios: Puede ser una lista ['a@a.com', 'b@b.com'] o un string 'a@a.com'
    """
    resend.api_key = os.getenv('RESEND_API_KEY')
    
    if not resend.api_key:
        print("Error: Credencial RESEND_API_KEY no configurada.")
        return False

    # Para entorno de pruebas gratuito, Resend exige este remitente
    remitente = "Acme <onboarding@resend.dev>"

    # Normalizar destinatarios a lista si viene como string
    if isinstance(destinatarios, str):
        if ',' in destinatarios:
            lista_destinatarios = [email.strip() for email in destinatarios.split(',')]
        else:
            lista_destinatarios = [destinatarios]
    else:
        lista_destinatarios = destinatarios

    # Preparar archivos adjuntos (Resend requiere que se lean y encodeen antes de armar la petición, aunque la librería maneje el payload, le pasamos el contenido en crudo o base64 iterado)
    attachments_payload = []
    for archivo_path in archivos_adjuntos:
        if os.path.exists(archivo_path):
            try:
                with open(archivo_path, 'rb') as f:
                    file_data = f.read()
                    file_name = os.path.basename(archivo_path)
                
                # Resend prefiere directamente enviar un dic con filename y el contenido en bytes (o lista de enteros)
                # El SDK de python moderno permite pasar un string o bytes
                attachments_payload.append({
                    "filename": file_name,
                    "content": list(file_data) # El SDK de Resend parsea mejor array de bytes
                })
            except Exception as e:
                print(f"Error adjuntando {archivo_path}: {e}")
        else:
            print(f"Advertencia: El archivo {archivo_path} no existe.")

    # Enviar usando la API HTTP
    try:
        params = {
            "from": remitente,
            "to": [remitente], # Hack técnico: Te lo mandás a vos mismo como principal
            "bcc": lista_destinatarios, # Y todos los clientes van ocultos
            "subject": asunto,
            "html": cuerpo,
            "attachments": attachments_payload
        }
        
        email = resend.Emails.send(params)
        print(f"Correo de reporte enviado exitosamente. ID Resend: {email['id']}")
        return True
    
    except Exception as e:
        print(f"Error enviando email vía Resend: {e}")
        return False