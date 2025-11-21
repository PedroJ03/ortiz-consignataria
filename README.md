# Sistema de Precios de Hacienda - Ortiz y Cia. Consignatarios

Plataforma digital integral para la captura, almacenamiento, análisis y visualización de precios del mercado ganadero (Faena e Invernada).

![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=flat&logo=python&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-Web_Framework-000000?style=flat&logo=flask&logoColor=white)
![SQLite](https://img.shields.io/badge/SQLite-Database-003B57?style=flat&logo=sqlite&logoColor=white)
![TailwindCSS](https://img.shields.io/badge/Tailwind_CSS-Style-38B2AC?style=flat&logo=tailwind-css&logoColor=white)

## 📋 Descripción del Proyecto

Este sistema automatiza la inteligencia de mercado para la consignataria **"Ortiz y Cia. Consignatarios"**. Su objetivo es eliminar la recolección manual de datos y proveer herramientas de decisión en tiempo real mediante un Dashboard interactivo y reportes automatizados.

**Funcionalidades Principales:**
* **Pipeline de Datos (ETL):** Scrapers robustos que extraen datos diarios del Mercado Agroganadero (MAG) y tendencias semanales de Invernada. Incluye manejo de sesiones dinámicas y reintentos automáticos.
* **Base de Datos Optimizada:** Almacenamiento en SQLite con fechas estandarizadas en formato ISO-8601 (`YYYY-MM-DD`) para consultas de alto rendimiento.
* **Dashboard Interactivo:** Interfaz web moderna con gráficos mixtos (Precio vs. Volumen), zoom interactivo, filtros en cascada y agrupación temporal inteligente (Diario/Semanal/Mensual).
* **Reportes Automáticos:** Generación de PDFs con identidad corporativa listos para distribución.
* **Observabilidad:** Sistema de logging jerárquico con alertas automáticas por email ante fallos críticos.

## 🏗 Arquitectura del Sistema (Monorepo)

El proyecto utiliza una arquitectura modular organizada como monorepo para centralizar la lógica de negocio y facilitar el mantenimiento.

```bash
ortiz-consignataria/
├── data_pipeline/       # Motor de Extracción y Procesamiento
│   ├── scrapers/        # Lógica de extracción (MAG, Invernada)
│   ├── reports/         # Generación de PDFs (Templates HTML + CSS)
│   └── utils/           # Scripts de mantenimiento (Backfills, Limpieza)
├── web_app/             # Aplicación Web (Flask + Tailwind)
│   ├── static/          # Assets (Imágenes, Logos)
│   ├── templates/       # Vistas HTML (Dashboard, Inicio)
│   └── app.py           # Punto de entrada de la Web App
├── shared_code/         # Código Compartido (Nexo)
│   ├── database/        # Gestión centralizada de SQLite
│   └── logger_config.py # Configuración de Logs y Alertas SMTP
├── logs/                # Historial de ejecución (Rotación automática)
└── precios_historicos.db # Archivo de base de datos
```

## 🚀 Instalación y Configuración

### 1\. Requisitos Previos

  * Python 3.8 o superior.
  * Git.

### 2\. Instalación

```bash
# Clonar el repositorio
git clone <url-del-repositorio>
cd ortiz-consignataria

# Crear entorno virtual
python -m venv entorno_consignataria

# Activar entorno
# En Linux/Mac:
source entorno_consignataria/bin/activate
# En Windows:
entorno_consignataria\Scripts\activate

# Instalar dependencias (Web y Pipeline)
pip install -r web_app/requirements_web.txt
pip install -r data_pipeline/requirements_pipeline.txt
```

### 3\. Configuración de Variables de Entorno (.env)

Crea un archivo `.env` en la raíz del proyecto. **Este paso es obligatorio** para que funcionen los scrapers y las alertas.

```ini
# --- CONFIGURACIÓN MAG (SCRAPER) ---
MAG_USER=tu_usuario_mag
MAG_CP=codigo
# URL directa al formulario de consulta
MAG_URL_BASE=[https://www.mercadoagroganadero.com.ar/dll/hacienda1.dll/haciinfo000502](https://www.mercadoagroganadero.com.ar/dll/hacienda1.dll/haciinfo000502)
MAG_URL_POST=[https://www.mercadoagroganadero.com.ar/dll/hacienda1.dll/haciinfo000502](https://www.mercadoagroganadero.com.ar/dll/hacienda1.dll/haciinfo000502)

# --- CONFIGURACIÓN TÉCNICA ---
USER_AGENT="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
LOG_LEVEL=INFO

# --- ALERTAS POR EMAIL (SMTP) ---
# Configuración para enviar correos ante errores CRÍTICOS
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=tu_email@gmail.com
SMTP_PASSWORD=tu_contraseña_de_aplicacion_16_digitos
ALERT_RECIPIENT=email_destino@gmail.com
```

## 💻 Uso del Sistema

### Ejecutar la Aplicación Web

Para iniciar el servidor de desarrollo:

```bash
python web_app/app.py
```

El dashboard estará disponible en `http://localhost:5000`.

### Ejecutar Actualización de Datos (Scrapers)

Para actualizar la base de datos con los últimos datos disponibles (ideal para Cron Jobs):

  * **Faena (MAG):**
    ```bash
    python data_pipeline/utils/backfill_faena.py
    ```
  * **Invernada:**
    ```bash
    python data_pipeline/utils/backfill_invernada.py
    ```

## 📡 Sistema de Logs y Mantenimiento

El sistema cuenta con `shared_code/logger_config.py` que gestiona la salud de la aplicación:

1.  **Logs Locales (`logs/app.log`):** Registro histórico de operaciones. Usa `RotatingFileHandler` (máx 5MB, 5 backups) para no saturar el disco.
2.  **Alertas SMTP:** Si ocurre un error de nivel `ERROR` o `CRITICAL` (ej: cambio de estructura HTML en MAG, fallo de conexión a BD), el sistema envía un email inmediato al `ALERT_RECIPIENT`.

## ☁️ Despliegue
El proyecto está configurado para desplegarse en **PythonAnywhere** debido a su compatibilidad nativa con SQLite persistente y Tareas Programadas.
* Consultar `docs/ADR_002_Seleccion_Infraestructura.md` para detalles de la decisión arquitectónica.

## 📄 Licencia y Créditos

Desarrollado exclusivamente para **Ortiz y Cia. Consignatarios**.
