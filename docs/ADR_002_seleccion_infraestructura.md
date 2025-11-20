# ADR 002: Selección de Infraestructura de Despliegue (PythonAnywhere)

**Estado:** Aceptado
**Fecha:** 20 de Noviembre de 2025
**Decisor:** Pedro jossi

## 1. Contexto
El proyecto "Ortíz y Cía." ha evolucionado de scripts aislados a una aplicación web con arquitectura de Monorepo que integra:
1.  **Web App:** Flask para visualización de datos.
2.  **ETL:** Scrapers que se ejecutan periódicamente.
3.  **Base de Datos:** SQLite (`precios_historicos.db`) como fuente única de verdad.

Necesitamos un entorno de producción para desplegar el MVP que cumpla con los requisitos de bajo mantenimiento, costo reducido y compatibilidad con la arquitectura actual.

## 2. Opciones Evaluadas

### A. PaaS Modernos (Render, Railway, Heroku)
* **Pros:** Despliegue basado en contenedores (Docker), escalabilidad horizontal sencilla.
* **Contras (Bloqueante):** Utilizan sistemas de archivos efímeros. Cada despliegue o reinicio borra el disco local. Esto es incompatible con nuestra base de datos SQLite, obligando a una migración compleja a PostgreSQL.

### B. VPS (DigitalOcean, AWS EC2)
* **Pros:** Control total del sistema operativo y persistencia garantizada.
* **Contras:** Requiere configuración manual de servidores, seguridad, certificados SSL y mantenimiento del SO (Linux), lo cual aumenta la carga operativa ("High Maintenance").

### C. PythonAnywhere (PaaS Clásico)
* **Pros:** Entorno persistente nativo (compatible con SQLite), configuración visual de tareas programadas (Cron Jobs), y entorno específico para Python/Flask.
* **Contras:** Tecnologías más antiguas, sin soporte nativo para Docker.

## 3. Decisión
Se ha decidido utilizar **PythonAnywhere** como plataforma de despliegue para la etapa actual del proyecto.

## 4. Justificación
La decisión se basa en tres pilares fundamentales:

1.  **Persistencia de Datos (SQLite):** PythonAnywhere trata el sistema de archivos como un disco persistente tradicional. Esto permite que los scrapers escriban en `precios_historicos.db` y la Web App lea del mismo archivo sin configuraciones complejas de volúmenes ni migraciones de motor de base de datos.
2.  **Automatización Simplificada (Cron Jobs):** La plataforma ofrece una interfaz nativa para programar la ejecución de los scripts de scraping sin necesidad de administrar demonios de Linux (systemd/cron).
3.  **Costo-Eficiencia:** El nivel gratuito (o de bajo costo "Hacker") es suficiente para el tráfico y procesamiento actual, cumpliendo con el requisito presupuestario del cliente.

## 5. Consecuencias
* **Positivas:** Despliegue inmediato sin cambios en el código (`db_manager.py` permanece intacto). Mantenimiento operativo cercano a cero.
* **Negativas:** Se genera un acoplamiento a la infraestructura de PythonAnywhere.
* **Mitigación:** Si el proyecto escala masivamente en el futuro (>10,000 visitas/día), se planificará una migración a PostgreSQL + Render/AWS.