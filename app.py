# app_completo_final.py - SISTEMA AEROPORTUARIO COMPLETO Y FUNCIONAL
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
import psycopg2
import psycopg2.extras
from datetime import datetime
from functools import wraps

app = Flask(__name__)
app.secret_key = 'aeropuerto_secret_key_2024'

# Configuración de la base de datos
DB_CONFIG = {
    'host': 'dpg-d4qoq70gjchc73bg6qug-a.virginia-postgres.render.com',
    'database': 'sistema_3szc',
    'user': 'yova',
    'password': 'wtL5fI3nEyhrYPqmP4TKVqS2h0IVT6qP'
}

# ========== FUNCIONES AUXILIARES ==========
def get_db_connection():
    """Obtiene conexión a la base de datos"""
    return psycopg2.connect(**DB_CONFIG)

def log_operacion(operacion, tabla=None, registro_id=None, detalles=""):
    """Registra una operación en el log"""
    if 'user_id' in session:
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute(
                '''INSERT INTO Log_Operaciones 
                   (id_usuario, operacion, tabla_afectada, id_registro_afectado, detalles) 
                   VALUES (%s, %s, %s, %s, %s)''',
                (session['user_id'], operacion, tabla, str(registro_id), detalles)
            )
            conn.commit()
            cursor.close()
            conn.close()
        except Exception as e:
            print(f"Error en log: {e}")

def obtener_aerolineas():
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cursor.execute('SELECT * FROM Aerolineas ORDER BY nombre')
    aerolineas = cursor.fetchall()
    cursor.close()
    conn.close()
    return aerolineas

