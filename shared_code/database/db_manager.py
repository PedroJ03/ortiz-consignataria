import sqlite3
import os
from datetime import datetime

# --- CONFIGURACIÓN DE RUTAS ---
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DB_PATH = os.path.join(PROJECT_ROOT, 'precios_historicos.db') 

def get_db_connection():
    """Crea y devuelve una conexión a la base de datos."""
    try:
        conn = sqlite3.connect(DB_PATH)
        # Habilitamos row_factory para acceder a columnas por nombre
        conn.row_factory = sqlite3.Row 
        return conn
    except sqlite3.Error as e:
        print(f"Error crítico conectando a BD: {e}")
        return None

def crear_tablas(conn):
    """Crea las tablas con índices optimizados."""
    try:
        cursor = conn.cursor()
        
        # Tabla FAENA
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS faena (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha_extraccion TIMESTAMP NOT NULL,
            fecha_consulta TEXT NOT NULL,  -- Se guarda como YYYY-MM-DD
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
        
        # Tabla INVERNADA
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS invernada (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha_extraccion TIMESTAMP NOT NULL,
            fecha_consulta_inicio TEXT, -- Se guarda como YYYY-MM-DD
            fecha_consulta_fin TEXT,    -- Se guarda como YYYY-MM-DD
            tipo_hacienda TEXT,
            categoria_original TEXT NOT NULL,
            precio_promedio_kg REAL,
            cabezas INTEGER,
            variacion_semanal_precio REAL,
            UNIQUE(fecha_consulta_fin, categoria_original)
        );
        """)
        
        # Índices para búsquedas rápidas por fecha
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_faena_fecha ON faena (fecha_consulta)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_invernada_fecha ON invernada (fecha_consulta_fin)")
        conn.commit()
    except sqlite3.Error as e:
        print(f"Error creando tablas: {e}")

# --- LÓGICA DE ESCRITURA (ENTRADA) ---
# Convierte DD/MM/YYYY (del Scraper) -> YYYY-MM-DD (para la BD)

def insertar_datos_faena(conn, lista_datos_faena):
    if not lista_datos_faena: return 0
    
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
    
    fecha_actual_str = datetime.now().isoformat()
    datos_para_insertar = []
    
    for item in lista_datos_faena:
        fecha_raw = item.get('fecha_consulta_inicio') # Viene como 19/11/2025
        
        # TRADUCCIÓN AL ENTRAR: DD/MM/YYYY -> YYYY-MM-DD
        try:
            fecha_iso = datetime.strptime(fecha_raw, "%d/%m/%Y").strftime("%Y-%m-%d")
        except (ValueError, TypeError):
            # Si falla, no insertamos basura
            print(f"Error de fecha en registro: {fecha_raw}")
            continue

        item_dict = {
            'fecha_extraccion': fecha_actual_str,
            'fecha_consulta': fecha_iso, # <--- GUARDAMOS ISO
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
        print(f"Error SQL insertando Faena: {e}")
        conn.rollback()
        return 0


def insertar_datos_invernada(conn, lista_datos_invernada):
    """
    Inserta registros de Invernada convirtiendo fechas de DD/MM/YYYY a YYYY-MM-DD.
    """
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
        # 1. Obtener fechas crudas (DD/MM/YYYY)
        inicio_raw = item.get('fecha_consulta_inicio')
        fin_raw = item.get('fecha_consulta_fin')
        
        # 2. Conversión a ISO (YYYY-MM-DD)
        try:
            inicio_iso = datetime.strptime(inicio_raw, "%d/%m/%Y").strftime("%Y-%m-%d") if inicio_raw else None
            fin_iso = datetime.strptime(fin_raw, "%d/%m/%Y").strftime("%Y-%m-%d") if fin_raw else None
        except (ValueError, TypeError):
            print(f"Error de fecha en registro Invernada: {inicio_raw} - {fin_raw}")
            continue # Saltamos registros con fechas rotas

        item_dict = {
            'fecha_extraccion': fecha_actual_str,
            'fecha_consulta_inicio': inicio_iso, # <--- GUARDADO COMO ISO
            'fecha_consulta_fin': fin_iso,       # <--- GUARDADO COMO ISO
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
        print(f"Error SQL insertando Invernada: {e}")
        conn.rollback()
        return 0

def get_faena_historico(conn, start_date, end_date, categoria=None, raza=None, rango_peso=None):
    """
    Devuelve los datos para el Dashboard incluyendo CABEZAS.
    """
    # Se agrega 'cabezas' al SELECT
    base_query = """
        SELECT 
            strftime('%d/%m/%Y', fecha_consulta) as fecha_consulta, 
            precio_promedio_kg,
            cabezas,  -- <--- ¡ESTO FALTABA!
            categoria_original,
            raza,
            rango_peso
        FROM faena 
        WHERE fecha_consulta BETWEEN ? AND ?
    """
    params = [start_date, end_date]

    if categoria:
        base_query += " AND categoria_original = ?"
        params.append(categoria)
    if raza:
        base_query += " AND raza = ?"
        params.append(raza)
    if rango_peso:
        base_query += " AND rango_peso = ?"
        params.append(rango_peso)
    
    base_query += " ORDER BY faena.fecha_consulta ASC"
    
    cursor = conn.cursor()
    cursor.execute(base_query, tuple(params))
    rows = [dict(row) for row in cursor.fetchall()]
    return rows

def get_invernada_historico(conn, start_date, end_date, categoria=None):
    # Se agrega 'cabezas' al SELECT
    base_query = """
        SELECT 
            strftime('%d/%m/%Y', fecha_consulta_inicio) as fecha_consulta_inicio,
            strftime('%d/%m/%Y', fecha_consulta_fin) as fecha_consulta_fin,
            categoria_original,
            precio_promedio_kg,
            variacion_semanal_precio,
            cabezas -- <--- ¡ESTO FALTABA!
        FROM invernada 
        WHERE fecha_consulta_fin BETWEEN ? AND ?
    """
    params = [start_date, end_date]

    if categoria:
        base_query += " AND categoria_original = ?"
        params.append(categoria)
    
    base_query += " ORDER BY invernada.fecha_consulta_fin ASC"
    
    cursor = conn.cursor()
    cursor.execute(base_query, tuple(params))
    rows = [dict(row) for row in cursor.fetchall()]
    return rows
