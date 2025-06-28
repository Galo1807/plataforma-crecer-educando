import sqlite3

# Conexión a la base de datos correcta
conn = sqlite3.connect('database/editorial.db')
c = conn.cursor()

# Tabla de deudas de proveedores
c.execute("""
    CREATE TABLE IF NOT EXISTS deudas_proveedor (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        proveedor_id INTEGER,
        fecha TEXT,
        valor REAL,
        descripcion TEXT,
        FOREIGN KEY (proveedor_id) REFERENCES proveedores(id)
    )
""")

# Tabla de abonos a proveedores
c.execute("""
    CREATE TABLE IF NOT EXISTS abonos_proveedor (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        proveedor_id INTEGER,
        fecha TEXT,
        valor REAL,
        descripcion TEXT,
        FOREIGN KEY (proveedor_id) REFERENCES proveedores(id)
    )
""")


conn.commit()
conn.close()
