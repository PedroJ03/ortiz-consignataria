import sys
import os
from datetime import datetime


# 1. Subir 3 niveles para encontrar la raíz del proyecto
# (data_pipeline -> utils -> backfill_invernada.py)
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

try:
    # 2. Importaciones absolutas
    from data_pipeline.scrapers import cac_scraper
    from shared_code.database import db_manager
except ModuleNotFoundError as e:
    print(f"Error: No se pudieron encontrar los módulos. Detalle: {e}")
    print("Asegúrate de ejecutar esto con el entorno virtual activado y desde la raíz.")
    sys.exit(1)


def ejecutar_backfill_invernada():
    """
    Ejecuta la carga histórica de Invernada (DeCampoACampo).
    Utiliza el modo 'histórico' del scraper para traer 3 años de datos mensuales.
    """
    print(f"\n--- INICIANDO BACKFILL DE INVERNADA (HISTÓRICO 3 AÑOS) ---")
    print(f"Fecha de ejecución: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    
    conn = None
    total_insertados = 0

    try:
        # 1. Conectar a la BBDD
        conn = db_manager.get_db_connection()
        if not conn:
            print("ERROR FATAL: No se pudo conectar a la base de datos.")
            return

        # Asegurar que la tabla exista
        db_manager.crear_tablas(conn)
        
        # 2. Ejecutar Scraper en Modo Histórico
        print("\n[1/2] Ejecutando Scraper de Invernada (Modo Histórico)...")
        try:
            # IMPORTANTE: Usamos la función específica para el historial
            datos_invernada = cac_scraper.scrape_invernada_historico(debug=True)
        except Exception as e:
            print(f"ERROR CRÍTICO en el scraper: {e}")
            import traceback
            traceback.print_exc()
            return

        if not datos_invernada:
            print("ADVERTENCIA: El scraper no devolvió ningún dato.")
            return

        print(f"Scraper finalizado. Se obtuvieron {len(datos_invernada)} registros históricos.")

        # 3. Insertar en BBDD
        print("\n[2/2] Insertando en Base de Datos...")
        
        # La función insertar_datos_invernada se encarga de convertir las fechas
        # e ignorar duplicados gracias a la clave única de la tabla.
        total_insertados = db_manager.insertar_datos_invernada(conn, datos_invernada)
        
        if total_insertados > 0:
            print(f"¡ÉXITO! Se insertaron {total_insertados} nuevos registros en la tabla 'invernada'.")
        else:
            print("No se insertaron registros nuevos (probablemente ya existían).")

    except Exception as e:
        print(f"Error fatal durante el backfill: {e}")
        import traceback
        traceback.print_exc()

    finally:
        if conn:
            conn.close()
            print("\nConexión a la base de datos cerrada.")

# --- Bloque de Ejecución ---
if __name__ == "__main__":
    print(f"Base de datos objetivo: {db_manager.DB_PATH}")
    print("Esto descargará ~3 años de historia para todas las categorías de Invernada.")
    
    confirmacion = input("¿Deseas continuar? (s/n): ").strip().lower()
    
    if confirmacion == 's':
        ejecutar_backfill_invernada()
    else:
        print("Operación cancelada.")