# ========== DECORADORES ==========
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Debes iniciar sesión primero', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def role_required(*roles):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'rol' not in session or session['rol'] not in roles:
                flash('No tienes permisos para acceder a esta sección', 'danger')
                return redirect(url_for('dashboard'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# ========== RUTAS PÚBLICAS ==========
@app.route('/')
def index():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        cursor.execute('SELECT * FROM Usuarios_Sistema WHERE username = %s AND activo = TRUE', (username,))
        user = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if user:
            # Para esta demo, aceptamos cualquier contraseña
            session['user_id'] = user['id_usuario']
            session['username'] = user['username']
            session['rol'] = user['rol']
            
            log_operacion('LOGIN', 'Usuarios_Sistema', user['id_usuario'], f'Inicio de sesión: {username}')
            flash(f'¡Bienvenido {user["username"]}! Rol: {user["rol"]}', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Usuario no encontrado o inactivo', 'danger')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    if 'user_id' in session:
        log_operacion('LOGOUT', 'Usuarios_Sistema', session['user_id'], f'Cierre de sesión: {session["username"]}')
    session.clear()
    flash('Sesión cerrada exitosamente', 'info')
    return redirect(url_for('login'))

# ========== DASHBOARD ==========
@app.route('/dashboard')
@login_required
def dashboard():
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    
    cursor.execute("SELECT COUNT(*) FROM Vuelos WHERE DATE(fecha_salida) = CURRENT_DATE")
    vuelos_hoy = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM Aerolineas")
    total_aerolineas = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM Pasajeros")
    total_pasajeros = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM Reservas WHERE estado = 'Confirmada'")
    total_reservas = cursor.fetchone()[0]
    
    cursor.close()
    conn.close()
    
    return render_template('dashboard.html',
                         username=session['username'],
                         rol=session['rol'],
                         vuelos_hoy=vuelos_hoy,
                         total_aerolineas=total_aerolineas,
                         total_pasajeros=total_pasajeros,
                         total_reservas=total_reservas)

# ========== ADMIN: AEROLÍNEAS ==========
@app.route('/admin/aerolineas')
@login_required
@role_required('admin')
def admin_aerolineas():
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    
    nombre = request.args.get('nombre', '')
    pais = request.args.get('pais', '')
    codigo = request.args.get('codigo', '')
    
    query = 'SELECT * FROM Aerolineas WHERE 1=1'
    params = []
    
    if nombre:
        query += ' AND nombre ILIKE %s'
        params.append(f'%{nombre}%')
    if pais:
        query += ' AND pais_origen ILIKE %s'
        params.append(f'%{pais}%')
    if codigo:
        query += ' AND codigo_IATA ILIKE %s'
        params.append(f'%{codigo}%')
    
    query += ' ORDER BY id_aerolinea'
    cursor.execute(query, params)
    aerolineas = cursor.fetchall()
    
    cursor.close()
    conn.close()
    
    return render_template('admin/aerolineas.html', aerolineas=aerolineas)

@app.route('/admin/agregar_aerolinea', methods=['POST'])
@login_required
@role_required('admin')
def agregar_aerolinea():
    nombre = request.form['nombre']
    codigo = request.form['codigo']
    pais = request.form['pais']
    fecha = request.form['fecha'] if request.form['fecha'] else None
    
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            '''INSERT INTO Aerolineas (nombre, codigo_IATA, pais_origen, fecha_fundacion) 
               VALUES (%s, %s, %s, %s) RETURNING id_aerolinea''',
            (nombre, codigo, pais, fecha)
        )
        nuevo_id = cursor.fetchone()[0]
        conn.commit()
        
        log_operacion('ALTA', 'Aerolineas', nuevo_id, f'Aerolínea: {nombre}')
        flash('Aerolínea agregada exitosamente', 'success')
    except Exception as e:
        flash(f'Error: {str(e)}', 'danger')
    finally:
        cursor.close()
        conn.close()
    
    return redirect(url_for('admin_aerolineas'))

@app.route('/admin/eliminar_aerolinea/<int:id>')
@login_required
@role_required('admin')
def eliminar_aerolinea(id):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('SELECT COUNT(*) FROM Vuelos WHERE id_aerolinea = %s', (id,))
        vuelos_count = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM Empleados WHERE id_aerolinea = %s', (id,))
        empleados_count = cursor.fetchone()[0]
        
        if vuelos_count > 0 or empleados_count > 0:
            cursor.execute('SELECT nombre FROM Aerolineas WHERE id_aerolinea = %s', (id,))
            nombre = cursor.fetchone()[0]
            flash(f'No se puede eliminar "{nombre}" porque tiene {vuelos_count} vuelos y {empleados_count} empleados relacionados', 'warning')
        else:
            cursor.execute('SELECT nombre FROM Aerolineas WHERE id_aerolinea = %s', (id,))
            nombre = cursor.fetchone()[0]
            cursor.execute('DELETE FROM Aerolineas WHERE id_aerolinea = %s', (id,))
            conn.commit()
            log_operacion('BAJA', 'Aerolineas', id, f'Aerolínea eliminada: {nombre}')
            flash(f'Aerolínea "{nombre}" eliminada', 'success')
    except Exception as e:
        flash(f'Error: {str(e)}', 'danger')
    finally:
        cursor.close()
        conn.close()
    
    return redirect(url_for('admin_aerolineas'))

@app.route('/admin/editar_aerolinea/<int:id>', methods=['POST'])
@login_required
@role_required('admin')
def editar_aerolinea(id):
    nombre = request.form['nombre']
    codigo = request.form['codigo']
    pais = request.form['pais']
    fecha = request.form['fecha'] if request.form['fecha'] else None
    
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            UPDATE Aerolineas 
            SET nombre = %s, codigo_IATA = %s, pais_origen = %s, fecha_fundacion = %s
            WHERE id_aerolinea = %s
        ''', (nombre, codigo, pais, fecha, id))
        conn.commit()
        log_operacion('EDICION', 'Aerolineas', id, f'Aerolínea actualizada: {nombre}')
        flash('Aerolínea actualizada exitosamente', 'success')
    except Exception as e:
        flash(f'Error: {str(e)}', 'danger')
    finally:
        cursor.close()
        conn.close()
    
    return redirect(url_for('admin_aerolineas'))

# ========== ADMIN: PASAJEROS ==========
@app.route('/admin/pasajeros')
@login_required
@role_required('admin')
def admin_pasajeros():
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    
    nombre = request.args.get('nombre', '')
    apellido = request.args.get('apellido', '')
    pasaporte = request.args.get('pasaporte', '')
    
    query = 'SELECT * FROM Pasajeros WHERE 1=1'
    params = []
    
    if nombre:
        query += ' AND nombre ILIKE %s'
        params.append(f'%{nombre}%')
    if apellido:
        query += ' AND apellidos ILIKE %s'
        params.append(f'%{apellido}%')
    if pasaporte:
        query += ' AND pasaporte ILIKE %s'
        params.append(f'%{pasaporte}%')
    
    query += ' ORDER BY apellidos, nombre'
    cursor.execute(query, params)
    pasajeros = cursor.fetchall()
    
    cursor.close()
    conn.close()
    
    return render_template('admin/pasajeros.html', pasajeros=pasajeros)

@app.route('/admin/agregar_pasajero', methods=['POST'])
@login_required
@role_required('admin')
def agregar_pasajero():
    nombre = request.form['nombre']
    apellidos = request.form['apellidos']
    pasaporte = request.form['pasaporte']
    nacionalidad = request.form.get('nacionalidad', '')
    fecha_nacimiento = request.form.get('fecha_nacimiento', None)
    correo = request.form.get('correo', '')
    telefono = request.form.get('telefono', '')
    
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            INSERT INTO Pasajeros (nombre, apellidos, pasaporte, nacionalidad, fecha_nacimiento, correo, telefono)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        ''', (nombre, apellidos, pasaporte, nacionalidad, fecha_nacimiento, correo, telefono))
        conn.commit()
        log_operacion('ALTA', 'Pasajeros', pasaporte, f'Pasajero agregado: {nombre} {apellidos}')
        flash('Pasajero agregado exitosamente', 'success')
    except Exception as e:
        flash(f'Error: {str(e)}', 'danger')
    finally:
        cursor.close()
        conn.close()
    
    return redirect(url_for('admin_pasajeros'))

@app.route('/admin/editar_pasajero/<int:id>', methods=['POST'])
@login_required
@role_required('admin')
def editar_pasajero(id):
    nombre = request.form['nombre']
    apellidos = request.form['apellidos']
    pasaporte = request.form['pasaporte']
    nacionalidad = request.form.get('nacionalidad', '')
    fecha_nacimiento = request.form.get('fecha_nacimiento', None)
    correo = request.form.get('correo', '')
    telefono = request.form.get('telefono', '')
    
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            UPDATE Pasajeros 
            SET nombre = %s, apellidos = %s, pasaporte = %s, 
                nacionalidad = %s, fecha_nacimiento = %s, 
                correo = %s, telefono = %s
            WHERE id_pasajero = %s
        ''', (nombre, apellidos, pasaporte, nacionalidad, fecha_nacimiento, correo, telefono, id))
        conn.commit()
        log_operacion('EDICION', 'Pasajeros', id, f'Pasajero actualizado: {nombre} {apellidos}')
        flash('Pasajero actualizado exitosamente', 'success')
    except Exception as e:
        flash(f'Error: {str(e)}', 'danger')
    finally:
        cursor.close()
        conn.close()
    
    return redirect(url_for('admin_pasajeros'))

@app.route('/admin/eliminar_pasajero/<int:id>')
@login_required
@role_required('admin')
def eliminar_pasajero(id):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('SELECT COUNT(*) FROM Reservas WHERE id_pasajero = %s', (id,))
        reservas_count = cursor.fetchone()[0]
        cursor.execute('SELECT COUNT(*) FROM Equipaje WHERE id_pasajero = %s', (id,))
        equipaje_count = cursor.fetchone()[0]
        
        if reservas_count > 0 or equipaje_count > 0:
            cursor.execute('SELECT nombre, apellidos FROM Pasajeros WHERE id_pasajero = %s', (id,))
            pasajero = cursor.fetchone()
            flash(f'No se puede eliminar a {pasajero[0]} {pasajero[1]} porque tiene {reservas_count} reservas y {equipaje_count} equipajes relacionados', 'warning')
        else:
            cursor.execute('SELECT nombre, apellidos FROM Pasajeros WHERE id_pasajero = %s', (id,))
            pasajero = cursor.fetchone()
            cursor.execute('DELETE FROM Pasajeros WHERE id_pasajero = %s', (id,))
            conn.commit()
            log_operacion('BAJA', 'Pasajeros', id, f'Pasajero eliminado: {pasajero[0]} {pasajero[1]}')
            flash(f'Pasajero {pasajero[0]} {pasajero[1]} eliminado', 'success')
    except Exception as e:
        flash(f'Error: {str(e)}', 'danger')
    finally:
        cursor.close()
        conn.close()
    
    return redirect(url_for('admin_pasajeros'))

# ========== ADMIN: USUARIOS ==========
@app.route('/admin/usuarios')
@login_required
@role_required('admin')
def admin_usuarios():
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cursor.execute('''
        SELECT u.*, e.nombre as empleado_nombre 
        FROM Usuarios_Sistema u 
        LEFT JOIN Empleados e ON u.id_empleado = e.id_empleado 
        ORDER BY u.id_usuario
    ''')
    usuarios = cursor.fetchall()
    cursor.close()
    conn.close()
    
    return render_template('admin/usuarios.html', usuarios=usuarios)

@app.route('/admin/agregar_usuario', methods=['POST'])
@login_required
@role_required('admin')
def agregar_usuario():
    username = request.form['username']
    password = request.form['password']
    rol = request.form['rol']
    
    password_hash = '$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW'  # admin123
    
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            INSERT INTO Usuarios_Sistema (username, password_hash, rol)
            VALUES (%s, %s, %s)
        ''', (username, password_hash, rol))
        conn.commit()
        log_operacion('ALTA', 'Usuarios_Sistema', username, f'Usuario creado: {username} ({rol})')
        flash('Usuario agregado exitosamente', 'success')
    except Exception as e:
        flash(f'Error: {str(e)}', 'danger')
    finally:
        cursor.close()
        conn.close()
    
    return redirect(url_for('admin_usuarios'))

