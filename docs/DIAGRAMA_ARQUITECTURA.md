# Diagrama de Arquitectura: Ortiz Consignataria

Este documento visualiza el flujo y la estructura del **Monorepo** y su conexión transversal usando bases de datos SQLite como pasarela persistente bajo contenedores.

```mermaid
flowchart TD
    %% Entidades Externas
    MAG(["M.A.G (Mercado Agroganadero)"])
    CAC(["C.A.C (Tendencias Invernada)"])
    Clients(["Clientes (Navegador)"])
    Admins(["Administradores"])
    EmailClient(["Destinatarios Email"])

    %% Data Pipeline
    subgraph Pipeline["Data Pipeline (Cron Job)"]
        Scraper["Scrapers Dinámicos\n(BeautifulSoup/Requests)"]
        PDF["Generador de Reportes\n(WeasyPrint)"]
        EmailService["Sistema de Distribución\n(API Resend)"]
        
        Scraper --> PDF
        PDF --> EmailService
    end

    %% Web App
    subgraph Web["App Web (Flask / Gunicorn)"]
        Auth["Auth & Roles\n(Flask-Login)"]
        VideoOpt["Optimizador de Video\n(MoviePy + FFmpeg)"]
        DashAPI["API Dashboard\n(Rest JSON)"]
        Routes["Rutas (Jinja2)"]
        
        Routes <--> Auth
        Routes <--> DashAPI
    end

    %% Capa Compartida de Datos (Shared & Volumes)
    subgraph DataLayer["Capa de Base de Datos (Persistencia /app/data/)"]
        DB_Manager["db_manager.py\n(Shared Data Access Object)"]
        PreciosDB[("precios_historicos.db\n(Datos Analíticos)")]
        MarketDB[("marketplace.db\n(Lotes & Usuarios)")]
        MediaVol["/uploads/ \n(Volumen de Estáticos)"]
    end

    %% Flujos de Proceso ETL
    MAG -.->|Extracción Diaria| Scraper
    CAC -.->|Extracción Diaria| Scraper
    EmailService -.->|PDF Reports| EmailClient

    %% Flujos Internos de App -> DB
    Scraper -->|Escribe Historicos| DB_Manager
    DashAPI -->|Lee Historicos| DB_Manager
    Auth -->|Lee/Escribe Usuarios| DB_Manager
    Routes -->|Sube/Borra Lotes| DB_Manager
    Routes -->|Sube Media| VideoOpt
    VideoOpt -->|Comprime y Guarda| MediaVol

    %% Conexiones Físicas
    DB_Manager <--> PreciosDB
    DB_Manager <--> MarketDB

    %% Interacciones de Usuario
    Clients -->|Navega Market| Routes
    Clients -.->|Lee APs AJAX| DashAPI
    Admins -->|Gestiona Usuarios/Lotes\n Dashboard admin| Routes
```

## Referencias Claves del Diseño
1. **Desacoplamiento de Escalado**: El *Data Pipeline* puede correr en un cron job completamente desconectado del proceso maestro de Gunicorn (*App Web*).
2. **`db_manager.py` como Puente**: Todas las transacciones SQL puras pasan obligatoriamente por el manager compartido, previniendo cuellos de botella e hilos no cerrados.
3. **Volumen Único**: Puesto que se monta usando contenedores (p.ej en Railway), tanto los archivos multimedia ubicados en `/uploads/` como las bases `.db` se persistirán sobre ciclos destructivos de redespliegue.
