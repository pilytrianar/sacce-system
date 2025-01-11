import sqlite3

# Conexión a la base de datos
conn = sqlite3.connect('database/attendance.db')
cursor = conn.cursor()

# Crear tabla de estudiantes
cursor.execute('''
CREATE TABLE IF NOT EXISTS students (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT NOT NULL
)
''')

# Crear tabla de asistencia
cursor.execute('''
CREATE TABLE IF NOT EXISTS attendance (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id INTEGER NOT NULL,
    date TEXT NOT NULL,
    status TEXT NOT NULL,
    FOREIGN KEY (student_id) REFERENCES students (id)
)
''')

print("Base de datos y tablas creadas con éxito.")
conn.commit()
conn.close()
