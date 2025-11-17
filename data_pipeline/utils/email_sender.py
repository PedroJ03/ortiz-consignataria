import smtplib
import os
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from datetime import datetime
from dotenv import load_dotenv # <-- Importar dotenv

# Cargar variables de entorno desde .env (si existe)
# Es importante llamarlo antes de acceder a las variables
load_dotenv() 

# Práctica Profesional: Usar variables de entorno para credenciales
EMAIL_SENDER = os.environ.get('EMAIL_SENDER_ADDRESS')
EMAIL_PASSWORD = os.environ.get('EMAIL_SENDER_PASSWORD') # ¡Usar contraseña de aplicación si es Gmail!
SMTP_SERVER = os.environ.get('SMTP_SERVER', 'smtp.gmail.com') # Default Gmail
SMTP_PORT = int(os.environ.get('SMTP_PORT', 587)) # Default Gmail (TLS)

# --- Definir PROJECT_ROOT aquí también para que el bloque de prueba funcione ---
# Obtiene la ruta del directorio actual (utils), luego sube un nivel
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) 


def send_report_email(recipient_email, subject, body, attachment_paths):
    """
    Envía un correo electrónico con archivos adjuntos (los reportes PDF).

    :param recipient_email: Dirección del destinatario.
    :param subject: Asunto del correo.
    :param body: Cuerpo del mensaje (texto plano).
    :param attachment_paths: Lista de rutas a los archivos PDF a adjuntar.
    :return: True si el envío fue exitoso, False en caso contrario.
    """
    if not EMAIL_SENDER or not EMAIL_PASSWORD:
        print("ERROR: Faltan variables de entorno EMAIL_SENDER_ADDRESS o EMAIL_SENDER_PASSWORD.")
        print("Asegúrate de que estén definidas en tu archivo .env o en el sistema.")
        print("El correo no puede ser enviado.")
        return False
        
    if not recipient_email or recipient_email == "correo_destinatario_prueba@ejemplo.com":
        print("ERROR: No se especificó un destinatario válido en la llamada a la función o en la variable de prueba.")
        return False

    # Crear el mensaje
    msg = MIMEMultipart()
    msg['From'] = EMAIL_SENDER
    msg['To'] = recipient_email
    msg['Subject'] = subject

    # Añadir cuerpo del mensaje
    msg.attach(MIMEText(body, 'plain'))

    # Adjuntar archivos
    for path in attachment_paths:
        if not os.path.exists(path):
            print(f"ADVERTENCIA: No se encontró el archivo adjunto: {path}")
            continue
            
        filename = os.path.basename(path)
        try:
            with open(path, "rb") as attachment:
                part = MIMEBase('application', 'octet-stream')
                part.set_payload(attachment.read())
            encoders.encode_base64(part)
            part.add_header(
                'Content-Disposition',
                f"attachment; filename= {filename}",
            )
            msg.attach(part)
            print(f"Archivo adjuntado: {filename}")
        except Exception as e:
            print(f"Error al adjuntar el archivo {filename}: {e}")

    # Enviar el correo
    server = None # Inicializar para el finally
    try:
        print(f"Conectando al servidor SMTP: {SMTP_SERVER}:{SMTP_PORT}...")
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.ehlo() # Saludar al servidor
        server.starttls() # Usar TLS para conexión segura
        server.ehlo() # Saludar de nuevo después de TLS
        print("Iniciando sesión...")
        server.login(EMAIL_SENDER, EMAIL_PASSWORD)
        print("Enviando correo...")
        text = msg.as_string()
        server.sendmail(EMAIL_SENDER, recipient_email, text)
        print(f"Correo enviado exitosamente a {recipient_email}.")
        return True
    except smtplib.SMTPAuthenticationError:
         print("ERROR: Falló la autenticación SMTP. Revisa el email y contraseña (o contraseña de aplicación) en tu archivo .env.")
         return False
    except smtplib.SMTPServerDisconnected:
        print("ERROR: El servidor SMTP se desconectó inesperadamente. Intenta de nuevo.")
        return False
    except Exception as e:
        print(f"Error al enviar el correo: {e}")
        import traceback
        traceback.print_exc() # Imprime más detalles del error
        return False
    finally:
        if server:
            try:
                server.quit()
                print("Conexión SMTP cerrada.")
            except Exception:
                pass 

# --- Bloque para probar este módulo individualmente ---
if __name__ == "__main__":
    print("--- Ejecutando prueba del módulo de envío de email ---")
    
    # --- ¡CONFIGURACIÓN DE PRUEBA! ---
    # 1. Asegúrate de tener tu archivo .env en la raíz del proyecto
    #    con EMAIL_SENDER_ADDRESS y EMAIL_SENDER_PASSWORD.
    
    # 2. Reemplaza esta línea con TU email para recibir la prueba:
    test_recipient = "pedrojossi03@gmail.com" 
    
    # 3. Verifica que tengas archivos PDF en la carpeta 'output'
    #    (ejecuta main.py con una fecha válida si no los tienes)
    test_pdf_path_base = os.path.join(PROJECT_ROOT, 'output') # <-- RUTA CORREGIDA
    
    # Intenta buscar PDFs con fecha de hoy o una fecha fija (ej. 17-10-2025)
    fecha_prueba_archivo = "17-10-2025" # datetime.now().strftime("%d-%m-%Y") 
    
    test_attachments = [
        os.path.join(test_pdf_path_base, f"reporte_MAG_TODOS_{fecha_prueba_archivo}.pdf"),
        os.path.join(test_pdf_path_base, f"reporte_MAG_FAENA_{fecha_prueba_archivo}.pdf"),
        os.path.join(test_pdf_path_base, f"reporte_MAG_INVERNADA_{fecha_prueba_archivo}.pdf") 
    ]
    
    # Verificar si las variables de entorno se cargaron
    if not EMAIL_SENDER or not EMAIL_PASSWORD:
         print("\n--- PRUEBA NO EJECUTADA ---")
         print("ERROR: No se pudieron leer EMAIL_SENDER_ADDRESS o EMAIL_SENDER_PASSWORD.")
         print("Verifica que el archivo .env exista en la raíz del proyecto y contenga las variables.")
         
    # Verificar si se puso un email de destinatario válido
    elif not test_recipient or test_recipient == "correo_destinatario_prueba@ejemplo.com":
         print("\n--- PRUEBA NO EJECUTADA ---")
         print("Edita el script 'utils/email_sender.py' y cambia 'test_recipient' a tu dirección de correo real.")
         
    else:
        # Si todo está bien, intentar enviar
        subject = f"Prueba Reporte Consignataria - {datetime.now().strftime('%d/%m/%Y %H:%M')}"
        body = "Este es un correo de prueba automático generado por el sistema de reportes.\n\n"
        body += f"Remitente: {EMAIL_SENDER}\n"
        body += "Verifica que los archivos PDF estén adjuntos.\n\nSaludos."
        
        # Filtrar adjuntos que realmente existen
        attachments_existentes = [p for p in test_attachments if os.path.exists(p)]
        if not attachments_existentes:
             print(f"ADVERTENCIA: No se encontraron archivos PDF de prueba con fecha {fecha_prueba_archivo} en '{test_pdf_path_base}' para adjuntar.")
             print("Asegúrate de haber ejecutado main.py para esa fecha.")
        else:
             print(f"Intentando adjuntar: {', '.join(os.path.basename(p) for p in attachments_existentes)}")

        # Llamar a la función de envío
        send_report_email(test_recipient, subject, body, attachments_existentes)


