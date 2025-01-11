from flask import Flask, render_template, request, redirect, url_for, send_file, session
import sqlite3
import pandas as pd
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle
from reportlab.lib import colors
from functools import wraps

app = Flask(__name__)
app.secret_key = "1234"  # Cambia esta clave por una más segura

# Decorador para restringir acceso según el rol
def role_required(role):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if 'role' not in session:
                return redirect(url_for('login'))  # Si no hay sesión, redirigir al login
            # Permitir acceso si el usuario tiene el rol requerido o es administrador
            if session['role'] != role and session['role'] != 'admin':
                return "Acceso denegado: no tiene los permisos necesarios.", 403
            return func(*args, **kwargs)
        return wrapper
    return decorator

# Ruta para el inicio de sesión
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        # Verificar credenciales
        conn = sqlite3.connect('database/attendance.db')
        cursor = conn.cursor()
        cursor.execute("SELECT id, role FROM users WHERE username = ? AND password = ?", (username, password))
        user = cursor.fetchone()
        conn.close()

        if user:
            session['user_id'] = user[0]
            session['role'] = user[1]
            return redirect(url_for('home'))
        else:
            return render_template('login.html', error="Credenciales incorrectas. Inténtelo de nuevo.")

    return render_template('login.html')

# Ruta para cerrar sesión
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# Ruta principal con control de acceso
@app.route('/')
def home():
    if 'role' not in session:
        return redirect(url_for('login'))

    # Menú dinámico según el rol
    menu = []
    if session['role'] == 'admin':
        menu = [
            {'label': 'Añadir Estudiante', 'url': url_for('add_student')},
            {'label': 'Registrar Asistencia', 'url': url_for('attendance')},
            {'label': 'Buscar Asistencia', 'url': url_for('search_attendance')},
            {'label': 'Ver Lista de Asistencia', 'url': url_for('list_attendance')},
            {'label': 'Cerrar Sesión', 'url': url_for('logout')}
        ]
    elif session['role'] == 'teacher':
        menu = [
            {'label': 'Registrar Asistencia', 'url': url_for('attendance')},
            {'label': 'Buscar Asistencia', 'url': url_for('search_attendance')},
            {'label': 'Ver Lista de Asistencia', 'url': url_for('list_attendance')},
            {'label': 'Cerrar Sesión', 'url': url_for('logout')}
        ]
    elif session['role'] == 'parent':
        menu = [
            {'label': 'Ver Asistencia de Hijos', 'url': url_for('parent_dashboard')},
            {'label': 'Cerrar Sesión', 'url': url_for('logout')}
        ]

    return render_template('home.html', role=session['role'], menu=menu)


# Ruta para registrar estudiantes
@app.route('/add_student', methods=['GET', 'POST'])
@role_required('teacher')
def add_student():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        identification = request.form['identification']
        grade = request.form['grade']

        conn = sqlite3.connect('database/attendance.db')
        cursor = conn.cursor()
        cursor.execute('INSERT INTO students (name, email, identification, grade) VALUES (?, ?, ?, ?)', 
                       (name, email, identification, grade))
        conn.commit()
        conn.close()

        return redirect(url_for('home'))

    return render_template('add_student.html')

# Ruta para registrar asistencia
@app.route('/attendance', methods=['GET', 'POST'])
@role_required('teacher')
def attendance():
    message = ""  # Variable inicializada vacía
    conn = sqlite3.connect('database/attendance.db')
    cursor = conn.cursor()

    if request.method == 'POST':
        student_id = request.form['student_id']
        status = request.form['status']
        date = request.form['date']

        cursor.execute('SELECT name, email, identification, grade FROM students WHERE id = ?', (student_id,))
        student = cursor.fetchone()
        if student:  # Verificar si se encontró el estudiante
            student_name, to_email, identification, grade = student

            cursor.execute('''
            INSERT INTO attendance (student_id, date, status, identification, grade) 
            VALUES (?, ?, ?, ?, ?)
            ''', (student_id, date, status, identification, grade))
            conn.commit()

            if status == 'Ausente':
                try:
                    send_email(to_email, student_name, date)
                    message = f"Correo enviado exitosamente a los padres del estudiante con identificación {identification}."
                except Exception as e:
                    message = f"Error al enviar el correo: {e}"
        else:
            message = "Estudiante no encontrado. Por favor, intente de nuevo."

    cursor.execute('SELECT id, name, identification, grade FROM students')
    students = cursor.fetchall()
    conn.close()

    return render_template('attendance.html', students=students, message=message)

