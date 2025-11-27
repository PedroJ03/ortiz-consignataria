import sqlite3
import os
import sys # <--- Agregar sys
from datetime import datetime

# --- LOGGING SETUP ---
# Asegurar que encuentra el logger_config subiendo niveles si es necesario
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(current_dir))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from shared_code.logger_config import setup_logger
logger = setup_logger('DB_Manager')

# --- CONFIGURACIÓN DE RUTAS ---
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# --- RUTAS DE BASES DE DATOS ---
# DB 1: Precios Históricos (Scrapers + Dashboard)
DB_PRECIOS_PATH = os.path.join(PROJECT_ROOT, 'precios_historicos.db')

# DB 2: Marketplace (Usuarios + Publicaciones) - ¡NUEVA!
DB_MARKET_PATH = os.path.join(PROJECT_ROOT, 'marketplace.db')

def get_db_connection(db_path=DB_PRECIOS_PATH):
    """
    Crea una conexión a la base de datos especificada.
    Por defecto conecta a precios_historicos (para compatibilidad).
    """
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        
        # ACTIVAR WAL (Write-Ahead Logging)
        # Esto permite que haya 1 escritor y múltiples lectores simultáneos.
        # Es vital para SQLite en producción.
        conn.execute("PRAGMA journal_mode=WAL;")
        
        return conn
    except sqlite3.Error as e:
        logger.critical(f"Error crítico conectando a BD en {db_path}: {e}")
        return None

# Helpers específicos para claridad en el código
def get_conn_precios():
    return get_db_connection(DB_PRECIOS_PATH)

def get_conn_market():
    return get_db_connection(DB_MARKET_PATH)
    
# --- CREACIÓN DE TABLAS (SEPARADA) ---

def crear_tablas_precios(conn):
    """Crea tablas de Faena e Invernada en la DB de Precios."""
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
        logger.error(f"Error creando tablas de precios: {e}")

def crear_tablas_market(conn):
    """Crea tablas de Usuarios y Publicaciones en la DB de Marketplace."""
    try:
        cursor = conn.cursor()
        
        # 1. Usuarios
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            nombre_completo TEXT NOT NULL,
            telefono TEXT,
            ubicacion TEXT,
            fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            es_admin BOOLEAN DEFAULT 0
        );
        """)

        # 2. Publicaciones (Lotes)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS publicaciones (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            titulo TEXT NOT NULL,
            categoria TEXT NOT NULL,
            raza TEXT,
            cantidad INTEGER NOT NULL,
            peso_promedio INTEGER,
            precio_pretendido REAL,
            descripcion TEXT,
            ubicacion_hacienda TEXT,
            imagen_principal TEXT,
            fecha_publicacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            activo BOOLEAN DEFAULT 1,
            FOREIGN KEY (user_id) REFERENCES users (id)
        );
        """)
        
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_publi_fecha ON publicaciones (fecha_publicacion)")
        conn.commit()
    except sqlite3.Error as e:
        logger.error(f"Error creando tablas de marketplace: {e}")

def inicializar_bases_datos():
    """Función maestra para inicializar ambas bases si no existen."""
    # 1. Precios
    conn_precios = get_conn_precios()
    if conn_precios:
        crear_tablas_precios(conn_precios)
        conn_precios.close()
        
    # 2. Marketplace
    conn_market = get_conn_market()
    if conn_market:
        crear_tablas_market(conn_market)
        conn_market.close()


# --- LÓGICA DE ESCRITURA (ENTRADA) ---
# Convierte DD/MM/YYYY (del Scraper) -> YYYY-MM-DD (para la BD)

