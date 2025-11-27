import sys
import os

# Setup de ruta
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from shared_code.database import db_manager

if __name__ == "__main__":
    print("--- INICIALIZANDO BASES DE DATOS ---")
    print(f"Root: {project_root}")
    
    # Esto crea 'marketplace.db' y 'precios_historicos.db' si no existen
    # y crea sus tablas correspondientes.
    try:
        db_manager.inicializar_bases_datos()
        print("✅ Bases de datos verificadas/creadas con éxito.")
        print(f"   - Precios: {db_manager.DB_PRECIOS_PATH}")
        print(f"   - Market:  {db_manager.DB_MARKET_PATH}")
    except Exception as e:
        print(f"❌ Error inicializando: {e}")