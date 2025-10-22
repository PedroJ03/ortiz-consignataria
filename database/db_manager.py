import sqlite3
import os
from datetime import datetime

# La ruta al archivo de BBDD real
DB_PATH = os.path.join(os.path.dirname(__file__), 'precios.db')

def get_db_connection():
    """
    Función de ayuda para crear una conexión a la BBDD real.
    """
    return sqlite3.connect(DB_PATH)

def crear_tabla(conn):
    """
    Crea la tabla 'precios' en la conexión de BBDD proporcionada.
    """
    try:
        cursor = conn.cursor()
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS precios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha_extraccion TIMESTAMP NOT NULL,
            fecha_consulta TEXT NOT NULL,
            fuente TEXT NOT NULL,
            tipo_hacienda TEXT,
            categoria_original TEXT NOT NULL,
            raza TEXT,
            rango_peso TEXT,
            precio_max_kg REAL,
            precio_min_kg REAL,
            precio_promedio_kg REAL,
            cabezas INTEGER,
            kilos_total INTEGER,
            importe_total REAL
        )
        """)
        
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_fecha_consulta ON precios (fecha_consulta)")
        conn.commit()
    except sqlite3.Error as e:
        print(f"Error al crear la tabla: {e}")
        raise # Relanzamos el error para que pytest lo capture

def insertar_datos(conn, lista_datos):
    """
    Recibe una lista de diccionarios y los inserta en la conexión de BBDD proporcionada.
    
    :param conn: Objeto de conexión a la BBDD.
    :param lista_datos: Lista de diccionarios con los datos a insertar.
    :return: Número de registros insertados.
    """
    if not lista_datos:
        return 0

    datos_para_insertar = []
    fecha_actual = datetime.now()
    
    for item in lista_datos:
        datos_para_insertar.append((
            fecha_actual,
            item.get('fecha_consulta', ''), # Usamos .get() para seguridad
            item.get('fuente', ''),
            item.get('tipo_hacienda', ''),
            item.get('categoria_original', ''),
            item.get('raza', ''),
            item.get('rango_peso', ''),
            item.get('precio_max_kg'),
            item.get('precio_min_kg'),
            item.get('precio_promedio_kg'),
            item.get('cabezas'),
            item.get('kilos_total'),
            item.get('importe_total')
        ))
    
    sql = """
    INSERT INTO precios (
        fecha_extraccion, fecha_consulta, fuente, tipo_hacienda, 
        categoria_original, raza, rango_peso, precio_max_kg, 
        precio_min_kg, precio_promedio_kg, cabezas, kilos_total, importe_total
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """
    
    try:
        cursor = conn.cursor()
        # Usamos '?' como placeholder
        cursor.executemany(sql, datos_para_insertar)
        conn.commit()
        print(f"Éxito: Se insertaron {len(datos_para_insertar)} registros en la base de datos.")
        return len(datos_para_insertar)
    except sqlite3.Error as e:
        print(f"Error al insertar datos: {e}")
        conn.rollback() # Revertimos cambios si hay error
        raise

# --- Bloque para probar este script individualmente (ahora usa la BBDD real) ---
if __name__ == "__main__":
    print("--- Ejecutando prueba del gestor de base de datos (esquema final) ---")
    
    # Este bloque ahora usa la conexión real
    conn_real = None
    try:
        conn_real = get_db_connection()
        crear_tabla(conn_real)
        print(f"Base de datos y tabla 'precios' (esquema final) aseguradas en: {DB_PATH}")

        # Datos de prueba
        datos_prueba = [{
            'fecha_consulta': '20/10/2025', 'fuente': 'Prueba', 'tipo_hacienda': 'FAENA',
            'categoria_original': 'NOVILLOS PRUEBA', 'raza': 'MESTIZO', 'rango_peso': '400-430',
            'precio_max_kg': 3000.0, 'precio_min_kg': 2800.0, 'precio_promedio_kg': 2900.0,
            'cabezas': 50, 'kilos_total': 21000, 'importe_total': 60900000.0
        }]
        
        insertar_datos(conn_real, datos_prueba)
        print("\n--- Prueba finalizada. ---")
        
    except sqlite3.Error as e:
        print(f"Error en la prueba: {e}")
    finally:
        if conn_real:
            conn_real.close()