def insertar_datos_faena(conn, lista_datos_faena):
    if not lista_datos_faena: return 0
    
    sql = """
    INSERT OR REPLACE INTO faena(
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
    INSERT OR REPLACE INTO invernada (
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


# --- MÉTODOS DE MARKETPLACE (Nuevos) ---

def get_usuario_por_email(conn, email):
    """Busca usuario en DB Marketplace."""
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
        row = cursor.fetchone()
        return dict(row) if row else None
    except sqlite3.Error as e:
        logger.error(f"Error buscando usuario: {e}")
        return None

def crear_usuario(conn, email, password_hash, nombre, telefono, ubicacion):
    """Crea usuario en DB Marketplace."""
    sql = """
    INSERT INTO users (email, password_hash, nombre_completo, telefono, ubicacion)
    VALUES (?, ?, ?, ?, ?)
    """
    try:
        cursor = conn.cursor()
        cursor.execute(sql, (email, password_hash, nombre, telefono, ubicacion))
        conn.commit()
        return cursor.lastrowid
    except sqlite3.IntegrityError:
        return None # Email duplicado
    except sqlite3.Error as e:
        logger.error(f"Error creando usuario: {e}")
        return None

# --- GESTIÓN DE PUBLICACIONES (MARKETPLACE) ---

def crear_publicacion(conn, user_id, titulo, categoria, raza, cantidad, peso, precio, descripcion, ubicacion, imagen):
    """Crea una nueva publicación de venta."""
    sql = """
    INSERT INTO publicaciones (
        user_id, titulo, categoria, raza, cantidad, peso_promedio, 
        precio_pretendido, descripcion, ubicacion_hacienda, imagen_principal
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """
    try:
        cursor = conn.cursor()
        cursor.execute(sql, (
            user_id, titulo, categoria, raza, cantidad, peso, 
            precio, descripcion, ubicacion, imagen
        ))
        conn.commit()
        return cursor.lastrowid
    except sqlite3.Error as e:
        logger.error(f"Error creando publicación: {e}")
        return None
    
# --- LECTURA DE MARKETPLACE ---

def obtener_publicaciones(conn, activo=True):
    """
    Recupera todas las publicaciones con los datos del vendedor.
    Hace un JOIN con la tabla users para saber quién vende.
    """
    sql = """
    SELECT 
        p.*, 
        u.nombre_completo as vendedor, 
        u.telefono as contacto_vendedor,
        u.ubicacion as ubicacion_vendedor
    FROM publicaciones p
    JOIN users u ON p.user_id = u.id
    WHERE p.activo = ?
    ORDER BY p.fecha_publicacion DESC
    """
    try:
        cursor = conn.cursor()
        cursor.execute(sql, (1 if activo else 0,))
        rows = [dict(row) for row in cursor.fetchall()]
        return rows
    except sqlite3.Error as e:
        print(f"Error leyendo publicaciones: {e}")
        return []
    
def obtener_ultima_publicacion(conn):
    """Recupera la publicación activa más reciente para mostrar en Inicio."""
    sql = """
    SELECT p.*, u.nombre_completo as vendedor
    FROM publicaciones p
    JOIN users u ON p.user_id = u.id
    WHERE p.activo = 1
    ORDER BY p.fecha_publicacion DESC
    LIMIT 1
    """
    try:
        cursor = conn.cursor()
        cursor.execute(sql)
        row = cursor.fetchone()
        return dict(row) if row else None
    except sqlite3.Error as e:
        print(f"Error obteniendo última publicación: {e}")
        return None
    
# --- FUNCIONES DE ADMINISTRADOR ---

def get_all_users(conn):
    """Admin: Obtener lista completa de usuarios."""
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT id, nombre_completo, email, telefono, ubicacion, fecha_registro, es_admin FROM users ORDER BY fecha_registro DESC")
        return [dict(row) for row in cursor.fetchall()]
    except sqlite3.Error as e:
        logger.error(f"Admin User Error: {e}")
        return []

def get_all_publicaciones_admin(conn):
    """Admin: Obtener TODAS las publicaciones (activas e inactivas)."""
    sql = """
    SELECT p.*, u.nombre_completo as vendedor 
    FROM publicaciones p 
    JOIN users u ON p.user_id = u.id 
    ORDER BY p.fecha_publicacion DESC
    """
    try:
        cursor = conn.cursor()
        cursor.execute(sql)
        return [dict(row) for row in cursor.fetchall()]
    except sqlite3.Error as e:
        logger.error(f"Admin Publi Error: {e}")
        return []

def eliminar_publicacion(conn, publi_id):
    """Admin: Borrado físico de una publicación (o soft delete si prefieres update activo=0)."""
    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM publicaciones WHERE id = ?", (publi_id,))
        conn.commit()
        return cursor.rowcount > 0
    except sqlite3.Error as e:
        logger.error(f"Error eliminando publicación {publi_id}: {e}")
        return False

def toggle_admin_status(conn, user_id, status):
    """Promover o degradar administrador."""
    try:
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET es_admin = ? WHERE id = ?", (1 if status else 0, user_id))
        conn.commit()
        return True
    except sqlite3.Error:
        return False

# --- EN SHARED_CODE/DATABASE/DB_MANAGER.PY ---

def toggle_publicacion_activa(conn, publi_id):
    """Cambia el estado de una publicación (De Activa a Pausada y viceversa)."""
    try:
        cursor = conn.cursor()
        # Primero vemos el estado actual
        cursor.execute("SELECT activo FROM publicaciones WHERE id = ?", (publi_id,))
        row = cursor.fetchone()
        if not row: return False
        
        nuevo_estado = 0 if row['activo'] else 1
        
        cursor.execute("UPDATE publicaciones SET activo = ? WHERE id = ?", (nuevo_estado, publi_id))
        conn.commit()
        return True
    except sqlite3.Error as e:
        logger.error(f"Error toggle publicacion {publi_id}: {e}")
        return False

def toggle_user_admin(conn, user_id):
    """Da o quita permisos de Admin a un usuario."""
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT es_admin FROM users WHERE id = ?", (user_id,))
        row = cursor.fetchone()
        if not row: return False
        
        nuevo_estado = 0 if row['es_admin'] else 1
        
        cursor.execute("UPDATE users SET es_admin = ? WHERE id = ?", (nuevo_estado, user_id))
        conn.commit()
        return True
    except sqlite3.Error as e:
        logger.error(f"Error toggle admin user {user_id}: {e}")
        return False