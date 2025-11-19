import sys
import os
import time
import sqlite3
from datetime import datetime

# --- SETUP ---
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

try:
    from data_pipeline.scrapers import cac_scraper
    from shared_code.database import db_manager
except ModuleNotFoundError as e:
    print(f"Error imports: {e}")
    sys.exit(1)

def limpiar_tabla_invernada(conn):
    """Borra la tabla para carga limpia."""
    cursor = conn.cursor()
    print("\n" + "="*50)
    print("!!! ADVERTENCIA CRÍTICA - INVERNADA !!!")
    print("Se borrará toda la tabla 'invernada'.")
    print("="*50)
    if input("Escribe 'BORRAR' para confirmar: ") == 'BORRAR':
        try:
            cursor.execute("DELETE FROM invernada")
            conn.commit()
            print(">> Tabla invernada vaciada.")
            return True
        except Exception as e:
            print(f"Error: {e}")
            return False
    return False

def ejecutar_backfill():
    conn = db_manager.get_db_connection()
    if not conn: return

    if not limpiar_tabla_invernada(conn):
        conn.close()
        return

    print("\n--- INICIANDO SCRAPING HISTÓRICO (3 AÑOS) ---")
    try:
        datos = cac_scraper.scrape_invernada_historico(debug=True)
        
        if datos:
            print(f"\nInsertando {len(datos)} registros...")
            count = db_manager.insertar_datos_invernada(conn, datos)
            print(f"¡ÉXITO! Insertados: {count}")
        else:
            print("El scraper no devolvió datos.")
            
    except Exception as e:
        print(f"Error fatal: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    ejecutar_backfill()