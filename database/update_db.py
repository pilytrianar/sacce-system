import sqlite3

# Conectar a la base de datos
conn = sqlite3.connect('database/attendance.db')
cursor = conn.cursor()

# Crear la tabla 'users'
try:
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL UNIQUE,
        password TEXT NOT NULL,
        role TEXT NOT NULL
    )
    ''')
    print("Tabla 'users' creada con éxito.")
except Exception as e:
    print(f"Error al crear la tabla 'users': {e}")

# Crear un vínculo entre padres y estudiantes en la tabla 'students'
try:
    cursor.execute('''
    ALTER TABLE students ADD COLUMN parent_id INTEGER
    ''')
    print("Columna 'parent_id' añadida a la tabla 'students'.")
except sqlite3.OperationalError:
    print("La columna 'parent_id' ya existe en la tabla 'students'.")

conn.commit()
conn.close()
