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
    
    NOTA: Se envía individualmente a cada destinatario (sin BCC) para evitar
    que Gmail marque como spam o retenga los emails con adjuntos.
    El problema "delivered delayed" de Gmail ocurre con BCC + adjuntos.
    
    :param destinatarios: Puede ser una lista ['a@a.com', 'b@b.com'] o un string 'a@a.com'
    :return: True si todos se enviaron correctamente, False si alguno falló
    """
    resend.api_key = os.getenv('RESEND_API_KEY')
    
    if not resend.api_key:
        print("Error: Credencial RESEND_API_KEY no configurada.")
        return False

    # Utilizamos el dominio oficial ya verificado en Resend
    remitente = "Reportes Ortiz <reportes@ortizconsignatarios.com.ar>"

    # Normalizar destinatarios a lista si viene como string
    if isinstance(destinatarios, str):
        if ',' in destinatarios:
            lista_destinatarios = [email.strip() for email in destinatarios.split(',')]
        else:
            lista_destinatarios = [destinatarios]
    else:
        lista_destinatarios = destinatarios

    # Preparar archivos adjuntos
    attachments_payload = []
    for archivo_path in archivos_adjuntos:
        if os.path.exists(archivo_path):
            try:
                with open(archivo_path, 'rb') as f:
                    file_data = f.read()
                    file_name = os.path.basename(archivo_path)
                
                attachments_payload.append({
                    "filename": file_name,
                    "content": list(file_data)
                })
            except Exception as e:
                print(f"Error adjuntando {archivo_path}: {e}")
        else:
            print(f"Advertencia: El archivo {archivo_path} no existe.")

    # Enviar individualmente a cada destinatario
    # Esto evita el "delivered delayed" de Gmail que ocurre con BCC + adjuntos
    exitosos = 0
    fallidos = 0
    
    for destinatario in lista_destinatarios:
        try:
            params = {
                "from": remitente,
                "to": [destinatario],  # Individual - evita delays de Gmail
                "subject": asunto,
                "html": cuerpo,
                "attachments": attachments_payload
            }
            
            email = resend.Emails.send(params)
            print(f"✅ Enviado a {destinatario} - ID: {email['id']}")
            exitosos += 1
            
        except Exception as e:
            print(f"❌ Error enviando a {destinatario}: {e}")
            fallidos += 1
    
    print(f"\nResumen: {exitosos} exitosos, {fallidos} fallidos de {len(lista_destinatarios)} destinatarios")
    
    # Retornar True solo si todos fueron exitosos
    return fallidos == 0
