import sys
import os
import time
import sqlite3
from datetime import datetime, timedelta

# --- SETUP DE RUTAS (ARQUITECTURA MONOREPO) ---
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(current_dir))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

try:
    from data_pipeline.scrapers import mag_scraper
    from shared_code.database import db_manager
except ModuleNotFoundError as e:
    print(f"Error de importación: {e}")
    print("Verifica que estás ejecutando desde la raíz o que las rutas son correctas.")
    sys.exit(1)

# --- CONFIGURACIÓN DEL BACKFILL ---
# FECHA SOLICITADA: 1 de Enero de 2022
START_DATE = datetime(2022, 1, 1) 
END_DATE = datetime.now()

# DÍAS DE OPERACIÓN: Martes(1), Miércoles(2), Jueves(3), Viernes(4)
DIAS_HABILES = [1, 2, 3, 4] 

# Pausa para no saturar al servidor (respeto profesional)
PAUSA_ENTRE_CONSULTAS = 1.5

def limpiar_tabla_faena(conn):
    """Borra TODOS los registros de faena para re-llenarlos con el nuevo formato."""
    cursor = conn.cursor()
    print("\n" + "="*50)
    print("!!! ADVERTENCIA CRÍTICA !!!")
    print("="*50)
    print("Se va a ejecutar: DELETE FROM faena")
    print(f"Se eliminarán todos los datos actuales y se recargarán desde {START_DATE.strftime('%d/%m/%Y')}.")
    print("="*50)
    confirm = input("Escribe 'BORRAR' para confirmar la operación: ")
    
    if confirm == 'BORRAR':
        try:
            # Asegúrate que el nombre de tu tabla en BBDD sea correcto ('precios_faena' o 'faena_mag')
            # Si dudas, revisa db_manager.py. Por defecto suele ser 'precios_faena'.
            cursor.execute("DELETE FROM faena") 
            conn.commit()
            print(">> Tabla limpiada correctamente. Base de datos lista para recibir historial nuevo.")
            return True
        except sqlite3.Error as e:
            print(f">> Error al limpiar tabla: {e}")
            return False
    else:
        print(">> Confirmación fallida. Operación cancelada.")
        return False

def ejecutar_backfill():
    # 1. Conexión a BBDD
    conn = db_manager.get_db_connection()
    if not conn:
        print("No hay conexión a base de datos.")
        return

    # 2. Limpieza Inicial
    if not limpiar_tabla_faena(conn):
        conn.close()
        return

    # 3. Generación de Lista de Fechas
    print(f"\nGenerando calendario de días hábiles (Mar-Vie) desde 2022...")
    current_date = START_DATE
    lista_fechas = []
    
    while current_date <= END_DATE:
        if current_date.weekday() in DIAS_HABILES:
            lista_fechas.append(current_date.strftime("%d/%m/%Y"))
        current_date += timedelta(days=1)

    total_dias = len(lista_fechas)
    tiempo_estimado_min = (total_dias * PAUSA_ENTRE_CONSULTAS) / 60
    
    print(f"Se procesarán {total_dias} fechas.")
    print(f"Tiempo estimado de ejecución: ~{tiempo_estimado_min:.1f} minutos.")
    print("Presiona Ctrl+C en cualquier momento para pausar/cancelar.")
    time.sleep(2) # Pequeña pausa para leer

    # 4. Proceso de Extracción
    total_registros_insertados = 0
    dias_con_datos = 0
    errores_consecutivos = 0
    
    try:
        for i, fecha_str in enumerate(lista_fechas):
            print(f"[{i+1}/{total_dias}] Consultando {fecha_str}...", end=" ", flush=True)
            
            try:
                # Llamada al Scraper Robusto
                datos = mag_scraper.scrape_mag_faena(fecha_str, fecha_str)
                
                if datos:
                    count = db_manager.insertar_datos_faena(conn, datos)
                    print(f"OK -> {count} registros guardados.")
                    total_registros_insertados += count
                    dias_con_datos += 1
                    errores_consecutivos = 0 # Reset contador de errores
                else:
                    # Es normal que algunos días no haya operaciones, pero imprimimos 'Vacío' para saber
                    print("Sin operaciones.")
                    errores_consecutivos = 0
                
            except Exception as e:
                print(f"ERROR: {e}")
                errores_consecutivos += 1
                # Si falla 10 veces seguidas, quizás nos banearon o cayó el sitio
                if errores_consecutivos >= 10:
                    print("\n!!! DEMASIADOS ERRORES CONSECUTIVOS. DETENIENDO SCRIPT POR SEGURIDAD.")
                    break

            # Respeto al servidor
            time.sleep(PAUSA_ENTRE_CONSULTAS)

    except KeyboardInterrupt:
        print("\n\n>> Proceso interrumpido manualmente por el usuario.")
    
    finally:
        conn.close()
        print("\n" + "="*50)
        print("RESUMEN FINAL DEL BACKFILL")
        print("="*50)
        print(f"Días consultados: {total_dias}")
        print(f"Días con actividad: {dias_con_datos}")
        print(f"Total registros insertados: {total_registros_insertados}")
        print("="*50)

if __name__ == "__main__":
    ejecutar_backfill()