# Ruta para listar registros de asistencia
@app.route('/list_attendance', methods=['GET'])
@role_required('teacher')
def list_attendance():
    conn = sqlite3.connect('database/attendance.db')
    cursor = conn.cursor()

    cursor.execute('''
    SELECT attendance.id, students.name, students.identification, students.grade, attendance.date, attendance.status
    FROM attendance
    INNER JOIN students ON attendance.student_id = students.id
    ''')
    attendance_records = cursor.fetchall()
    conn.close()

    return render_template('list_attendance.html', records=attendance_records)

# Ruta para descargar registros en CSV
@app.route('/download_csv', methods=['GET'])
def download_csv():
    import pandas as pd

    conn = sqlite3.connect('database/attendance.db')
    cursor = conn.cursor()

    # Obtener todos los registros de asistencia
    cursor.execute('''
    SELECT attendance.id, students.name, students.identification, students.grade, attendance.date, attendance.status
    FROM attendance
    INNER JOIN students ON attendance.student_id = students.id
    ''')
    attendance_records = cursor.fetchall()
    conn.close()

    # Crear un DataFrame con pandas
    df = pd.DataFrame(attendance_records, columns=['ID', 'Nombre del Estudiante', 'Documento', 'Grado', 'Fecha', 'Estado'])

    # Guardar el DataFrame como un archivo CSV
    csv_file = 'attendance_report.csv'
    df.to_csv(csv_file, index=False)

    # Enviar el archivo al navegador para descargarlo
    return send_file(csv_file, as_attachment=True)


# Función para enviar correos electrónicos
def send_email(to_email, student_name, date):
    # Configura tu correo y contraseña
    from_email = "hugoaromerop@gmail.com"
    from_password = "bczv ayqp tmvq avqx"

    # Crea el mensaje de correo
    subject = "Notificación de Ausencia"
    body = f"Estimado padre/madre de {student_name},\n\nLe informamos que su hijo/a estuvo ausente el día {date}.\nPor favor, comuníquese con el colegio para más información.\n\nAtentamente,\nSistema SACCE"
    
    # Configuración del correo
    message = MIMEMultipart()
    message["From"] = from_email
    message["To"] = to_email
    message["Subject"] = subject
    message.attach(MIMEText(body, "plain"))

    # Conexión al servidor SMTP
    try:
        server = smtplib.SMTP("smtp.gmail.com", 587)  # Gmail usa este servidor SMTP
        server.starttls()
        server.login(from_email, from_password)
        server.sendmail(from_email, to_email, message.as_string())
        server.quit()
        print(f"Correo enviado exitosamente a {to_email}")
    except Exception as e:
        print(f"Error al enviar el correo: {e}")
        
#Función para generar reportes en PDF
@app.route('/download_pdf', methods=['GET'])
def download_pdf():
    from reportlab.lib.pagesizes import letter
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle
    from reportlab.lib import colors

    conn = sqlite3.connect('database/attendance.db')
    cursor = conn.cursor()

    # Obtener todos los registros de asistencia
    cursor.execute('''
    SELECT attendance.id, students.name, students.identification, students.grade, attendance.date, attendance.status
    FROM attendance
    INNER JOIN students ON attendance.student_id = students.id
    ''')
    attendance_records = cursor.fetchall()
    conn.close()

    # Crear el archivo PDF
    pdf_file = "attendance_report.pdf"
    pdf = SimpleDocTemplate(pdf_file, pagesize=letter)
    elements = []

    # Crear tabla con los registros
    data = [["ID", "Nombre", "Documento", "Grado", "Fecha", "Estado"]] + list(attendance_records)
    table = Table(data)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
    ]))

    elements.append(table)
    pdf.build(elements)

    # Enviar el archivo PDF al navegador para descargarlo
    return send_file(pdf_file, as_attachment=True)