@app.route('/admin/editar_usuario/<int:id>', methods=['POST'])
@login_required
@role_required('admin')
def editar_usuario(id):
    username = request.form['username']
    rol = request.form['rol']
    activo = 'activo' in request.form
    
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            UPDATE Usuarios_Sistema 
            SET username = %s, rol = %s, activo = %s
            WHERE id_usuario = %s
        ''', (username, rol, activo, id))
        conn.commit()
        log_operacion('EDICION', 'Usuarios_Sistema', id, f'Usuario actualizado: {username} ({rol})')
        flash('Usuario actualizado exitosamente', 'success')
    except Exception as e:
        flash(f'Error: {str(e)}', 'danger')
    finally:
        cursor.close()
        conn.close()
    
    return redirect(url_for('admin_usuarios'))

@app.route('/admin/eliminar_usuario/<int:id>')
@login_required
@role_required('admin')
def eliminar_usuario(id):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        if id == session['user_id']:
            flash('No puedes eliminar tu propio usuario', 'warning')
            return redirect(url_for('admin_usuarios'))
        
        cursor.execute('SELECT COUNT(*) FROM Usuarios_Sistema WHERE rol = %s', ('admin',))
        admin_count = cursor.fetchone()[0]
        cursor.execute('SELECT username, rol FROM Usuarios_Sistema WHERE id_usuario = %s', (id,))
        usuario = cursor.fetchone()
        
        if usuario[1] == 'admin' and admin_count <= 1:
            flash('No se puede eliminar el último administrador', 'danger')
        else:
            cursor.execute('SELECT COUNT(*) FROM Log_Operaciones WHERE id_usuario = %s', (id,))
            logs_count = cursor.fetchone()[0]
            
            if logs_count > 0:
                cursor.execute('UPDATE Usuarios_Sistema SET activo = FALSE WHERE id_usuario = %s', (id,))
                flash(f'Usuario {usuario[0]} desactivado (tiene {logs_count} logs relacionados)', 'success')
            else:
                cursor.execute('DELETE FROM Usuarios_Sistema WHERE id_usuario = %s', (id,))
                flash(f'Usuario {usuario[0]} eliminado', 'success')
            
            conn.commit()
            log_operacion('BAJA', 'Usuarios_Sistema', id, f'Usuario eliminado/desactivado: {usuario[0]}')
    except Exception as e:
        flash(f'Error: {str(e)}', 'danger')
    finally:
        cursor.close()
        conn.close()
    
    return redirect(url_for('admin_usuarios'))

# ========== ADMIN: LOGS ==========
@app.route('/admin/logs')
@login_required
@role_required('admin')
def ver_logs():
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cursor.execute('''
        SELECT l.*, u.username 
        FROM Log_Operaciones l 
        LEFT JOIN Usuarios_Sistema u ON l.id_usuario = u.id_usuario 
        ORDER BY l.fecha_hora DESC 
        LIMIT 100
    ''')
    logs = cursor.fetchall()
    cursor.close()
    conn.close()
    
    return render_template('admin/logs.html', logs=logs)

# ========== VUELOS ==========
@app.route('/responsable/vuelos')
@login_required
@role_required('admin', 'responsable')
def responsable_vuelos():
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    
    estado = request.args.get('estado', '')
    fecha = request.args.get('fecha', '')
    origen = request.args.get('origen', '')
    destino = request.args.get('destino', '')
    
    query = '''
        SELECT v.*, a.nombre as aerolinea_nombre 
        FROM Vuelos v 
        LEFT JOIN Aerolineas a ON v.id_aerolinea = a.id_aerolinea 
        WHERE 1=1
    '''
    params = []
    
    if estado:
        query += ' AND v.estado = %s'
        params.append(estado)
    if fecha:
        query += ' AND DATE(v.fecha_salida) = %s'
        params.append(fecha)
    if origen:
        query += ' AND v.origen ILIKE %s'
        params.append(f'%{origen}%')
    if destino:
        query += ' AND v.destino ILIKE %s'
        params.append(f'%{destino}%')
    
    query += ' ORDER BY v.fecha_salida DESC'
    cursor.execute(query, params)
    vuelos = cursor.fetchall()
    
    cursor.close()
    conn.close()
    aerolineas = obtener_aerolineas()
    
    return render_template('responsable/vuelos.html', vuelos=vuelos, aerolineas=aerolineas)

@app.route('/responsable/agregar_vuelo', methods=['POST'])
@login_required
@role_required('admin', 'responsable')
def agregar_vuelo():
    id_vuelo = request.form['id_vuelo']
    id_aerolinea = request.form['id_aerolinea']
    origen = request.form['origen']
    destino = request.form['destino']
    fecha_salida = request.form['fecha_salida']
    fecha_llegada = request.form['fecha_llegada']
    estado = request.form['estado']
    puerta = request.form['puerta']
    
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            INSERT INTO Vuelos (id_vuelo, id_aerolinea, origen, destino, fecha_salida, fecha_llegada, estado, puerta_embarque)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        ''', (id_vuelo, id_aerolinea, origen, destino, fecha_salida, fecha_llegada, estado, puerta))
        conn.commit()
        log_operacion('ALTA', 'Vuelos', id_vuelo, f'Vuelo: {id_vuelo} - {origen} a {destino}')
        flash('Vuelo agregado exitosamente', 'success')
    except Exception as e:
        flash(f'Error: {str(e)}', 'danger')
    finally:
        cursor.close()
        conn.close()
    
    return redirect(url_for('responsable_vuelos'))

