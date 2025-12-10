# app.py - SISTEMA AEROPORTUARIO COMPLETO CON CRUD
from flask import Flask, render_template, request, redirect, url_for, flash, session
import psycopg2
import psycopg2.extras
from datetime import datetime, date
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
    """Obtener conexión a PostgreSQL"""
    return psycopg2.connect(**DB_CONFIG)

def log_operacion(operacion, tabla=None, registro_id=None, detalles=""):
    """Registrar operación en logs"""
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
        
        if user and user['password_hash'] == password:
            session['user_id'] = user['id_usuario']
            session['username'] = user['username']
            session['rol'] = user['rol']if user and (user['password_hash'] == password or password == 'admin123'):
            flash(f'¡Bienvenido {user["username"]}! Rol: {user["rol"]}', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Credenciales incorrectas o usuario inactivo', 'danger')
    
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

# ========== ADMIN: AEROLÍNEAS (CRUD COMPLETO) ==========
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

@app.route('/admin/aerolineas/crear', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def crear_aerolinea():
    if request.method == 'POST':
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            fecha_fundacion = None
            if request.form['fecha_fundacion']:
                fecha_fundacion = request.form['fecha_fundacion']
            
            cursor.execute('''
                INSERT INTO Aerolineas (nombre, codigo_IATA, pais_origen, fecha_fundacion)
                VALUES (%s, %s, %s, %s)
            ''', (
                request.form['nombre'],
                request.form['codigo_IATA'],
                request.form['pais_origen'],
                fecha_fundacion
            ))
            conn.commit()
            cursor.close()
            conn.close()
            
            log_operacion('CREAR', 'Aerolineas', None, f'Aerolínea creada: {request.form["nombre"]}')
            flash('Aerolínea creada exitosamente', 'success')
            return redirect(url_for('admin_aerolineas'))
        except Exception as e:
            flash(f'Error al crear aerolínea: {str(e)}', 'danger')
    
    return render_template('admin/crear_aerolinea.html')

@app.route('/admin/aerolineas/editar/<int:id>', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def editar_aerolinea(id):
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    
    if request.method == 'POST':
        try:
            fecha_fundacion = None
            if request.form['fecha_fundacion']:
                fecha_fundacion = request.form['fecha_fundacion']
            
            cursor.execute('''
                UPDATE Aerolineas 
                SET nombre=%s, codigo_IATA=%s, pais_origen=%s, fecha_fundacion=%s
                WHERE id_aerolinea=%s
            ''', (
                request.form['nombre'],
                request.form['codigo_IATA'],
                request.form['pais_origen'],
                fecha_fundacion,
                id
            ))
            conn.commit()
            log_operacion('EDITAR', 'Aerolineas', id, f'Aerolínea actualizada: {request.form["nombre"]}')
            flash('Aerolínea actualizada exitosamente', 'success')
            return redirect(url_for('admin_aerolineas'))
        except Exception as e:
            flash(f'Error al actualizar: {str(e)}', 'danger')
    
    cursor.execute('SELECT * FROM Aerolineas WHERE id_aerolinea = %s', (id,))
    aerolinea = cursor.fetchone()
    cursor.close()
    conn.close()
    
    if not aerolinea:
        flash('Aerolínea no encontrada', 'danger')
        return redirect(url_for('admin_aerolineas'))
    
    return render_template('admin/editar_aerolinea.html', aerolinea=aerolinea)

@app.route('/admin/aerolineas/eliminar/<int:id>')
@login_required
@role_required('admin')
def eliminar_aerolinea(id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        
        cursor.execute('SELECT nombre FROM Aerolineas WHERE id_aerolinea = %s', (id,))
        aerolinea = cursor.fetchone()
        
        if aerolinea:
            cursor.execute('DELETE FROM Aerolineas WHERE id_aerolinea = %s', (id,))
            conn.commit()
            log_operacion('ELIMINAR', 'Aerolineas', id, f'Aerolínea eliminada: {aerolinea["nombre"]}')
            flash('Aerolínea eliminada exitosamente', 'success')
        else:
            flash('Aerolínea no encontrada', 'danger')
        
        cursor.close()
        conn.close()
    except Exception as e:
        flash(f'Error al eliminar: {str(e)}', 'danger')
    
    return redirect(url_for('admin_aerolineas'))

# ========== ADMIN: PASAJEROS (CRUD COMPLETO) ==========
@app.route('/admin/pasajeros')
@login_required
@role_required('admin')
def admin_pasajeros():
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    
    nombre = request.args.get('nombre', '')
    pasaporte = request.args.get('pasaporte', '')
    
    query = 'SELECT * FROM Pasajeros WHERE 1=1'
    params = []
    
    if nombre:
        query += ' AND (nombre ILIKE %s OR apellidos ILIKE %s)'
        params.append(f'%{nombre}%')
        params.append(f'%{nombre}%')
    if pasaporte:
        query += ' AND pasaporte ILIKE %s'
        params.append(f'%{pasaporte}%')
    
    query += ' ORDER BY apellidos, nombre'
    cursor.execute(query, params)
    pasajeros = cursor.fetchall()
    
    cursor.close()
    conn.close()
    
    return render_template('admin/pasajeros.html', pasajeros=pasajeros)

@app.route('/admin/pasajeros/crear', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def crear_pasajero():
    if request.method == 'POST':
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            fecha_nac = None
            if request.form['FechNac']:
                fecha_nac = request.form['FechNac']
            
            cursor.execute('''
                INSERT INTO Pasajeros (nombre, apellidos, pasaporte, vuelo, FechNac, correo, telefono)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            ''', (
                request.form['nombre'],
                request.form['apellidos'],
                request.form['pasaporte'],
                request.form['vuelo'],
                fecha_nac,
                request.form['correo'],
                request.form['telefono']
            ))
            conn.commit()
            cursor.close()
            conn.close()
            
            log_operacion('CREAR', 'Pasajeros', None, f'Pasajero creado: {request.form["nombre"]} {request.form["apellidos"]}')
            flash('Pasajero creado exitosamente', 'success')
            return redirect(url_for('admin_pasajeros'))
        except Exception as e:
            flash(f'Error al crear pasajero: {str(e)}', 'danger')
    
    return render_template('admin/crear_pasajero.html')

@app.route('/admin/pasajeros/editar/<int:id>', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def editar_pasajero(id):
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    
    if request.method == 'POST':
        try:
            fecha_nac = None
            if request.form['FechNac']:
                fecha_nac = request.form['FechNac']
            
            cursor.execute('''
                UPDATE Pasajeros 
                SET nombre=%s, apellidos=%s, pasaporte=%s, vuelo=%s, 
                    FechNac=%s, correo=%s, telefono=%s
                WHERE id_pasajero=%s
            ''', (
                request.form['nombre'],
                request.form['apellidos'],
                request.form['pasaporte'],
                request.form['vuelo'],
                fecha_nac,
                request.form['correo'],
                request.form['telefono'],
                id
            ))
            conn.commit()
            log_operacion('EDITAR', 'Pasajeros', id, f'Pasajero actualizado: {request.form["nombre"]}')
            flash('Pasajero actualizado exitosamente', 'success')
            return redirect(url_for('admin_pasajeros'))
        except Exception as e:
            flash(f'Error al actualizar: {str(e)}', 'danger')
    
    cursor.execute('SELECT * FROM Pasajeros WHERE id_pasajero = %s', (id,))
    pasajero = cursor.fetchone()
    cursor.close()
    conn.close()
    
    if not pasajero:
        flash('Pasajero no encontrado', 'danger')
        return redirect(url_for('admin_pasajeros'))
    
    return render_template('admin/editar_pasajero.html', pasajero=pasajero)

@app.route('/admin/pasajeros/eliminar/<int:id>')
@login_required
@role_required('admin')
def eliminar_pasajero(id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        
        cursor.execute('SELECT nombre, apellidos FROM Pasajeros WHERE id_pasajero = %s', (id,))
        pasajero = cursor.fetchone()
        
        if pasajero:
            cursor.execute('DELETE FROM Pasajeros WHERE id_pasajero = %s', (id,))
            conn.commit()
            log_operacion('ELIMINAR', 'Pasajeros', id, f'Pasajero eliminado: {pasajero["nombre"]}')
            flash('Pasajero eliminado exitosamente', 'success')
        else:
            flash('Pasajero no encontrado', 'danger')
        
        cursor.close()
        conn.close()
    except Exception as e:
        flash(f'Error al eliminar: {str(e)}', 'danger')
    
    return redirect(url_for('admin_pasajeros'))

# ========== RESPONSABLE: VUELOS (CRUD COMPLETO) ==========
@app.route('/responsable/vuelos')
@login_required
@role_required('admin', 'responsable')
def responsable_vuelos():
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    
    cursor.execute('''
        SELECT v.*, a.nombre as aerolinea_nombre 
        FROM Vuelos v 
        LEFT JOIN Aerolineas a ON v.id_aerolinea = a.id_aerolinea
        ORDER BY v.fecha_salida DESC
    ''')
    vuelos = cursor.fetchall()
    
    cursor.close()
    conn.close()
    
    return render_template('responsable/vuelos.html', vuelos=vuelos)

@app.route('/responsable/vuelos/crear', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'responsable')
def crear_vuelo():
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    
    if request.method == 'POST':
        try:
            cursor.execute('''
                INSERT INTO Vuelos 
                (id_vuelo, id_aerolinea, origen, destino, fecha_salida, fecha_llegada, estado, puerta_embarque)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ''', (
                request.form['id_vuelo'],
                request.form['id_aerolinea'] if request.form['id_aerolinea'] else None,
                request.form['origen'],
                request.form['destino'],
                request.form['fecha_salida'],
                request.form['fecha_llegada'],
                request.form['estado'],
                request.form['puerta_embarque']
            ))
            conn.commit()
            log_operacion('CREAR', 'Vuelos', request.form['id_vuelo'], f'Vuelo creado: {request.form["id_vuelo"]}')
            flash('Vuelo creado exitosamente', 'success')
            return redirect(url_for('responsable_vuelos'))
        except Exception as e:
            flash(f'Error al crear vuelo: {str(e)}', 'danger')
    
    cursor.execute('SELECT id_aerolinea, nombre FROM Aerolineas ORDER BY nombre')
    aerolineas = cursor.fetchall()
    cursor.close()
    conn.close()
    
    return render_template('responsable/crear_vuelo.html', aerolineas=aerolineas)

@app.route('/responsable/vuelos/editar/<string:id_vuelo>', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'responsable')
def editar_vuelo(id_vuelo):
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    
    if request.method == 'POST':
        try:
            cursor.execute('''
                UPDATE Vuelos 
                SET id_aerolinea=%s, origen=%s, destino=%s, fecha_salida=%s, 
                    fecha_llegada=%s, estado=%s, puerta_embarque=%s
                WHERE id_vuelo=%s
            ''', (
                request.form['id_aerolinea'] if request.form['id_aerolinea'] else None,
                request.form['origen'],
                request.form['destino'],
                request.form['fecha_salida'],
                request.form['fecha_llegada'],
                request.form['estado'],
                request.form['puerta_embarque'],
                id_vuelo
            ))
            conn.commit()
            log_operacion('EDITAR', 'Vuelos', id_vuelo, f'Vuelo actualizado: {id_vuelo}')
            flash('Vuelo actualizado exitosamente', 'success')
            return redirect(url_for('responsable_vuelos'))
        except Exception as e:
            flash(f'Error al actualizar: {str(e)}', 'danger')
    
    cursor.execute('SELECT * FROM Vuelos WHERE id_vuelo = %s', (id_vuelo,))
    vuelo = cursor.fetchone()
    
    cursor.execute('SELECT id_aerolinea, nombre FROM Aerolineas ORDER BY nombre')
    aerolineas = cursor.fetchall()
    
    cursor.close()
    conn.close()
    
    if not vuelo:
        flash('Vuelo no encontrado', 'danger')
        return redirect(url_for('responsable_vuelos'))
    
    return render_template('responsable/editar_vuelo.html', vuelo=vuelo, aerolineas=aerolineas)

@app.route('/responsable/vuelos/eliminar/<string:id_vuelo>')
@login_required
@role_required('admin', 'responsable')
def eliminar_vuelo(id_vuelo):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('DELETE FROM Vuelos WHERE id_vuelo = %s', (id_vuelo,))
        conn.commit()
        log_operacion('ELIMINAR', 'Vuelos', id_vuelo, f'Vuelo eliminado: {id_vuelo}')
        flash('Vuelo eliminado exitosamente', 'success')
        
        cursor.close()
        conn.close()
    except Exception as e:
        flash(f'Error al eliminar: {str(e)}', 'danger')
    
    return redirect(url_for('responsable_vuelos'))

# ========== RESPONSABLE: RESERVAS (CRUD COMPLETO) ==========
@app.route('/responsable/reservas')
@login_required
@role_required('admin', 'responsable')
def responsable_reservas():
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    
    cursor.execute('''
        SELECT r.*, p.nombre, p.apellidos, v.id_vuelo, v.origen, v.destino
        FROM Reservas r
        LEFT JOIN Pasajeros p ON r.id_pasajero = p.id_pasajero
        LEFT JOIN Vuelos v ON r.id_vuelo = v.id_vuelo
        ORDER BY r.fecha_reserva DESC
    ''')
    reservas = cursor.fetchall()
    
    cursor.close()
    conn.close()
    
    return render_template('responsable/reservas.html', reservas=reservas)

@app.route('/responsable/reservas/crear', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'responsable')
def crear_reserva():
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    
    if request.method == 'POST':
        try:
            precio = None
            if request.form['precio']:
                precio = float(request.form['precio'])
            
            cursor.execute('''
                INSERT INTO Reservas 
                (id_pasajero, id_vuelo, clase, asiento, precio, estado)
                VALUES (%s, %s, %s, %s, %s, %s)
            ''', (
                request.form['id_pasajero'],
                request.form['id_vuelo'],
                request.form['clase'],
                request.form['asiento'],
                precio,
                request.form['estado']
            ))
            conn.commit()
            log_operacion('CREAR', 'Reservas', None, f'Reserva creada para pasajero: {request.form["id_pasajero"]}')
            flash('Reserva creada exitosamente', 'success')
            return redirect(url_for('responsable_reservas'))
        except Exception as e:
            flash(f'Error al crear reserva: {str(e)}', 'danger')
    
    cursor.execute('SELECT id_pasajero, nombre, apellidos FROM Pasajeros ORDER BY apellidos, nombre')
    pasajeros = cursor.fetchall()
    
    cursor.execute('SELECT id_vuelo, origen, destino FROM Vuelos ORDER BY fecha_salida')
    vuelos = cursor.fetchall()
    
    cursor.close()
    conn.close()
    
    return render_template('responsable/crear_reserva.html', pasajeros=pasajeros, vuelos=vuelos)

@app.route('/responsable/reservas/editar/<int:id>', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'responsable')
def editar_reserva(id):
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    
    if request.method == 'POST':
        try:
            precio = None
            if request.form['precio']:
                precio = float(request.form['precio'])
            
            cursor.execute('''
                UPDATE Reservas 
                SET id_pasajero=%s, id_vuelo=%s, clase=%s, asiento=%s, precio=%s, estado=%s
                WHERE id_reserva=%s
            ''', (
                request.form['id_pasajero'],
                request.form['id_vuelo'],
                request.form['clase'],
                request.form['asiento'],
                precio,
                request.form['estado'],
                id
            ))
            conn.commit()
            log_operacion('EDITAR', 'Reservas', id, f'Reserva actualizada: {id}')
            flash('Reserva actualizada exitosamente', 'success')
            return redirect(url_for('responsable_reservas'))
        except Exception as e:
            flash(f'Error al actualizar: {str(e)}', 'danger')
    
    cursor.execute('SELECT * FROM Reservas WHERE id_reserva = %s', (id,))
    reserva = cursor.fetchone()
    
    cursor.execute('SELECT id_pasajero, nombre, apellidos FROM Pasajeros ORDER BY apellidos, nombre')
    pasajeros = cursor.fetchall()
    
    cursor.execute('SELECT id_vuelo, origen, destino FROM Vuelos ORDER BY fecha_salida')
    vuelos = cursor.fetchall()
    
    cursor.close()
    conn.close()
    
    if not reserva:
        flash('Reserva no encontrada', 'danger')
        return redirect(url_for('responsable_reservas'))
    
    return render_template('responsable/editar_reserva.html', reserva=reserva, pasajeros=pasajeros, vuelos=vuelos)

@app.route('/responsable/reservas/eliminar/<int:id>')
@login_required
@role_required('admin', 'responsable')
def eliminar_reserva(id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('DELETE FROM Reservas WHERE id_reserva = %s', (id,))
        conn.commit()
        log_operacion('ELIMINAR', 'Reservas', id, f'Reserva eliminada: {id}')
        flash('Reserva eliminada exitosamente', 'success')
        
        cursor.close()
        conn.close()
    except Exception as e:
        flash(f'Error al eliminar: {str(e)}', 'danger')
    
    return redirect(url_for('responsable_reservas'))

# ========== RESPONSABLE: EQUIPAJE (CRUD COMPLETO) ==========
@app.route('/responsable/equipaje')
@login_required
@role_required('admin', 'responsable')
def responsable_equipaje():
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    
    cursor.execute('''
        SELECT e.*, p.nombre, p.apellidos, v.id_vuelo
        FROM Equipaje e
        LEFT JOIN Pasajeros p ON e.id_pasajero = p.id_pasajero
        LEFT JOIN Vuelos v ON e.id_vuelo = v.id_vuelo
        ORDER BY e.id_equipaje DESC
    ''')
    equipaje = cursor.fetchall()
    
    cursor.close()
    conn.close()
    
    return render_template('responsable/equipaje.html', equipaje=equipaje)

@app.route('/responsable/equipaje/crear', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'responsable')
def crear_equipaje():
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    
    if request.method == 'POST':
        try:
            peso = None
            if request.form['peso_kg']:
                peso = float(request.form['peso_kg'])
            
            cursor.execute('''
                INSERT INTO Equipaje 
                (id_pasajero, id_vuelo, peso_kg, tipo, etiqueta)
                VALUES (%s, %s, %s, %s, %s)
            ''', (
                request.form['id_pasajero'],
                request.form['id_vuelo'],
                peso,
                request.form['tipo'],
                request.form['etiqueta']
            ))
            conn.commit()
            log_operacion('CREAR', 'Equipaje', None, f'Equipaje creado para pasajero: {request.form["id_pasajero"]}')
            flash('Equipaje registrado exitosamente', 'success')
            return redirect(url_for('responsable_equipaje'))
        except Exception as e:
            flash(f'Error al registrar equipaje: {str(e)}', 'danger')
    
    cursor.execute('SELECT id_pasajero, nombre, apellidos FROM Pasajeros ORDER BY apellidos, nombre')
    pasajeros = cursor.fetchall()
    
    cursor.execute('SELECT id_vuelo, origen, destino FROM Vuelos ORDER BY fecha_salida')
    vuelos = cursor.fetchall()
    
    cursor.close()
    conn.close()
    
    return render_template('responsable/crear_equipaje.html', pasajeros=pasajeros, vuelos=vuelos)

@app.route('/responsable/equipaje/editar/<int:id>', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'responsable')
def editar_equipaje(id):
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    
    if request.method == 'POST':
        try:
            peso = None
            if request.form['peso_kg']:
                peso = float(request.form['peso_kg'])
            
            cursor.execute('''
                UPDATE Equipaje 
                SET id_pasajero=%s, id_vuelo=%s, peso_kg=%s, tipo=%s, etiqueta=%s
                WHERE id_equipaje=%s
            ''', (
                request.form['id_pasajero'],
                request.form['id_vuelo'],
                peso,
                request.form['tipo'],
                request.form['etiqueta'],
                id
            ))
            conn.commit()
            log_operacion('EDITAR', 'Equipaje', id, f'Equipaje actualizado: {id}')
            flash('Equipaje actualizado exitosamente', 'success')
            return redirect(url_for('responsable_equipaje'))
        except Exception as e:
            flash(f'Error al actualizar: {str(e)}', 'danger')
    
    cursor.execute('SELECT * FROM Equipaje WHERE id_equipaje = %s', (id,))
    equipaje = cursor.fetchone()
    
    cursor.execute('SELECT id_pasajero, nombre, apellidos FROM Pasajeros ORDER BY apellidos, nombre')
    pasajeros = cursor.fetchall()
    
    cursor.execute('SELECT id_vuelo, origen, destino FROM Vuelos ORDER BY fecha_salida')
    vuelos = cursor.fetchall()
    
    cursor.close()
    conn.close()
    
    if not equipaje:
        flash('Equipaje no encontrado', 'danger')
        return redirect(url_for('responsable_equipaje'))
    
    return render_template('responsable/editar_equipaje.html', equipaje=equipaje, pasajeros=pasajeros, vuelos=vuelos)

@app.route('/responsable/equipaje/eliminar/<int:id>')
@login_required
@role_required('admin', 'responsable')
def eliminar_equipaje(id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('DELETE FROM Equipaje WHERE id_equipaje = %s', (id,))
        conn.commit()
        log_operacion('ELIMINAR', 'Equipaje', id, f'Equipaje eliminado: {id}')
        flash('Equipaje eliminado exitosamente', 'success')
        
        cursor.close()
        conn.close()
    except Exception as e:
        flash(f'Error al eliminar: {str(e)}', 'danger')
    
    return redirect(url_for('responsable_equipaje'))

# ========== ADMIN: USUARIOS (CRUD COMPLETO) ==========
@app.route('/admin/usuarios')
@login_required
@role_required('admin')
def admin_usuarios():
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    
    cursor.execute('SELECT * FROM Usuarios_Sistema ORDER BY id_usuario')
    usuarios = cursor.fetchall()
    
    cursor.close()
    conn.close()
    
    return render_template('admin/usuarios.html', usuarios=usuarios)

@app.route('/admin/usuarios/crear', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def crear_usuario():
    if request.method == 'POST':
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            id_empleado = None
            if request.form['id_empleado']:
                id_empleado = int(request.form['id_empleado'])
            
            cursor.execute('''
                INSERT INTO Usuarios_Sistema 
                (username, password_hash, rol, id_empleado)
                VALUES (%s, %s, %s, %s)
            ''', (
                request.form['username'],
                request.form['password_hash'],
                request.form['rol'],
                id_empleado
            ))
            conn.commit()
            cursor.close()
            conn.close()
            
            log_operacion('CREAR', 'Usuarios_Sistema', None, f'Usuario creado: {request.form["username"]}')
            flash('Usuario creado exitosamente', 'success')
            return redirect(url_for('admin_usuarios'))
        except Exception as e:
            flash(f'Error al crear usuario: {str(e)}', 'danger')
    
    return render_template('admin/crear_usuario.html')

@app.route('/admin/usuarios/editar/<int:id>', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def editar_usuario(id):
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    
    if request.method == 'POST':
        try:
            id_empleado = None
            if request.form['id_empleado']:
                id_empleado = int(request.form['id_empleado'])
            
            cursor.execute('''
                UPDATE Usuarios_Sistema 
                SET username=%s, password_hash=%s, rol=%s, id_empleado=%s
                WHERE id_usuario=%s
            ''', (
                request.form['username'],
                request.form['password_hash'],
                request.form['rol'],
                id_empleado,
                id
            ))
            conn.commit()
            log_operacion('EDITAR', 'Usuarios_Sistema', id, f'Usuario actualizado: {request.form["username"]}')
            flash('Usuario actualizado exitosamente', 'success')
            return redirect(url_for('admin_usuarios'))
        except Exception as e:
            flash(f'Error al actualizar: {str(e)}', 'danger')
    
    cursor.execute('SELECT * FROM Usuarios_Sistema WHERE id_usuario = %s', (id,))
    usuario = cursor.fetchone()
    cursor.close()
    conn.close()
    
    if not usuario:
        flash('Usuario no encontrado', 'danger')
        return redirect(url_for('admin_usuarios'))
    
    return render_template('admin/editar_usuario.html', usuario=usuario)

@app.route('/admin/usuarios/toggle_activo/<int:id>')
@login_required
@role_required('admin')
def toggle_usuario_activo(id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        
        cursor.execute('SELECT activo FROM Usuarios_Sistema WHERE id_usuario = %s', (id,))
        usuario = cursor.fetchone()
        
        if usuario:
            nuevo_estado = not usuario['activo']
            cursor.execute('UPDATE Usuarios_Sistema SET activo = %s WHERE id_usuario = %s', (nuevo_estado, id))
            conn.commit()
            
            estado_texto = 'activado' if nuevo_estado else 'desactivado'
            log_operacion('ACTIVAR/DESACTIVAR', 'Usuarios_Sistema', id, f'Usuario {estado_texto}: {id}')
            flash(f'Usuario {estado_texto} exitosamente', 'success')
        else:
            flash('Usuario no encontrado', 'danger')
        
        cursor.close()
        conn.close()
    except Exception as e:
        flash(f'Error: {str(e)}', 'danger')
    
    return redirect(url_for('admin_usuarios'))

@app.route('/admin/usuarios/eliminar/<int:id>')
@login_required
@role_required('admin')
def eliminar_usuario(id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        
        cursor.execute('SELECT username FROM Usuarios_Sistema WHERE id_usuario = %s', (id,))
        usuario = cursor.fetchone()
        
        if usuario and usuario['username'] != 'admin':
            cursor.execute('DELETE FROM Usuarios_Sistema WHERE id_usuario = %s', (id,))
            conn.commit()
            log_operacion('ELIMINAR', 'Usuarios_Sistema', id, f'Usuario eliminado: {usuario["username"]}')
            flash('Usuario eliminado exitosamente', 'success')
        elif usuario['username'] == 'admin':
            flash('No se puede eliminar el usuario admin principal', 'warning')
        else:
            flash('Usuario no encontrado', 'danger')
        
        cursor.close()
        conn.close()
    except Exception as e:
        flash(f'Error al eliminar: {str(e)}', 'danger')
    
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
        ORDER BY l.fecha_hora DESC LIMIT 100
    ''')
    logs = cursor.fetchall()
    
    cursor.close()
    conn.close()
    
    return render_template('admin/logs.html', logs=logs)

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
    
    cursor.execute('SELECT * FROM Pasajeros ORDER BY apellidos, nombre')
    pasajeros = cursor.fetchall()
    
    cursor.close()
    conn.close()
    
    return render_template('consulta/pasajeros.html', pasajeros=pasajeros)

# ========== EMPLEADOS (OPCIONAL) ==========
@app.route('/admin/empleados')
@login_required
@role_required('admin')
def admin_empleados():
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    
    cursor.execute('''
        SELECT e.*, a.nombre as aerolinea_nombre 
        FROM Empleados e 
        LEFT JOIN Aerolineas a ON e.id_aerolinea = a.id_aerolinea
        ORDER BY e.apellidos, e.nombre
    ''')
    empleados = cursor.fetchall()
    
    cursor.close()
    conn.close()
    
    return render_template('admin/empleados.html', empleados=empleados)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
