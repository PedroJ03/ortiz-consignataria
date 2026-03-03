# Sistema Integral y Marketplace - Ortiz y Cia. Consignatarios

Plataforma digital integral que combina **Inteligencia de mercado** (captura y análisis de precios ganaderos) con un **Marketplace de Lotes interactivo**, diseñado para automatizar labores comerciales e informar a clientes en tiempo real.

![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=flat&logo=python&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-Web_Framework-000000?style=flat&logo=flask&logoColor=white)
![SQLite](https://img.shields.io/badge/SQLite-Database-003B57?style=flat&logo=sqlite&logoColor=white)
![TailwindCSS](https://img.shields.io/badge/Tailwind_CSS-Style-38B2AC?style=flat&logo=tailwind-css&logoColor=white)

## Funcionalidades Principales

Este sistema está dividido en dos grandes pilares interconectados:

### 1. Sistema de "Marketplace" (Vidriera de Lotes)
* **Gestión de Usuarios y Roles:** Autenticación de usuarios segura (`Flask-Login`) con distinción entre cuentas de Administrador y Cliente.
* **Publicación de Lotes Multimedia:** Los usuarios pueden publicar lotes de hacienda subiendo fotos y videos.
* **Optimización Automática de Video:** Sistema integrado que comprime y optimiza silenciosamente los videos subidos por los usuarios usando `moviepy` y FFmpeg, ahorrando almacenamiento.
* **Panel de Administración (`/admin`):** Interfaz exclusiva para moderar usuarios y administrar las publicaciones (habilitar/eliminar lotes).

### 2. Pipeline de Datos y Reportes (ETL)
* **Scraping Automático:** Extracción de datos del Mercado Agroganadero (MAG) y Tendencias de Invernada (CAC) mediante sesión dinámica.
* **Generación de PDFs (`WeasyPrint`):** Reportes corporativos automatizados y programados diariamente.
* **Distribución por Email (`SMTP`):** Envío automático de los reportes PDF generados a una lista de clientes configurables.
* **Dashboard Interactivo:** Gráficos mixtos (Precio vs. Volumen), filtros en cascada y análisis temporal de los precios históricos.

## Arquitectura del Sistema (Monorepo)

El proyecto utiliza un patrón de Monorepo organizado con doble base de datos para separar la lógica analítica de la transaccional. *(Ver `docs/ADR_001_arquitectura_monorepo.md` para detalles).*

```bash
ortiz-consignataria/
├── data_pipeline/         # Extracción de MAG/CAC y Generación de KPIs y PDFs
├── web_app/               # Aplicación Flask Web y Rutas del Marketplace
├── shared_code/           # Código puente (Manager de Base de Datos y Logs)
├── tests/                 # Suite de pruebas unitarias y de integración (Pytest)
├── docs/                  # Documentación de Arquitectura de Decisiones (ADRs)
├── precios_historicos.db  # BD Analítica: Datos del Scraping
└── marketplace.db         # BD Transaccional: Usuarios, Lotes y Media
```

## Requisitos e Instalación

### 1. Dependencias del Sistema (S.O)
Dado que el sistema genera PDFs corporativos y comprime video, el servidor donde hospedes la app requerirá ciertas librerías del sistema instaladas:
* **FFmpeg:** Necesario para el procesamiento de `moviepy`.
* **Pango, Cairo, GDK-PixBuf:** Requeridos por `WeasyPrint` para estructurar los PDFs.

*(Si usas Linux/Ubuntu, puedes instalarlos con `sudo apt install ffmpeg libpango-1.0-0 libpangoft2-1.0-0`)*

### 2. Entorno Python

```bash
# Clonar y crear entorno
git clone <url-del-repositorio>
cd ortiz-consignataria
python -m venv entorno_consignataria
source entorno_consignataria/bin/activate  # o \Scripts\activate en Windows

# Instalar dependencias segmentadas
pip install -r web_app/requirements_web.txt
pip install -r data_pipeline/requirements_pipeline.txt
```

### 3. Configuración del .env

Debes crear un archivo `.env` en la raíz. Ahora requiere variables fundamentales de seguridad y mensajería:

```ini
SECRET_KEY="clave_super_secreta_flask_aqui"

# --- CONFIGURACIÓN MAG ---
MAG_USER="usuario"
MAG_CP="codigo"
MAG_URL_BASE="url_mag"
MAG_URL_POST="url_mag_post"

# --- SISTEMA DE EMAIL ---
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USER="tucorreo@empresa.com"
SMTP_PASSWORD="tu_app_password"
ALERT_RECIPIENT="admin@empresa.com"
CLIENT_EMAILS="cliente1@agronegocios.com, cliente2@campo.com" # Lista de distribución de PDFs
```

### 4. Inicialización del Marketplace

Antes de encender el servidor web, debes preparar la base de datos de usuarios:

```bash
# 1. Crea las tablas de la BD Marketplace
python data_pipeline/utils/init_marketplace.py

# 2. Registra un usuario desde la Interfaz Web o crea uno predeterminado, luego hazlo Admin:
# IMPORTANTE: Asegúrate de que el usuario ya existe en la BD antes de correr esto.
python data_pipeline/utils/set_admin.py tu_email_registrado@empresa.com
```

## Uso, Tareas Diarias y Testing

* **Servidor Web:** `python web_app/app.py`
* **Orquestador Diario (Descarga, Analiza, Crea PDF, Envía Emails):**
  ```bash
  # Este comando debería ponerse en un Cronjob en PythonAnywhere
  python data_pipeline/main.py
  ```
* **Suite de Pruebas (Tests):**
  ```bash
  pip install -r requirements_test.txt
  pytest tests/
  ```

## Infraestructura
Diseñado nativamente para ser desplegado en **PythonAnywhere** dado su soporte robusto para Cron Jobs puros (para los scrapers) y bases de datos basadas en archivos (SQLite x2). *(Referencia en `docs/ADR_002_seleccion_infraestructura.md`)*.