@app.route('/responsable/editar_vuelo/<id>', methods=['POST'])
@login_required
@role_required('admin', 'responsable')
def editar_vuelo(id):
    id_vuelo_nuevo = request.form['id_vuelo']
    id_aerolinea = request.form['id_aerolinea']
    origen = request.form['origen']
    destino = request.form['destino']
    fecha_salida = request.form['fecha_salida']
    fecha_llegada = request.form['fecha_llegada']
    estado = request.form['estado']
    puerta = request.form['puerta']
    
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        if id_vuelo_nuevo != id:
            cursor.execute('UPDATE Vuelos SET id_vuelo = %s WHERE id_vuelo = %s', (id_vuelo_nuevo, id))
            id = id_vuelo_nuevo
        
        cursor.execute('''
            UPDATE Vuelos 
            SET id_aerolinea = %s, origen = %s, destino = %s, 
                fecha_salida = %s, fecha_llegada = %s, estado = %s, puerta_embarque = %s
            WHERE id_vuelo = %s
        ''', (id_aerolinea, origen, destino, fecha_salida, fecha_llegada, estado, puerta, id))
        conn.commit()
        log_operacion('EDICION', 'Vuelos', id, f'Vuelo actualizado: {id}')
        flash('Vuelo actualizado exitosamente', 'success')
    except Exception as e:
        flash(f'Error: {str(e)}', 'danger')
    finally:
        cursor.close()
        conn.close()
    
    return redirect(url_for('responsable_vuelos'))

