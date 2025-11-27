import sys
import os
import sqlite3

# Setup ruta
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from shared_code.database import db_manager

if __name__ == "__main__":
    email = input("Introduce el email del usuario a convertir en ADMIN: ").strip()
    
    conn = db_manager.get_conn_market()
    cursor = conn.cursor()
    
    # Verificar si existe
    cursor.execute("SELECT id, nombre_completo FROM users WHERE email = ?", (email,))
    user = cursor.fetchone()
    
    if user:
        print(f"Usuario encontrado: {user['nombre_completo']} (ID: {user['id']})")
        confirm = input("¿Confirmar permisos de administrador? (s/n): ")
        if confirm.lower() == 's':
            cursor.execute("UPDATE users SET es_admin = 1 WHERE id = ?", (user['id'],))
            conn.commit()
            print("✅ ¡Éxito! El usuario ahora es Administrador.")
    else:
        print("❌ Error: Usuario no encontrado. Regístrate primero en la web.")
    
    conn.close()