import sqlite3

# Conectar a la base de datos
conn = sqlite3.connect('database/attendance.db')
cursor = conn.cursor()

# Crear usuarios de ejemplo
users = [
    ("admin", "admin123", "admin"),  # Usuario administrador
    ("teacher1", "teacher123", "teacher"),  # Docente
    ("parent1", "parent123", "parent")  # Padre
]

for user in users:
    try:
        cursor.execute("INSERT INTO users (username, password, role) VALUES (?, ?, ?)", user)
    except sqlite3.IntegrityError:
        print(f"El usuario '{user[0]}' ya existe.")

print("Usuarios añadidos con éxito.")

conn.commit()
conn.close()