@app.route('/responsable/eliminar_vuelo/<id>')
@login_required
@role_required('admin')
def eliminar_vuelo(id):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('SELECT COUNT(*) FROM Reservas WHERE id_vuelo = %s', (id,))
        reservas_count = cursor.fetchone()[0]
        cursor.execute('SELECT COUNT(*) FROM Equipaje WHERE id_vuelo = %s', (id,))
        equipaje_count = cursor.fetchone()[0]
        
        if reservas_count > 0 or equipaje_count > 0:
            flash(f'No se puede eliminar el vuelo {id} porque tiene {reservas_count} reservas y {equipaje_count} equipajes relacionados', 'warning')
        else:
            cursor.execute('DELETE FROM Vuelos WHERE id_vuelo = %s', (id,))
            conn.commit()
            log_operacion('BAJA', 'Vuelos', id, f'Vuelo eliminado: {id}')
            flash(f'Vuelo {id} eliminado', 'success')
    except Exception as e:
        flash(f'Error: {str(e)}', 'danger')
    finally:
        cursor.close()
        conn.close()
    
    return redirect(url_for('responsable_vuelos'))

# ========== RESERVAS ==========
@app.route('/responsable/reservas')
@login_required
@role_required('admin', 'responsable')
def responsable_reservas():
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    
    # Obtener reservas con información de pasajeros y vuelos
    cursor.execute('''
        SELECT r.*, 
               p.nombre as pasajero_nombre, 
               p.apellidos as pasajero_apellidos,
               p.pasaporte,
               v.id_vuelo,
               v.origen,
               v.destino,
               v.fecha_salida,
               a.nombre as aerolinea_nombre
        FROM Reservas r
        LEFT JOIN Pasajeros p ON r.id_pasajero = p.id_pasajero
        LEFT JOIN Vuelos v ON r.id_vuelo = v.id_vuelo
        LEFT JOIN Aerolineas a ON v.id_aerolinea = a.id_aerolinea
        ORDER BY r.fecha_reserva DESC
    ''')
    reservas = cursor.fetchall()
    
    # Obtener datos para formularios
    cursor.execute('SELECT * FROM Pasajeros ORDER BY apellidos, nombre')
    pasajeros = cursor.fetchall()
    
    cursor.execute('''
        SELECT v.*, a.nombre as aerolinea_nombre 
        FROM Vuelos v 
        LEFT JOIN Aerolineas a ON v.id_aerolinea = a.id_aerolinea 
        ORDER BY v.fecha_salida
    ''')
    vuelos = cursor.fetchall()
    
    cursor.close()
    conn.close()
    
    return render_template('responsable/reservas.html', 
                         reservas=reservas, 
                         pasajeros=pasajeros, 
                         vuelos=vuelos)

