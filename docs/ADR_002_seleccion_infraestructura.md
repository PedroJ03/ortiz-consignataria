# ADR 002: Selección de Infraestructura de Despliegue (Railway)

**Estado:** Aceptado (Reemplaza decisión anterior sobre PythonAnywhere)
**Fecha:** 5 de Marzo de 2026
**Decisor:** Pedro Jossi

## 1. Contexto Modificado
Originalmente, el proyecto "Ortiz y Cía." se desplegó en PythonAnywhere debido a la facilidad para manejar bases de datos SQLite nativas y Cron Jobs en un entorno académico/inicial.
Sin embargo, el software evolucionó incorporando funcionalidades multimedia complejas:
1.  **Motor WeasyPrint:** Requiere librerías C nativas (`pango`, `cairo`).
2.  **Validación Magic Bytes:** Requiere `libmagic1`.
3.  **Compresión de Video:** Requiere `ffmpeg` instalado a nivel sistema operativo para que `MoviePy` pueda procesar subidas de los usuarios.

La incapacidad de PythonAnywhere para escalar y permitir instalaciones profundas de binarios C a nivel de sistema operativo impidió la ejecución de estas nuevas dependencias. Se requería una infraestructura que soportara contenedores Docker para inyectar dichas librerías.

## 2. Opciones Evaluadas para la Migración

### A. VPS Tradicional (DigitalOcean, AWS EC2)
* **Pros:** Control absoluto del sistema operativo, permitiendo instalar cualquier binario.
* **Contras:** Sobrecarga gigante de mantenimiento (SysAdmin). Requiere gestionar llaves SSH, actualizaciones de seguridad de Linux, configuración manual de Nginx/Gunicorn y rotación de certificados SSL.

### B. Heroku / Render
* **Pros:** PaaS modernos con excelente soporte para contenedores Docker.
* **Contras:** Sistemas de archivos efímeros. Al no soportar discos persistentes nativos (sin plugins costosos), cada vez que se reiniciaba el contenedor se eliminaba la base de datos `marketplace.db`, `precios_historicos.db` y todos los videos de los usuarios. Nos forzaba a re-escribir el proyecto entero a PostgreSQL y AWS S3.

### C. Railway (PaaS con Volúmenes Persistentes)
* **Pros:** Soporta despliegue nativo mediante `Dockerfile` (permitiendo instalar `ffmpeg` y `libmagic` fácilmente). Además, ofrece **Volúmenes Persistentes** nativos, lo que significa que podemos montar una carpeta (`/app/data`) que sobrevive a los redespliegues, manteniendo intactas nuestras bases SQLite as-is y las subidas estáticas.
* **Contras:** La capa gratuita es medida, requiere una curva de aprendizaje mínima para mapear el volumen en el `Dockerfile`.

## 3. Decisión
Se ha decidido migrar y utilizar **Railway** como la infraestructura definitiva de producción, orquestando el entorno mediante un `Dockerfile`.

## 4. Justificación
Railway provee el "sweet spot" exacto que exige el proyecto actualmente:
1.  **Libertad de SO:** La contenedorización con `python:3.10-slim` nos permitió instalar las bibliotecas pesadas de compresión pre-compiladas sin fricción.
2.  **Cero Refactorización de Código:** Gracias al Volumen Persistente de Railway (`/app/data`), pudimos mantener nuestra arquitectura ligera basada en doble SQLite y el almacenamiento local de videos sin tener que migrar meses de código hacia Buckets S3 de AWS y bases de datos SQL en red.

## 5. Consecuencias
* **Positivas:** 
  * Se implementó compresión de video y seguridad deep-file (Magic bytes) con éxito.
  * Los despliegues ahora son reproducibles localmente construyendo la imagen Docker.
* **Negativas:**
  * Mayor complejidad en la configuración inicial (`railway.json`, montaje de discos en el Dashboard).
* **Acciones de Migración (Completadas):**
  * Se escribió el `Dockerfile`.
  * Se modificaron las rutas duras en `.env` hacia variables de entorno de nube (`RAILWAY_VOLUME_MOUNT_PATH`).
  * Se implementó Gunicorn como servidor WSGI de producción (`web_app.app:app`).