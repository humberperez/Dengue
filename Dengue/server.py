from flask import Flask, flash, render_template, request, redirect, url_for
from flask_mysqldb import MySQL
from dotenv import load_dotenv
import os
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from functools import wraps

app = Flask(__name__, static_url_path='/static')
load_dotenv()

# Conectar a MySQL
app.config['MYSQL_USER'] = os.getenv('MYSQL_USER')
app.config['MYSQL_PASSWORD'] = os.getenv('MYSQL_PASSWORD')
app.config['MYSQL_HOST'] = os.getenv('MYSQL_HOST')
app.config['MYSQL_DB'] = os.getenv('MYSQL_DB')

mysql = MySQL(app)

# Configuración de Flask-Login
app.secret_key = "mysecretkey"
login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message = "Por favor inicia sesión para acceder a esta página."

# Modelo de usuario
class User(UserMixin):
    def __init__(self, email, contraseña, is_admin=False):
        self.id = email
        self.email = email
        self.contraseña = contraseña
        self.is_admin = is_admin

@login_manager.user_loader
def load_user(email):
    with mysql.connection.cursor() as cur:
        cur.execute("SELECT Correo, Contraseña, is_admin FROM usuarios WHERE Correo = %s", (email,))
        user = cur.fetchone()
        if user:
            print(f"Usuario cargado: {user}")  # verifica los datos cargados
            return User(user[0], user[1], user[2])
    return None