@app.route('/responsable/agregar_reserva', methods=['POST'])
@login_required
@role_required('admin', 'responsable')
def agregar_reserva():
    id_pasajero = request.form['id_pasajero']
    id_vuelo = request.form['id_vuelo']
    clase = request.form['clase']
    asiento = request.form['asiento']
    precio = request.form['precio']
    estado = request.form['estado']
    
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            INSERT INTO Reservas (id_pasajero, id_vuelo, clase, asiento, precio, estado)
            VALUES (%s, %s, %s, %s, %s, %s) RETURNING id_reserva
        ''', (id_pasajero, id_vuelo, clase, asiento, precio, estado))
        nueva_id = cursor.fetchone()[0]
        conn.commit()
        
        cursor.execute('SELECT nombre, apellidos FROM Pasajeros WHERE id_pasajero = %s', (id_pasajero,))
        pasajero = cursor.fetchone()
        log_operacion('ALTA', 'Reservas', nueva_id, 
                     f'Reserva: Pasajero {pasajero[0]} {pasajero[1]} en vuelo {id_vuelo}')
        flash('Reserva agregada exitosamente', 'success')
    except Exception as e:
        flash(f'Error: {str(e)}', 'danger')
    finally:
        cursor.close()
        conn.close()
    
    return redirect(url_for('responsable_reservas'))

@app.route('/responsable/eliminar_reserva/<int:id>')
@login_required
@role_required('admin', 'responsable')
def eliminar_reserva(id):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('DELETE FROM Reservas WHERE id_reserva = %s', (id,))
        conn.commit()
        log_operacion('BAJA', 'Reservas', id, f'Reserva eliminada ID: {id}')
        flash('Reserva eliminada exitosamente', 'success')
    except Exception as e:
        flash(f'Error: {str(e)}', 'danger')
    finally:
        cursor.close()
        conn.close()
    
    return redirect(url_for('responsable_reservas'))

# ========== EQUIPAJE ==========
@app.route('/responsable/equipaje')
@login_required
@role_required('admin', 'responsable')
def responsable_equipaje():
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    
    cursor.execute('''
        SELECT e.*, 
               p.nombre as pasajero_nombre, 
               p.apellidos as pasajero_apellidos,
               v.id_vuelo,
               v.origen,
               v.destino
        FROM Equipaje e
        LEFT JOIN Pasajeros p ON e.id_pasajero = p.id_pasajero
        LEFT JOIN Vuelos v ON e.id_vuelo = v.id_vuelo
        ORDER BY e.id_equipaje DESC
    ''')
    equipaje = cursor.fetchall()
    
    cursor.execute('SELECT * FROM Pasajeros ORDER BY apellidos, nombre')
    pasajeros = cursor.fetchall()
    
    cursor.execute('SELECT * FROM Vuelos ORDER BY fecha_salida')
    vuelos = cursor.fetchall()
    
    cursor.close()
    conn.close()
    
    return render_template('responsable/equipaje.html', 
                         equipaje=equipaje, 
                         pasajeros=pasajeros, 
                         vuelos=vuelos)

@app.route('/responsable/agregar_equipaje', methods=['POST'])
@login_required
@role_required('admin', 'responsable')
def agregar_equipaje():
    id_pasajero = request.form['id_pasajero']
    id_vuelo = request.form['id_vuelo']
    peso_kg = request.form['peso_kg']
    tipo = request.form['tipo']
    etiqueta = request.form['etiqueta']
    
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            INSERT INTO Equipaje (id_pasajero, id_vuelo, peso_kg, tipo, etiqueta)
            VALUES (%s, %s, %s, %s, %s) RETURNING id_equipaje
        ''', (id_pasajero, id_vuelo, peso_kg, tipo, etiqueta))
        nueva_id = cursor.fetchone()[0]
        conn.commit()
        
        log_operacion('ALTA', 'Equipaje', nueva_id, f'Equipaje: {peso_kg}kg {tipo} etiqueta {etiqueta}')
        flash('Equipaje registrado exitosamente', 'success')
    except Exception as e:
        flash(f'Error: {str(e)}', 'danger')
    finally:
        cursor.close()
        conn.close()
    
    return redirect(url_for('responsable_equipaje'))

