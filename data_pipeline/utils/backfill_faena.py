import sys
import os
import time
from datetime import datetime, timedelta

# --- ========================================== ---
# --- INICIO DE CORRECCIÓN DE ARQUITECTURA ---
# --- ========================================== ---

# 1. Corregir el 'sys.path'
# __file__ está en .../data_pipeline/utils/backfill_faena.py
# Necesitamos subir 3 niveles para llegar a la raíz 'ortiz-consignataria'
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

try:
    # 2. Corregir las importaciones
    from data_pipeline.scrapers import mag_scraper
    from shared_code.database import db_manager
except ModuleNotFoundError as e:
    print(f"Error: No se pudieron encontrar los módulos. Detalle: {e}")
    print("Asegúrate de que 'shared_code' y 'data_pipeline' existan en la raíz.")
    sys.exit(1)

# --- FIN DE CORRECCIÓN DE ARQUITECTURA ---


# --- Constantes de Configuración (Sin cambios) ---
START_DATE = datetime(2025, 1, 1)
END_DATE = datetime.now() 
DIAS_HABILES = [1, 2, 3, 4] # Martes a Viernes
PAUSA_ENTRE_SOLICITUDES = 1.5 

def generar_rango_fechas(start, end):
    """
    Genera una lista de strings de fechas (DD/MM/YYYY) para los días hábiles
    dentro del rango especificado.
    """
    print(f"Generando lista de días hábiles (Mar-Vie) entre {start.strftime('%d/%m/%Y')} y {end.strftime('%d/%m/%Y')}...")
    
    fechas_a_procesar = []
    current_date = start
    
    while current_date <= end:
        if current_date.weekday() in DIAS_HABILES:
            fechas_a_procesar.append(current_date.strftime("%d/%m/%Y"))
        current_date += timedelta(days=1)
        
    print(f"Se procesarán {len(fechas_a_procesar)} días.")
    return fechas_a_procesar

def ejecutar_backfill(lista_fechas):
    """
    Ejecuta el scraper e inserta en la BBDD para cada fecha en la lista.
    """
    conn = None
    total_registros_insertados = 0
    dias_procesados = 0
    dias_con_datos = 0

    try:
        # La ruta en db_manager (DB_PATH) ya es correcta (apunta a la raíz)
        conn = db_manager.get_db_connection()
        if not conn:
            print("ERROR FATAL: No se pudo conectar a la base de datos.")
            return

        db_manager.crear_tablas(conn)
        
        total_dias = len(lista_fechas)
        
        for i, fecha_str in enumerate(lista_fechas):
            print(f"\n--- Procesando día {i+1}/{total_dias}: {fecha_str} ---")
            
            try:
                # 1. Scrapear (Sigue siendo DD/MM/YYYY)
                datos_dia = mag_scraper.scrape_mag_faena(fecha_str, fecha_str, debug=False)
                
                if datos_dia:
                    print(f"Se encontraron {len(datos_dia)} registros.")
                    dias_con_datos += 1
                    
                    # 2. Insertar (db_manager ahora convierte DD/MM/YYYY a YYYY-MM-DD)
                    registros_insertados = db_manager.insertar_datos_faena(conn, datos_dia)
                    print(f"Éxito: Se insertaron {registros_insertados} nuevos registros.")
                    total_registros_insertados += registros_insertados
                else:
                    print("Sin datos encontrados para esta fecha.")
                    
                dias_procesados += 1

            except Exception as e:
                print(f"ERROR al procesar la fecha {fecha_str}: {e}")
                print("Continuando con la siguiente fecha...")

            finally:
                print(f"Pausando {PAUSA_ENTRE_SOLICITUDES} segundos...")
                time.sleep(PAUSA_ENTRE_SOLICITUDES)

    except KeyboardInterrupt:
        print("\n--- PROCESO DE BACKFILL INTERRUMPIDO POR EL USUARIO ---")
    
    except Exception as e:
        print(f"Error fatal durante el backfill: {e}")

    finally:
        if conn:
            conn.close()
            print("\nConexión a la base de datos cerrada.")

    print("\n--- BACKFILL FINALIZADO ---")
    print(f"Días totales en el rango: {len(lista_fechas)}")
    print(f"Días procesados (con/sin datos): {dias_procesados}")
    print(f"Días que devolvieron datos: {dias_con_datos}")
    print(f"Total de registros NUEVOS insertados en la BBDD: {total_registros_insertados}")

# --- Bloque de Ejecución Principal ---
if __name__ == "__main__":
    
    lista_fechas = generar_rango_fechas(START_DATE, END_DATE)
    
    print("\n--- ADVERTENCIA ---")
    print(f"Estás a punto de ejecutar un script de backfill para {len(lista_fechas)} días.")
    print(f"Esto realizará {len(lista_fechas)} solicitudes al servidor de MAG.")
    print(f"Tiempo estimado (aprox): {len(lista_fechas) * PAUSA_ENTRE_SOLICITUDES / 60:.1f} minutos.")
    
    # La ruta en db_manager (DB_PATH) ya es correcta
    print(f"Los datos se insertarán en: {db_manager.DB_PATH}") 
    
    confirmacion = input("\n¿Estás seguro de que deseas continuar? (s/n): ").strip().lower()
    
    if confirmacion == 's':
        ejecutar_backfill(lista_fechas)
    else:
        print("Operación cancelada por el usuario.")