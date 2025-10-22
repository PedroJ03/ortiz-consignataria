import sys
import sqlite3
import requests  # Importa requests para capturar su excepción específica
from datetime import datetime
from scrapers import mag_scraper
from database import db_manager

def ejecutar_proceso_completo(fecha_consulta_str, tipo_hacienda='TODOS', debug=False):
    """
    Orquesta el proceso completo:
    1. Asegura que la BBDD y la tabla existan.
    2. Ejecuta el scraper del MAG.
    3. Inserta los datos en la BBDD.
    """
    print(f"--- INICIANDO PROCESO COMPLETO PARA FECHA: {fecha_consulta_str} ---")

    conn = None  # Inicializa conn fuera del try para que exista en el finally
    registros_insertados_total = 0
    registros_extraidos_total = 0

    try:
        # --- Práctica Profesional: Manejo de Conexión ---
        # Obtenemos la conexión a la BBDD una sola vez al inicio.
        conn = db_manager.get_db_connection()
        print("Conexión a la base de datos establecida.")

        # 1. Asegurar la estructura de la BBDD
        print("Asegurando estructura de la base de datos...")
        # Pasamos la conexión activa a la función
        db_manager.crear_tabla(conn)

        # 2. Ejecutar Scrapers
        print("\n[FASE 1: SCRAPING MAG]")
        datos_mag = mag_scraper.scrape_mag(fecha_consulta_str, tipo_hacienda, debug=debug)
        registros_extraidos_total = len(datos_mag)
        # Aseguramos que el print refleje el resultado real
        print(f"Scraper MAG finalizado. Se encontraron {registros_extraidos_total} registros.")


        # 3. Almacenar Datos
        print("\n[FASE 2: ALMACENAMIENTO]")
        if datos_mag:
            # Pasamos la conexión activa a la función
            registros_insertados_total = db_manager.insertar_datos(conn, datos_mag)
        else:
            print("No se encontraron datos para insertar.")

        print("\n--- PROCESO COMPLETO FINALIZADO ---")
        print(f"Registros extraídos: {registros_extraidos_total}")
        print(f"Registros insertados: {registros_insertados_total}")

    except sqlite3.Error as e:
        # Error específico de la BBDD
        print(f"\n--- ERROR CRÍTICO (Base de Datos) ---")
        print(f"Error de SQLite: {e}")
        print("PROCESO FINALIZADO (CON ERRORES)")

    except requests.RequestException as e:
        # Error específico de Red (definido en el scraper)
        print(f"\n--- ERROR CRÍTICO (Scraper/Red) ---")
        print(f"Error de Red: {e}")
        print("PROCESO FINALIZADO (CON ERRORES)")

    except Exception as e:
        # Captura cualquier otro error inesperado
        print(f"\n--- ERROR CRÍTICO (Inesperado) ---")
        print(f"Error: {e}")
        # Práctica Profesional: Imprimir el traceback completo para depuración
        import traceback
        traceback.print_exc()
        print("PROCESO FINALIZADO (CON ERRORES)")

    finally:
        # --- Práctica Profesional: Cerrar Conexión ---
        # Nos aseguramos de cerrar la conexión a la BBDD pase lo que pase.
        if conn:
            conn.close()
            print("Conexión a la base de datos cerrada.")

# --- Bloque de Ejecución Principal ---
if __name__ == "__main__":
    """
    Este es el punto de entrada principal.
    Ejecuta el scraper para el día ACTUAL.
    """

    # Comprobar si se pasó 'debug' como argumento
    # python main.py debug
    run_debug = len(sys.argv) > 1 and sys.argv[1].lower() == 'debug'

    hoy = datetime.now()
    # Práctica Profesional: Usar el formato YYYY-MM-DD es más estándar para BBDD, pero mantenemos DD/MM/YYYY por coherencia con el scraper
    fecha_consulta_str = hoy.strftime("%d/%m/%Y")

    print(f"Iniciando ejecución para la fecha actual: {fecha_consulta_str} ({hoy.strftime('%A')})")

    ejecutar_proceso_completo(fecha_consulta_str, debug=run_debug)

    # --- Para pruebas manuales, puedes comentar lo de arriba y descomentar esto ---
    # print("\n--- EJECUTANDO PRUEBA MANUAL PARA EL 17/10/2025 ---")
    # ejecutar_proceso_completo("17/10/2025", tipo_hacienda='TODOS', debug=True)