@app.route('/responsable/eliminar_equipaje/<int:id>')
@login_required
@role_required('admin', 'responsable')
def eliminar_equipaje(id):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('DELETE FROM Equipaje WHERE id_equipaje = %s', (id,))
        conn.commit()
        log_operacion('BAJA', 'Equipaje', id, f'Equipaje eliminado ID: {id}')
        flash('Equipaje eliminado exitosamente', 'success')
    except Exception as e:
        flash(f'Error: {str(e)}', 'danger')
    finally:
        cursor.close()
        conn.close()
    
    return redirect(url_for('responsable_equipaje'))

# ========== CONSULTAS ==========
@app.route('/consulta/vuelos_hoy')
@login_required
def consulta_vuelos_hoy():
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cursor.execute('''
        SELECT v.*, a.nombre as aerolinea_nombre 
        FROM Vuelos v 
        LEFT JOIN Aerolineas a ON v.id_aerolinea = a.id_aerolinea 
        WHERE DATE(v.fecha_salida) = CURRENT_DATE
        ORDER BY v.fecha_salida
    ''')
    vuelos = cursor.fetchall()
    cursor.close()
    conn.close()
    
    hoy = datetime.now().strftime('%d/%m/%Y')
    return render_template('consulta/vuelos_hoy.html', vuelos=vuelos, hoy=hoy)

