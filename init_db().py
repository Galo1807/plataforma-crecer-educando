import sqlite3

# Ruta a tu base de datos
DATABASE = 'database/editorial.db'

# Conexión y creación de tabla
conn = sqlite3.connect(DATABASE)
c = conn.cursor()

# Crear la tabla 'entregas' si no existe
c.execute('''
    CREATE TABLE IF NOT EXISTS entregas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        cliente_id INTEGER NOT NULL,
        materia TEXT NOT NULL,
        cantidad INTEGER NOT NULL,
        precio REAL NOT NULL,
        nota TEXT,
        fecha TEXT NOT NULL
    )
''')

conn.commit()
conn.close()

print("✅ Tabla 'entregas' creada correctamente.")
