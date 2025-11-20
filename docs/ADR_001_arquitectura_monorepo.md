# ADR 001: Adopción de Arquitectura de Monorepo Organizado

**Estado:** Aceptado
**Fecha:** 17 de Noviembre de 2025
**Decisores:** Pedro Jossi

## 1. Contexto
El proyecto "Ortiz y Cía. Consignatarios" nació como una solución monolítica donde la aplicación web (`app.py`) y el pipeline de datos (`main.py`) coexistían en la raíz del directorio, compartiendo un único archivo `requirements.txt` y mezclando responsabilidades.

Esta arquitectura monolítica presentaba los siguientes desafíos:
* **Despliegue Pesado:** La aplicación web se veía forzada a instalar dependencias pesadas de procesamiento de datos (como scrapers o generadores de PDF) que no utilizaba en tiempo de ejecución.
* **Acoplamiento:** El código de la interfaz de usuario y la lógica de extracción estaban entremezclados, dificultando el mantenimiento.
* **Escalabilidad Rígida:** No era posible escalar los servicios de forma independiente.

Se requería una reestructuración que permitiera desacoplar los servicios sin perder la consistencia de los datos compartidos.

## 2. Opciones Evaluadas

### A. Mantener Monolito (Status Quo)
* **Pros:** Simplicidad inicial, sin configuración de rutas de importación.
* **Contras:** Despliegues ineficientes, código "spaghetti", difícil de mantener a largo plazo.

### B. Multi-Repo (Dos Repositorios Separados)
* **Descripción:** Separar el proyecto en dos repositorios de Git distintos: uno para la Web App y otro para el Data Pipeline.
* **Pros:** Desacoplamiento total.
* **Contras (Bloqueante):** Alto riesgo de desincronización en el código compartido, específicamente en `db_manager.py`. Un cambio en el esquema de base de datos en un repositorio podría romper el otro, introduciendo bugs críticos.

### C. Monorepo Organizado
* **Descripción:** Mantener un único repositorio pero reestructurando carpetas internas para aislar contextos (`web_app/`, `data_pipeline/`) y centralizar la lógica común (`shared_code/`).
* **Pros:** Commits atómicos, dependencias separadas, código compartido único y consistente.
* **Contras:** Requiere configuración adicional de `sys.path` para las importaciones entre carpetas.

## 3. Decisión
Se ha decidido refactorizar el proyecto hacia una arquitectura de **Monorepo Organizado**.

La estructura adoptada será:
* `/web_app`: Contendrá la aplicación Flask, templates y assets estáticos.
* `/data_pipeline`: Contendrá scrapers, generación de reportes y scripts de mantenimiento.
* `/shared_code`: Contendrá la lógica de acceso a datos (`db_manager.py`) y configuraciones comunes.

## 4. Justificación
Esta arquitectura ofrece el mejor balance costo-beneficio para el estado actual del proyecto:

1.  **Cero Duplicación de Código:** Al centralizar `db_manager.py` en `shared_code/`, eliminamos el riesgo de inconsistencias en el manejo de la base de datos SQLite, que es el recurso crítico compartido.
2.  **Despliegues Independientes:** Cada módulo tendrá su propio `requirements.txt`. Esto permite que la Web App sea ligera en producción, instalando solo lo necesario para servir tráfico HTTP.
3.  **Integridad Transaccional (Git):** Los cambios que afectan tanto al scraper como a la web (ej. una nueva columna en la BD) se pueden realizar en un único "Atomic Commit", asegurando que el sistema siempre esté sincronizado.

## 5. Consecuencias
* **Positivas:**
    * Claridad en la separación de responsabilidades.
    * Reducción del tamaño de las imágenes de despliegue o entornos virtuales específicos.
    * Facilidad para onboardear nuevos desarrolladores en módulos específicos.
* **Negativas:**
    * Complejidad en la gestión de importaciones de Python (necesidad de manipular `sys.path` en los puntos de entrada).
* **Acciones Requeridas:**
    * Mover archivos a las nuevas carpetas (`web_app`, `data_pipeline`, `shared_code`).
    * Separar el `requirements.txt` monolítico en `requirements_web.txt` y `requirements_pipeline.txt`.
    * Ajustar los scripts de inicio (`app.py`, `backfill_*.py`) para incluir la raíz del proyecto en el `PYTHONPATH` o `sys.path`.