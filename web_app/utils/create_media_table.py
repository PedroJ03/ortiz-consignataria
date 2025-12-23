import sys
import os
import sqlite3

project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from shared_code.database import db_manager

def crear_tabla_media():
    conn = db_manager.get_conn_market()
    cursor = conn.cursor()
    
    try:
        # 1. Crear tabla para guardar muchos archivos
        print("Creando tabla 'media_lotes'...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS media_lotes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                publicacion_id INTEGER,
                filename TEXT NOT NULL,
                tipo TEXT NOT NULL, -- 'imagen' o 'video'
                FOREIGN KEY (publicacion_id) REFERENCES publicaciones (id)
            )
        """)
        
        # 2. Migrar datos viejos (Opcional, para no perder lo que ya subiste)
        print("Migrando datos existentes...")
        cursor.execute("SELECT id, imagen_filename, video_filename FROM publicaciones")
        lotes = cursor.fetchall()
        
        for lote in lotes:
            pid, img, vid = lote
            if img:
                cursor.execute("INSERT INTO media_lotes (publicacion_id, filename, tipo) VALUES (?, ?, 'imagen')", (pid, img))
            if vid:
                cursor.execute("INSERT INTO media_lotes (publicacion_id, filename, tipo) VALUES (?, ?, 'video')", (pid, vid))
        
        conn.commit()
        print("✅ Sistema de Galería Multimedia configurado.")
        
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    crear_tabla_media()