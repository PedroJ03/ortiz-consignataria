import sqlite3
import os
from datetime import datetime

# --- ========================================== ---
# --- 1. RUTA CORREGIDA (3 NIVELES) ---
# --- ========================================== ---
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DB_PATH = os.path.join(PROJECT_ROOT, 'precios_historicos.db') 


def get_db_connection():
    """Crea y devuelve una conexión a la base de datos (el archivo real)."""
    try:
        conn = sqlite3.connect(DB_PATH, detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES)
        conn.execute("PRAGMA foreign_keys = ON;")
        conn.row_factory = sqlite3.Row 
        return conn
    except sqlite3.Error as e:
        print(f"Error al conectar a la base de datos en {DB_PATH}: {e}")
        return None

def crear_tablas(conn):
    """Crea las tablas (faena e invernada) si no existen."""
    try:
        cursor = conn.cursor()
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS faena (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha_extraccion TIMESTAMP NOT NULL,
            fecha_consulta TEXT NOT NULL,
            tipo_hacienda TEXT,
            categoria_original TEXT NOT NULL,
            raza TEXT,
            rango_peso TEXT,
            precio_max_kg REAL,
            precio_min_kg REAL,
            precio_promedio_kg REAL,
            cabezas INTEGER,
            kilos_total INTEGER,
            importe_total REAL,
            UNIQUE(fecha_consulta, categoria_original, raza, rango_peso)
        );
        """)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS invernada (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha_extraccion TIMESTAMP NOT NULL,
            fecha_consulta_inicio TEXT,
            fecha_consulta_fin TEXT,
            tipo_hacienda TEXT,
            categoria_original TEXT NOT NULL,
            precio_promedio_kg REAL,
            cabezas INTEGER,
            variacion_semanal_precio REAL,
            UNIQUE(fecha_consulta_fin, categoria_original)
        );
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_faena_fecha ON faena (fecha_consulta)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_invernada_fecha ON invernada (fecha_consulta_fin)")
        conn.commit()
    except sqlite3.Error as e:
        print(f"Error al crear las tablas: {e}")

# --- ========================================== ---
# --- 2. LÓGICA DE INSERCIÓN (DD/MM/YYYY y ISO) ---
# --- ========================================== ---
def insertar_datos_faena(conn, lista_datos_faena):
    """Inserta registros de Faena. (Guarda fecha_consulta como DD/MM/YYYY)."""
    if not lista_datos_faena:
        return 0
    sql = """
    INSERT OR IGNORE INTO faena(
        fecha_extraccion, fecha_consulta, tipo_hacienda, categoria_original, raza, 
        rango_peso, precio_max_kg, precio_min_kg, precio_promedio_kg, 
        cabezas, kilos_total, importe_total
    ) VALUES (
        :fecha_extraccion, :fecha_consulta, :tipo_hacienda, :categoria_original, :raza,
        :rango_peso, :precio_max_kg, :precio_min_kg, :precio_promedio_kg,
        :cabezas, :kilos_total, :importe_total
    );
    """
    
    # Corregido para DeprecationWarning
    fecha_actual_str = datetime.now().isoformat()
    
    datos_para_insertar = []
    for item in lista_datos_faena:
        # Guardar la fecha del scraper (DD/MM/YYYY) directamente
        fecha_consulta_dmy = item.get('fecha_consulta_inicio')
        if not fecha_consulta_dmy:
            print(f"Omitiendo registro de faena sin 'fecha_consulta_inicio'. Datos: {item}")
            continue

        item_dict = {
            'fecha_extraccion': fecha_actual_str, # (Guardado como ISO)
            'fecha_consulta': fecha_consulta_dmy, # (Guardado como DD/MM/YYYY)
            'tipo_hacienda': item.get('tipo_hacienda'),
            'categoria_original': item.get('categoria_original'),
            'raza': item.get('raza'),
            'rango_peso': item.get('rango_peso'),
            'precio_max_kg': item.get('precio_max_kg'),
            'precio_min_kg': item.get('precio_min_kg'),
            'precio_promedio_kg': item.get('precio_promedio_kg'),
            'cabezas': item.get('cabezas'),
            'kilos_total': item.get('kilos_total'),
            'importe_total': item.get('importe_total')
        }
        datos_para_insertar.append(item_dict)

    try:
        cursor = conn.cursor()
        cursor.executemany(sql, datos_para_insertar)
        conn.commit()
        return cursor.rowcount 
    except sqlite3.Error as e:
        print(f"Error al insertar datos de Faena: {e}")
        conn.rollback()
        return 0

def insertar_datos_invernada(conn, lista_datos_invernada):
    """Inserta registros de Invernada. (Guarda fechas como DD/MM/YYYY)."""
    if not lista_datos_invernada:
        return 0
    sql = """
    INSERT OR IGNORE INTO invernada (
        fecha_extraccion, fecha_consulta_inicio, fecha_consulta_fin, tipo_hacienda, 
        categoria_original, precio_promedio_kg, cabezas, variacion_semanal_precio
    ) VALUES (
        :fecha_extraccion, :fecha_consulta_inicio, :fecha_consulta_fin, :tipo_hacienda,
        :categoria_original, :precio_promedio_kg, :cabezas, :variacion_semanal_precio
    );
    """
    
    fecha_actual_str = datetime.now().isoformat()
    datos_para_insertar = []
    
    for item in lista_datos_invernada:
        item_dict = {
            'fecha_extraccion': fecha_actual_str,
            'fecha_consulta_inicio': item.get('fecha_consulta_inicio'), # (DD/MM/YYYY)
            'fecha_consulta_fin': item.get('fecha_consulta_fin'),       # (DD/MM/YYYY)
            'tipo_hacienda': item.get('tipo_hacienda'),
            'categoria_original': item.get('categoria_original'),
            'precio_promedio_kg': item.get('precio_promedio_kg'),
            'cabezas': item.get('cabezas'),
            'variacion_semanal_precio': item.get('variacion_semanal_precio')
        }
        datos_para_insertar.append(item_dict)

    try:
        cursor = conn.cursor()
        cursor.executemany(sql, datos_para_insertar)
        conn.commit()
        return cursor.rowcount
    except sqlite3.Error as e:
        print(f"Error al insertar datos de Invernada: {e}")
        conn.rollback()
        return 0

# --- ========================================== ---
# --- 3. LÓGICA DE CONSULTA CORRECTA (SUBSTR) ---
# --- ========================================== ---
def get_faena_historico(conn, start_date, end_date, categoria=None, raza=None, rango_peso=None):
    """Obtiene datos históricos de Faena. (Lee fechas DD/MM/YYYY)."""
    if not start_date or not end_date:
         raise ValueError("Formato de fecha inválido. Se esperaba YYYY-MM-DD.")

    # Re-introducida la lógica SUBSTR para leer DD/MM/YYYY
    base_query = """
        SELECT fecha_consulta, precio_promedio_kg FROM faena 
        WHERE (SUBSTR(fecha_consulta, 7, 4) || '-' || 
             SUBSTR(fecha_consulta, 4, 2) || '-' || 
             SUBSTR(fecha_consulta, 1, 2))
            BETWEEN ? AND ?
    """
    params = [start_date, end_date] # Compara con YYYY-MM-DD

    if categoria:
        base_query += " AND categoria_original = ?"
        params.append(categoria)
    if raza:
        base_query += " AND raza = ?"
        params.append(raza)
    if rango_peso:
        base_query += " AND rango_peso = ?"
        params.append(rango_peso)
    
    base_query += " ORDER BY (SUBSTR(fecha_consulta, 7, 4) || '-' || SUBSTR(fecha_consulta, 4, 2) || '-' || SUBSTR(fecha_consulta, 1, 2)) ASC"
    
    cursor = conn.cursor()
    cursor.execute(base_query, tuple(params))
    rows = [dict(row) for row in cursor.fetchall()]
    return rows

def get_invernada_historico(conn, start_date, end_date, categoria=None):
    """Obtiene datos históricos de Invernada. (Lee fechas DD/MM/YYYY)."""
    if not start_date or not end_date:
         raise ValueError("Formato de fecha inválido. Se esperaba YYYY-MM-DD.")

    # Re-introducida la lógica SUBSTR
    base_query = """
        SELECT fecha_consulta_fin, precio_promedio_kg FROM invernada 
        WHERE (SUBSTR(fecha_consulta_fin, 7, 4) || '-' || 
             SUBSTR(fecha_consulta_fin, 4, 2) || '-' || 
             SUBSTR(fecha_consulta_fin, 1, 2))
            BETWEEN ? AND ?
    """
    params = [start_date, end_date]

    if categoria:
        base_query += " AND categoria_original = ?"
        params.append(categoria)
    
    base_query += " ORDER BY (SUBSTR(fecha_consulta_fin, 7, 4) || '-' || SUBSTR(fecha_consulta_fin, 4, 2) || '-' || SUBSTR(fecha_consulta_fin, 1, 2)) ASC"
    
    cursor = conn.cursor()
    cursor.execute(base_query, tuple(params))
    rows = [dict(row) for row in cursor.fetchall()]
    return rows


# --- Bloque de prueba (Actualizado) ---
if __name__ == '__main__':
    print(f"Buscando base de datos en: {DB_PATH}")
    if not os.path.exists(DB_PATH):
        print("\n--- ERROR ---")
        print(f"No se encontró el archivo 'precios_historicos.db' en la ruta esperada: {DB_PATH}")
    else:
        print("¡Base de datos encontrada!")
        print("\nProbando get_faena_historico (con todos los filtros):")
        
        conn_test = None
        try:
            conn_test = get_db_connection()
            if conn_test:
                # El bloque de prueba ahora usa la consulta SUBSTR
                datos = get_faena_historico(
                    conn_test,
                    '2025-01-01', # YYYY-MM-DD
                    '2025-12-31', # YYYY-MM-DD
                    #'01/01/2025', # DD/MM/YYYY
                    #'31/12/2025', # DD/MM/YYYY
                    categoria='NOVILLOS', 
                    #raza='MESTIZOS', 
                    #rango_peso='391-430' 
                )
                print(f"Se encontraron {len(datos)} registros de Faena.")
                
                print("\nProbando get_invernada_historico:")
                datos_inv = get_invernada_historico(
                    conn_test,
                    '2025-01-01',
                    '2025-12-31', 
                    categoria='TERNEROS'
                )
                print(f"Se encontraron {len(datos_inv)} registros de Invernada.")
            else:
                print("No se pudo establecer la conexión de prueba.")
        except Exception as e:
            print(f"Error durante la prueba: {e}")
        finally:
            if conn_test:
                conn_test.close()