#Función para generar reportes en EXCEL

@app.route('/download_excel', methods=['GET'])
def download_excel():
    import pandas as pd

    conn = sqlite3.connect('database/attendance.db')
    cursor = conn.cursor()

    # Obtener todos los registros de asistencia
    cursor.execute('''
    SELECT attendance.id, students.name, students.identification, students.grade, attendance.date, attendance.status
    FROM attendance
    INNER JOIN students ON attendance.student_id = students.id
    ''')
    attendance_records = cursor.fetchall()
    conn.close()

    # Crear un DataFrame con pandas
    df = pd.DataFrame(attendance_records, columns=['ID', 'Nombre', 'Documento', 'Grado', 'Fecha', 'Estado'])

    # Guardar el DataFrame como un archivo Excel
    excel_file = "attendance_report.xlsx"
    df.to_excel(excel_file, index=False)

    # Enviar el archivo Excel al navegador para descargarlo
    return send_file(excel_file, as_attachment=True)

# Ruta para buscar registros de asistencia
@app.route('/search_attendance', methods=['GET', 'POST'])
@role_required('teacher')
def search_attendance():
    conn = sqlite3.connect('database/attendance.db')
    cursor = conn.cursor()
    results = []

    if request.method == 'POST':
        student_name = request.form.get('student_name', '').strip()
        identification = request.form.get('identification', '').strip()
        grade = request.form.get('grade', '').strip()
        date = request.form.get('date', '').strip()

        query = '''
        SELECT attendance.id, students.name, students.identification, students.grade, attendance.date, attendance.status
        FROM attendance
        INNER JOIN students ON attendance.student_id = students.id
        WHERE 1=1
        '''
        params = []

        if student_name:
            query += " AND students.name LIKE ?"
            params.append(f"%{student_name}%")

        if identification:
            query += " AND students.identification = ?"
            params.append(identification)

        if grade:
            query += " AND students.grade = ?"
            params.append(grade)

        if date:
            query += " AND attendance.date = ?"
            params.append(date)

        cursor.execute(query, params)
        results = cursor.fetchall()

    conn.close()

    return render_template('search_attendance.html', results=results)

#Función para editar registros de asistencia
@app.route('/edit_attendance/<int:attendance_id>', methods=['GET', 'POST'])
def edit_attendance(attendance_id):
    conn = sqlite3.connect('database/attendance.db')
    cursor = conn.cursor()

    if request.method == 'POST':
        # Actualizar el registro en la base de datos
        new_date = request.form['date']
        new_status = request.form['status']
        cursor.execute('''
        UPDATE attendance
        SET date = ?, status = ?
        WHERE id = ?
        ''', (new_date, new_status, attendance_id))
        conn.commit()
        conn.close()
        return redirect('/search_attendance')  # Redirigir a la página de búsqueda después de editar

    # Obtener los datos del registro para mostrar en el formulario
    cursor.execute('''
    SELECT attendance.id, students.name, attendance.date, students.grade, attendance.status
    FROM attendance
    INNER JOIN students ON attendance.student_id = students.id
    WHERE attendance.id = ?
    ''', (attendance_id,))
    record = cursor.fetchone()
    conn.close()

    return render_template('edit_attendance.html', record=record)


#Función para redirigir a parent dashboard

@app.route('/parent_dashboard')
@role_required('parent')
def parent_dashboard():
    # Aquí podrías obtener la asistencia de los hijos asociados al usuario 'parent'.
    conn = sqlite3.connect('database/attendance.db')
    cursor = conn.cursor()

    # Supongamos que cada padre está asociado a un grupo de estudiantes.
    # Aquí puedes adaptar la consulta para filtrar según el ID del usuario padre.
    parent_id = session.get('user_id')  # ID del usuario actual.
    cursor.execute('''
    SELECT attendance.date, attendance.status, students.name, students.grade
    FROM attendance
    INNER JOIN students ON attendance.student_id = students.id
    WHERE students.parent_id = ?
    ''', (parent_id,))
    attendance_records = cursor.fetchall()
    conn.close()

    return render_template('parent_dashboard.html', records=attendance_records)



if __name__ == '__main__':
    app.run(debug=True)
