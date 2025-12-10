import psycopg2

# Configuración de Render (misma que en app.py)
DB_CONFIG = {
    'host': 'dpg-d4qoq70gjchc73bg6qug-a.virginia-postgres.render.com',
    'database': 'sistema_3szc',
    'user': 'yova',
    'password': 'wtL5fI3nEyhrYPqmP4TKVqS2h0IVT6qP'
}

def crear_usuario_admin():
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        # Verificar si ya existe
        cursor.execute("SELECT * FROM Usuarios_Sistema WHERE username = 'admin'")
        if cursor.fetchone():
            print("✅ El usuario admin ya existe")
            return
        
        # Crear usuario admin
        cursor.execute('''
            INSERT INTO Usuarios_Sistema (username, password_hash, rol, activo) 
            VALUES (%s, %s, %s, %s)
        ''', ('admin', 'admin123', 'admin', True))
        
        # Crear otros usuarios de ejemplo
        usuarios = [
            ('responsable', 'responsable123', 'responsable', True),
            ('consulta', 'consulta123', 'consulta', True),
            ('empleado1', 'empleado123', 'consulta', True)
        ]
        
        for user in usuarios:
            cursor.execute('''
                INSERT INTO Usuarios_Sistema (username, password_hash, rol, activo) 
                VALUES (%s, %s, %s, %s)
            ''', user)
        
        conn.commit()
        print("✅ Usuarios creados exitosamente:")
        print("   - admin / admin123")
        print("   - responsable / responsable123")
        print("   - consulta / consulta123")
        print("   - empleado1 / empleado123")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == '__main__':
    crear_usuario_admin()