# Decorador para restringir acceso de admin
def admin_required(f):
    @wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):
        if not current_user.is_admin:
            flash('Acceso denegado: solo el administrador puede acceder a esta página.', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# Rutas
@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None

    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        
        with mysql.connection.cursor() as cur:
            cur.execute("SELECT Correo, Contraseña, is_admin FROM usuarios WHERE correo = %s", (email,))
            user = cur.fetchone()
            if user:
                user_obj = User(user[0], user[1], user[2])
                print(f"Usuario encontrado: {user_obj.email}, is_admin: {user_obj.is_admin}")  # Debugging: verifica is_admin
                if password == user_obj.contraseña:
                    login_user(user_obj)
                    flash('¡Inicio de sesión exitoso!', 'success')
                    if user_obj.is_admin:
                        return redirect(url_for('data'))  # Redirige a la página de administrador
                    else:
                        error = "No tienes permisos de administrador para acceder a esta página."
                else:
                    error = "Credenciales inválidas. Por favor, inténtalo de nuevo."
            else:
                error = "Usuario no encontrado en el sistema."
    
    return render_template('login.html', error=error)

# Ruta principal
@app.route('/')
def main():
    return redirect(url_for('login'))


# Ruta de cierre de sesion
@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Has cerrado sesión', 'info')
    return redirect(url_for('login'))

# Ruta de gráfico
@app.route('/grafico')
@login_required
def grafico():
    return render_template('grafico.html')

@app.route('/graph')
def graph():
    cur = mysql.connection.cursor()
    cur.execute('SELECT grupo, COUNT(*) FROM pacientes GROUP BY grupo')
    data = cur.fetchall()
    print(data)
    labels = [row[0] for row in data]
    values = [row[1] for row in data]

    return render_template('graph.html', labels=labels, values=values)

# Leer datos de usuarios
@app.route('/usuarios')
@admin_required
def usuarios():
    try:
        with mysql.connection.cursor() as cur:
            cur.execute('SELECT nombre, correo, is_admin FROM usuarios')
            data = cur.fetchall()
        return render_template('usuarios.html', usuarios=data)
    except Exception as e:
        print(f"Error fetching data from database: {str(e)}")
        flash('Error al obtener los datos', 'error')
        return redirect(url_for('data'))

# Cargar usuario
@app.route('/cargar_usuario', methods=['GET', 'POST'])
@login_required
def cargar_usuario():
    if request.method == 'POST':
        nombre = request.form['nombre']
        correo = request.form['correo']
        contraseña = request.form['contraseña']
        is_admin = request.form.get('is_admin', False)

        try:
            with mysql.connection.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO usuarios 
                    (nombre, correo, contraseña, is_admin) 
                    VALUES (%s, %s, %s, %s)
                    """,
                    (nombre, correo, contraseña, is_admin))
                mysql.connection.commit()
            flash('Usuario cargado correctamente', 'success')
            return redirect(url_for('usuarios'))
        except Exception as e:
            print(f"Error al cargar usuario en la base de datos: {str(e)}")
            flash('Error al cargar usuario', 'error')

    return render_template(url_for('cargar_usuario'))

# Editar usuario
@app.route('/editar_usuario/<correo>', methods=['GET', 'POST'])
@login_required
def editar_usuario(correo):
    try:
        if request.method == 'GET':
            with mysql.connection.cursor() as cur:
                cur.execute('SELECT nombre, correo, is_admin FROM usuarios WHERE correo = %s', (correo,))
                data = cur.fetchone()
            return render_template('editar_usuario.html', usuario=data)
        
        elif request.method == 'POST':
            nombre = request.form['nombre']
            nuevo_correo = request.form['correo']
            is_admin = request.form['is_admin']

            with mysql.connection.cursor() as cur:
                cur.execute("""
                    UPDATE usuarios
                    SET nombre = %s,
                        correo = %s,
                        is_admin = %s
                    WHERE correo = %s
                """, (nombre, nuevo_correo, is_admin, correo))
                mysql.connection.commit()

            flash('Usuario actualizado correctamente', 'success')
            return redirect(url_for('usuarios'))

    except Exception as e:
        print(f"Error al editar usuario en la base de datos: {str(e)}")
        flash('Error al editar usuario', 'error')
        return redirect(url_for('usuarios'))


# Eliminar usuario
@app.route('/delete_usuario/<correo>', methods=['GET', 'POST'])
@login_required
def delete_usuario(correo):
    try:
        with mysql.connection.cursor() as cur:
            cur.execute('DELETE FROM usuarios WHERE Correo = %s', (correo,))
            mysql.connection.commit()
        flash('Usuario eliminado correctamente', 'success')
    except Exception as e:
        print(f"Error al eliminar usuario de la base de datos: {str(e)}")
        flash('Error al eliminar usuario', 'error')
    return redirect(url_for('usuarios'))

# Leer datos pacientes
@app.route('/data')
@admin_required
def data():
    try:
        with mysql.connection.cursor() as cur:
            cur.execute('SELECT Nombre, Telefono, Correo, Grupo, Sexo, Edad, Localidad, Direccion FROM pacientes')
            data = cur.fetchall()
        return render_template('index.html', pacientes=data)
    except Exception as e:
        print(f"Error fetching data from database: {str(e)}")
        flash('Error al obtener los datos', 'error')
        return redirect(url_for('data'))

# Guardar datos paciente
@app.route('/save', methods=['POST'])
@login_required
def save():
    try:
        if request.method == 'POST':
            nombre = request.form['nombre']
            telefono = request.form['telefono']
            correo = request.form['correo']
            sexo = request.form['sexo']
            edad = request.form['edad']
            grupo = request.form['grupo']
            localidad = request.form['localidad']
            direccion = request.form['direccion']
            with mysql.connection.cursor() as cur:
                cur.execute(
                    "INSERT INTO pacientes (Nombre, Telefono, Correo, Grupo, Sexo, Edad, Localidad, Direccion) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
                    (nombre, telefono, correo, grupo, sexo, edad, localidad, direccion))
                mysql.connection.commit()
            flash('Registro agregado correctamente', 'success')
    except Exception as e:
        print(f"Error al guardar registro en la base de datos: {str(e)}")
        flash('Error al guardar registro', 'error')
    return redirect(url_for('data'))

# Cargar datos paciente
@app.route('/cargar', methods=['GET', 'POST'])
@login_required
def cargar():
    if request.method == 'POST':
        nombre = request.form['nombre']
        telefono = request.form['telefono']
        correo = request.form['correo']
        grupo = request.form['grupo']
        sexo = request.form['sexo']
        edad = request.form['edad']
        localidad = request.form['localidad']
        direccion = request.form['direccion']

        try:
            with mysql.connection.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO pacientes 
                    (Nombre, Telefono, Correo, Grupo, Sexo, Edad, Localidad, Direccion) 
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (nombre, telefono, correo, grupo, sexo, edad, localidad, direccion))
                mysql.connection.commit()
            flash('Paciente cargado correctamente', 'success')
            return redirect(url_for('data'))
        except Exception as e:
            print(f"Error al cargar paciente en la base de datos: {str(e)}")
            flash('Error al cargar paciente', 'error')
    
    return render_template('cargar.html')


# tabla de pacientes
@app.route('/edit/<correo>', methods=['GET', 'POST'])
@login_required
def edit(correo):
    try:
        with mysql.connection.cursor() as cur:
            cur.execute('SELECT Nombre, Telefono, Correo, Grupo, Sexo, Edad, Localidad, Direccion FROM pacientes WHERE Correo = %s', (correo,))
            data = cur.fetchone()
        return render_template('edit.html', contact=data)
    except Exception as e:
        print(f"Error fetching data from database: {str(e)}")
        flash('Error al obtener los datos del paciente', 'error')
        return redirect(url_for('data'))

# editar datos paciente
@app.route('/update/<correo>', methods=['POST'])
@login_required
def update_contact(correo):
    try:
        if request.method == 'POST':
            nombre = request.form['nombre']
            telefono = request.form['telefono']
            nuevo_correo = request.form['correo']
            grupo = request.form['grupo']
            sexo = request.form['sexo']
            edad = request.form['edad']
            localidad = request.form['localidad']
            direccion = request.form['direccion']
            
            with mysql.connection.cursor() as cur:
                cur.execute("""
                    UPDATE pacientes
                    SET Nombre = %s,
                        Telefono = %s,
                        Correo = %s,
                        Grupo = %s,
                        Sexo = %s,
                        Edad = %s,
                        Localidad = %s,
                        Direccion = %s
                    WHERE Correo = %s
                """, (nombre, telefono, nuevo_correo, grupo, sexo, edad, localidad, direccion, correo))
                mysql.connection.commit()
            
            flash('Paciente actualizado correctamente', 'success')
            
    except Exception as e:
        print(f"Error al actualizar paciente en la base de datos: {str(e)}")
        flash('Error al actualizar paciente', 'error')
    
    return redirect(url_for('data'))


# Eliminar paciente
@app.route('/delete_contact/<correo>', methods=['GET', 'POST'])
@login_required
def delete_contact(correo):
    try:
        with mysql.connection.cursor() as cur:
            cur.execute('DELETE FROM pacientes WHERE Correo = %s', (correo,))
            mysql.connection.commit()
        flash('Paciente eliminado correctamente', 'success')
    except Exception as e:
        print(f"Error al eliminar paciente de la base de datos: {str(e)}")
        flash('Error al eliminar paciente', 'error')
    return redirect(url_for('data'))

# Iniciar el servidor
if __name__ == '__main__':
    app.run(port=9000, debug=True)
