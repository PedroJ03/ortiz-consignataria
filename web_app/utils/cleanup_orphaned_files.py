#!/usr/bin/env python3
"""
Script de limpieza de archivos huérfanos.
Elimina archivos en uploads que no están asociados a ninguna publicación.

Uso:
    python cleanup_orphaned_files.py [--dry-run]

Opciones:
    --dry-run   Muestra qué se eliminaría sin borrar realmente
"""

import os
import sys
import argparse
from pathlib import Path

# Agregar el proyecto al path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from shared_code.database import db_manager


def cleanup_orphaned_files(upload_folder='/app/data/uploads/lotes', dry_run=False):
    """
    Elimina archivos huérfanos del directorio de uploads.
    
    Args:
        upload_folder: Ruta al directorio de uploads
        dry_run: Si True, solo muestra lo que se eliminaría
    
    Returns:
        tuple: (archivos_eliminados, archivos_conservados, espacio_liberado_mb)
    """
    # Usar la ruta correcta de la base de datos del marketplace
    db_path = '/app/data/marketplace.db'
    conn = db_manager.get_db_connection(db_path)
    if not conn:
        print("❌ Error: No se pudo conectar a la base de datos")
        return 0, 0, 0
    
    try:
        # Obtener todos los archivos válidos registrados en la base de datos
        cursor = conn.cursor()
        cursor.execute("SELECT filename FROM media_lotes")
        db_files = {os.path.basename(row['filename']) for row in cursor.fetchall()}
        
        # También obtener imágenes y videos de la tabla publicaciones
        cursor.execute("SELECT imagen_filename, video_filename FROM publicaciones")
        for row in cursor.fetchall():
            if row['imagen_filename']:
                db_files.add(os.path.basename(row['imagen_filename']))
            if row['video_filename']:
                db_files.add(os.path.basename(row['video_filename']))
        
        print(f"📊 Archivos registrados en BD: {len(db_files)}")
        
        # Revisar archivos en el directorio
        upload_path = Path(upload_folder)
        if not upload_path.exists():
            print(f"❌ Error: El directorio {upload_folder} no existe")
            return 0, 0, 0
        
        archivos_eliminados = 0
        archivos_conservados = 0
        espacio_liberado = 0
        
        for file_path in upload_path.iterdir():
            if file_path.is_file():
                filename = file_path.name
                
                if filename in db_files:
                    archivos_conservados += 1
                else:
                    file_size = file_path.stat().st_size
                    espacio_liberado += file_size
                    
                    if dry_run:
                        print(f"🟡 [DRY RUN] Se eliminaría: {filename} ({file_size / (1024*1024):.2f} MB)")
                    else:
                        try:
                            file_path.unlink()
                            print(f"🗑️  Eliminado: {filename} ({file_size / (1024*1024):.2f} MB)")
                            archivos_eliminados += 1
                        except Exception as e:
                            print(f"❌ Error eliminando {filename}: {e}")
        
        espacio_liberado_mb = espacio_liberado / (1024 * 1024)
        
        print(f"\n📈 Resumen:")
        print(f"   Archivos conservados: {archivos_conservados}")
        print(f"   Archivos eliminados: {archivos_eliminados}")
        print(f"   Espacio liberado: {espacio_liberado_mb:.2f} MB")
        
        if dry_run:
            print(f"\n📝 Esto fue un DRY RUN. Usa sin --dry-run para eliminar realmente.")
        
        return archivos_eliminados, archivos_conservados, espacio_liberado_mb
        
    except Exception as e:
        print(f"❌ Error durante la limpieza: {e}")
        return 0, 0, 0
    finally:
        conn.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Limpia archivos huérfanos del sistema')
    parser.add_argument('--dry-run', action='store_true', 
                        help='Muestra qué se eliminaría sin borrar realmente')
    parser.add_argument('--upload-folder', default='/app/data/uploads/lotes',
                        help='Ruta al directorio de uploads')
    
    args = parser.parse_args()
    
    print("🧹 Limpieza de archivos huérfanos\n")
    cleanup_orphaned_files(args.upload_folder, args.dry_run)