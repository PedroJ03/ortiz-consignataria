# Sistema Integral y Marketplace - Ortiz y Cia. Consignatarios

🔗 **[Visitar el sitio web: ortizconsignatarios.com.ar](https://ortizconsignatarios.com.ar)**

Plataforma digital integral que combina un sistema automatizado de **Inteligencia de Mercado** (Scraping, ETL y Reportes de precios ganaderos) con un **Marketplace de Lotes interactivo**. Desarrollado bajo un patrón de Monorepo, está diseñado para automatizar labores comerciales y proporcionar información veraz en tiempo real a clientes y administradores.


![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=flat&logo=python&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-Web_Framework-000000?style=flat&logo=flask&logoColor=white)
![SQLite](https://img.shields.io/badge/SQLite-Database-003B57?style=flat&logo=sqlite&logoColor=white)
![TailwindCSS](https://img.shields.io/badge/Tailwind_CSS-Style-38B2AC?style=flat&logo=tailwind-css&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-Containerization-2496ED?style=flat&logo=docker&logoColor=white)

---

## Funcionalidades Principales

El sistema se compone de dos grandes módulos funcionales e interconectados:

### 1. Sistema de "Marketplace" (Aplicación Web)
* **Gestión de Lotes Multimedia:** Plataforma donde los usuarios autenticados pueden publicar lotes de hacienda subiendo contenido multimedia (fotos y videos).
* **Validación de Archivos "Magic Bytes":** La carga de imágenes y videos está estrictamente asegurada mediante el análisis de cabeceras de los archivos (`libmagic`), previniendo vulnerabilidades comunes de inyección de código encubierto.
* **Optimización Automática de Video:** Los videos subidos por los usuarios son procesados en segundo plano mediante `moviepy` y `FFmpeg` (reducción a 480p, 24 FPS y compresión libx264). Esto ahorra drásticamente el uso de almacenamiento y mejora los tiempos de carga web.
* **Dashboard Interactivo y Analítico:** Panel para clientes donde pueden visualizar históricos de precios mediante gráficos combinados y dinámicos, filtros multicriterio, exportación de tablas a formato `CSV` nativo y estados vacíos estilizados.
* **Sistema de Roles y Panel Admin (`/admin`):** Diferenciación entre usuarios corrientes y administradores. El panel de administración permite habilitar, deshabilitar o eliminar rápidamente las publicaciones.

### 2. Pipeline de Datos y Reportes (Cron Job & ETL)
* **Web Scraping y Extracción Diaria:** Extracción automática de la cotización diaria de ganado desde Mercado Agroganadero (MAG) y de Campo a Campo (CAC), manejando autenticación en sesión de forma dinámica.
* **Generación de Reportes PDF (`WeasyPrint`):** Consolidación de los datos extraídos en documentos PDF corporativos y listos para distribución.
* **Distribución Automatizada (Resend API):** Sistema automatizado que compone e-mails y distribuye el reporte diario (archivos adjuntos y KPI relevantes en el cuerpo) a una lista de difusión personalizable (`CLIENT_EMAILS` en `.env`) utilizando la infraestructura de Resend para mejor entregabilidad y evitar bloqueos SMTP.

---

## Arquitectura del Sistema (Monorepo)

El proyecto utiliza un patrón de Monorepo que separa lógicamente el proceso asíncrono ETL del despacho de tráfico web HTTP, pero comparten las librerías base.

```bash
ortiz-consignataria/
├── data_pipeline/         # Extracción web (MAG/CAC), orquestador y envío de reportes
├── web_app/               # Aplicación Flask, endpoints API, interfaces y templates HTML
├── shared_code/           # Lógica y entidades puente: Manejo de base de datos y Logs 
├── tests/                 # Suite de pruebas automatizadas (Pytest)
├── docs/                  # Documentación extendida (Arquitectura y ADRs)
├── precios_historicos.db  # Base de Datos Analítica: Alimentada por los Scrapers
└── marketplace.db         # Base de Datos Transaccional: Usuarios, Roles, Posts y Media
```
*(Para mayor detalle, consultar el archivo `docs/ADR_001_arquitectura_monorepo.md` en el repositorio).*

---

## Despliegue e Infraestructura (Docker & Railway)

El sistema ha sido nativamente vectorizado (Dockerizado) para un despliegue sin fricciones en **Railway**, garantizando la inyección de las dependencias nativas del sistema operativo.

### Requisitos del SO (Instalados vía Dockerfile)
La generación de PDFs con `WeasyPrint`, validación de archivos con `python-magic` y la compresión con `MoviePy` obligan tener herramientas precompiladas en C:
* `ffmpeg`
* `libpango-1.0-0`, `libpangoft2-1.0-0`, `libcairo2`
* `libmagic1`

### Volúmenes Persistentes
En el esquema del `Dockerfile`, se despliega un volumen en la ruta `/app/data/`. Allí residen ambas bases de datos SQLite y el contenido multimedia (`/uploads/`) de forma estática permanente a prueba de redespliegues.

---

## Requisitos e Instalación Local

> **IMPORTANTE:** Este proyecto impone la utilización del entorno virtual `entorno_consignataria` para poder ejecutar correctamente las librerías compartidas.

```bash
# 1. Clonar el repositorio
git clone <url-del-repositorio>
cd ortiz-consignataria

# 2. Crear y activar el entorno virtual
python -m venv entorno_consignataria
source entorno_consignataria/bin/activate  # o .\entorno_consignataria\Scripts\activate en Windows

# 3. Instalación de dependencias por módulo
pip install -r web_app/requirements_web.txt
pip install -r data_pipeline/requirements_pipeline.txt
```

### Configuración de Entorno (`.env`)
Crear un archivo `.env` en la raíz (ver `.env.example` en caso de existir) con la siguiente estructura base:

```ini
# Seguridades y Accesos
SECRET_KEY="clave_super_secreta_flask_aqui"

# Configuración Data Pipeline (MAG)
MAG_USER="usuario"
MAG_CP="codigo"
MAG_URL_BASE="url_endpoint"
MAG_URL_POST="url_endpoint_login"
# Opcional si utiliza un token avanzado: MAG_MASTER_TOKEN="..."

# Configuración Emails (Resend)
RESEND_API_KEY="re_123456789_xxxxxxxxxxxxxxxxxxxxxx"
CLIENT_EMAILS="cliente1@agronegocios.com,cliente2@campo.com"
EMAIL_SENDER_ADDRESS="tucorreo@empresa.com"
```

### Inicialización 
Antes de arrancar la aplicación por primera vez, prepara las bases concurrentes:

```bash
# 1. Generar la estructura SQL de las Bases de Datos
python data_pipeline/utils/init_marketplace.py

# 2. Inscribir al menos un usuario administrador
python data_pipeline/utils/set_admin.py usuario@empresa.com
```

---

## Uso y Comandos Diarios

* **Levantar el Servidor Web (Local):** `python web_app/app.py`
  * O usando gunicorn sugerido: `gunicorn --bind 0.0.0.0:8000 web_app.app:app`
* **Orquestador Diario (Descarga, Analiza, Crea PDF, Envía Emails):**
  ```bash
  python data_pipeline/main.py
  # Opcional (Correr ignorando los emails): python data_pipeline/main.py --no-email
  ```
* **Correr Suite de Pruebas Unitarias:**
  ```bash
  pip install -r requirements_test.txt
  pytest tests/
  ```
