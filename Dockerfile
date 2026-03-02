# Usamos una imagen de Python oficial de Debian (slim para que sea más liviana)
FROM python:3.10-slim

# Evita que Python escriba archivos .pyc en el disco duro
ENV PYTHONDONTWRITEBYTECODE 1
# Evita que Python haga buffering en stdout y stderr (útil para ver logs en Railway)
ENV PYTHONUNBUFFERED 1
# Agrega el directorio raíz al PYTHONPATH para evitar errores de módulos
ENV PYTHONPATH=/app

# Instalamos las dependencias del sistema operativo que necesita tu proyecto
# ffmpeg: para moviepy
# dependencias pango/cairo: para WeasyPrint (Generación de PDFs)
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ffmpeg \
        libpango-1.0-0 \
        libpangoft2-1.0-0 \
        libcairo2 \
        libffi-dev \
        python3-dev \
        build-essential \
    && rm -rf /var/lib/apt/lists/*

# Establecemos el directorio de trabajo dentro del contenedor
WORKDIR /app

# Copiamos primero los requerimientos para aprovechar la caché de Docker
COPY web_app/requirements_web.txt web_app/requirements_web.txt
COPY data_pipeline/requirements_pipeline.txt data_pipeline/requirements_pipeline.txt

# Instalamos las dependencias de Python combinadas
RUN pip install --no-cache-dir -r web_app/requirements_web.txt
RUN pip install --no-cache-dir -r data_pipeline/requirements_pipeline.txt

# Instalamos Gunicorn, que es el servidor de producción para Flask
RUN pip install --no-cache-dir gunicorn

# Ahora copiamos el resto de tu código al contenedor
COPY . /app

# Creamos un directorio seguro para las bases de datos (este será el "Volumen" persistente en Railway)
# y le damos permisos
RUN mkdir -p /app/data && chmod -R 777 /app/data

# Por defecto, exponemos el puerto 8000
EXPOSE 8000

# Comando para ejecutar la aplicación en producción con Gunicorn
# NOTA: Gunicorn apuntará a la variable 'app' dentro de web_app/app.py
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "3", "--timeout", "120", "web_app.app:app"]
