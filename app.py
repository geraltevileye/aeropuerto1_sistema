# app.py - SISTEMA AEROPORTUARIO COMPLETO
from flask import Flask, render_template, request, redirect, url_for, flash, session
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
    return psycopg2.connect(**DB_CONFIG)

def log_operacion(operacion, tabla=None, registro_id=None, detalles=""):
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
        except:
            pass

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

# ========== RESERVAS ==========
@app.route('/responsable/reservas')
@login_required
@role_required('admin', 'responsable')
def responsable_reservas():
    """ESTA ES LA FUNCIÓN QUE FALTABA"""
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

# ========== VUELOS ==========
@app.route('/responsable/vuelos')
@login_required
@role_required('admin', 'responsable')
def responsable_vuelos():
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cursor.execute('SELECT * FROM Vuelos ORDER BY fecha_salida DESC')
    vuelos = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('responsable/vuelos.html', vuelos=vuelos)

# ========== EQUIPAJE ==========
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

# ========== ADMIN: PASAJEROS ==========
@app.route('/admin/pasajeros')
@login_required
@role_required('admin')
def admin_pasajeros():
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cursor.execute('SELECT * FROM Pasajeros ORDER BY apellidos, nombre')
    pasajeros = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('admin/pasajeros.html', pasajeros=pasajeros)

# ========== ADMIN: USUARIOS ==========
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

# ========== ADMIN: LOGS ==========
@app.route('/admin/logs')
@login_required
@role_required('admin')
def ver_logs():
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cursor.execute('SELECT * FROM Log_Operaciones ORDER BY fecha_hora DESC LIMIT 100')
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
    cursor.execute("SELECT * FROM Vuelos WHERE DATE(fecha_salida) = CURRENT_DATE ORDER BY fecha_salida")
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

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