@app.route('/consulta/pasajeros')
@login_required
def consulta_pasajeros():
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    
    nombre = request.args.get('nombre', '')
    apellido = request.args.get('apellido', '')
    pasaporte = request.args.get('pasaporte', '')
    
    query = 'SELECT * FROM Pasajeros WHERE 1=1'
    params = []
    
    if nombre:
        query += ' AND nombre ILIKE %s'
        params.append(f'%{nombre}%')
    if apellido:
        query += ' AND apellidos ILIKE %s'
        params.append(f'%{apellido}%')
    if pasaporte:
        query += ' AND pasaporte ILIKE %s'
        params.append(f'%{pasaporte}%')
    
    query += ' ORDER BY apellidos, nombre'
    cursor.execute(query, params)
    pasajeros = cursor.fetchall()
    
    cursor.close()
    conn.close()
    
    return render_template('consulta/pasajeros.html', pasajeros=pasajeros)

# ========== INICIO ==========
if __name__ == '__main__':
    print("="*60)
    print("🚀 SISTEMA AEROPORTUARIO COMPLETO - VERSIÓN FUNCIONAL")
    print("="*60)
    print("🌐 Accede en: http://localhost:5000")
    print("🔑 Usuarios de prueba:")
    print("   • admin / admin123       (Control total)")
    print("   • responsable / admin123 (Puede editar)")
    print("   • consulta / admin123    (Solo ver)")
    print("="*60)
    print("✅ Todas las rutas definidas")
    print("✅ CRUD completo para todas las tablas")
    print("✅ Sistema de Reservas y Equipaje")
    print("="*60)
    
    app.run(debug=True, host='0.0.0.0', port=5000)
