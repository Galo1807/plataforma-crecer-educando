from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.utils import secure_filename
import os
import sqlite3
from flask import send_file
from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

app = Flask(__name__)
app.secret_key = 'editorial_secret_key'
UPLOAD_FOLDER = 'static/images'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

DATABASE = 'database/editorial.db'

def precio_del_libro(nombre):
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute("SELECT precio FROM libros WHERE nombre = ?", (nombre,))
    resultado = c.fetchone()
    conn.close()
    return resultado[0] if resultado else 0.0


# Obtener cliente
def obtener_cliente(cliente_id):
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute("SELECT * FROM clientes WHERE id = ?", (cliente_id,))
    cliente = c.fetchone()
    conn.close()
    return cliente

# Obtener entregas
def obtener_entregas(cliente_id):
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute("""
        SELECT id, libro, cantidad, precio_unitario, fecha, nota
        FROM ventas
        WHERE cliente_id = ?
    """, (cliente_id,))
    entregas = c.fetchall()
    conn.close()
    return entregas


# Obtener devoluciones
def obtener_devoluciones(cliente_id):
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute("SELECT * FROM devoluciones WHERE cliente_id = ?", (cliente_id,))
    devoluciones = c.fetchall()
    conn.close()
    return devoluciones

# Obtener abonos
def obtener_abonos(cliente_id):
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute("SELECT * FROM abonos WHERE cliente_id = ?", (cliente_id,))
    abonos = c.fetchall()
    conn.close()
    return abonos

# Guardar entrega
def guardar_entrega(cliente_id, fecha, nota, materias, cantidades):
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    for materia, cantidad in zip(materias, cantidades):
        if materia and cantidad:
            # Consultar el precio real del libro
            c.execute("SELECT precio FROM libros WHERE nombre = ?", (materia,))
            precio = c.fetchone()
            if precio:
                c.execute("""
                    INSERT INTO ventas (cliente_id, libro, cantidad, precio_unitario, fecha, nota)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (cliente_id, materia, int(cantidad), precio[0], fecha, nota))

    conn.commit()
    conn.close()


# Guardar devolución
def guardar_devolucion(cliente_id, fecha, materia, cantidad):
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute("""
        INSERT INTO devoluciones (cliente_id, libro, cantidad, fecha)
        VALUES (?, ?, ?, ?)
    """, (cliente_id, materia, cantidad, fecha))
    conn.commit()
    conn.close()

# Guardar abono
def guardar_abono(cliente_id, fecha, monto, comentario, comprobante=None):
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute("""
        INSERT INTO abonos (cliente_id, monto, fecha, comentario, comprobante)
        VALUES (?, ?, ?, ?, ?)
    """, (cliente_id, monto, fecha, comentario, comprobante))
    conn.commit()
    conn.close()

# Generar PDF de estado de cuenta
def generar_estado_cuenta_pdf(cliente, entregas, devoluciones, abonos):
    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter

    p.setFont("Helvetica-Bold", 14)
    p.drawString(50, height - 50, f"Estado de Cuenta - Cliente: {cliente[1]}")
    p.setFont("Helvetica", 12)

    y = height - 80
    p.drawString(50, y, f"ID Cliente: {cliente[0]}")
    y -= 30

    p.setFont("Helvetica-Bold", 12)
    p.drawString(50, y, "Entregas:")
    y -= 20
    total_entregado = 0
    for e in entregas:
        libro = e[1]
        cantidad = int(e[2])
        precio = float(e[3])
        fecha = e[4]
        nota = e[5] if e[5] else "Sin Nota"
        subtotal = cantidad * precio
        total_entregado += subtotal

        linea = f"Nota {nota} - {fecha} - {libro}: {cantidad} x ${precio:.2f} = ${subtotal:.2f}"
        p.setFont("Helvetica", 10)
        p.drawString(60, y, linea)
        y -= 15


    y -= 15
    p.setFont("Helvetica-Bold", 10)
    p.drawString(50, y, "Devoluciones:")
    y -= 20
    total_devoluciones = 0
    for d in devoluciones:
        total_devoluciones += d[3]
        p.drawString(60, y, f"{d[4]} - {d[2]}: {d[3]}")
        y -= 15

    y -= 15
    p.setFont("Helvetica-Bold", 10)
    p.drawString(50, y, "Abonos:")
    y -= 20
    total_abonos = 0
    for a in abonos:
        total_abonos += a[2]
        p.drawString(60, y, f"{a[3]} - ${a[2]:.2f} - {a[4]}")
        y -= 15

    y -= 25
    p.setFont("Helvetica-Bold", 10)
    total_deuda = total_entregado - total_devoluciones - total_abonos
    p.drawString(50, y, f"TOTAL ENTREGADO: ${total_entregado:.2f}")
    y -= 20
    p.drawString(50, y, f"TOTAL DEVOLUCIONES: ${total_devoluciones:.2f}")
    y -= 20
    p.drawString(50, y, f"TOTAL ABONOS: ${total_abonos:.2f}")
    y -= 20
    p.drawString(50, y, f"TOTAL DEUDA: ${total_deuda:.2f}")

    p.showPage()
    p.save()

    buffer.seek(0)
    return buffer


def init_db():
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()

    # Tabla de administradores / usuarios
    c.execute("""
        CREATE TABLE IF NOT EXISTS admin (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT,
            email TEXT,
            password TEXT,
            rol TEXT DEFAULT 'usuario'
        )
    """)

    # Tabla de libros
    c.execute("""
        CREATE TABLE IF NOT EXISTS libros (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT,
            precio REAL,
            imagen TEXT
        )
    """)

    # Tabla de clientes
    c.execute("""
        CREATE TABLE IF NOT EXISTS clientes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT,
            foto TEXT
        )
    """)

    # Tabla de ventas (detalle de venta)
    c.execute("""
        CREATE TABLE IF NOT EXISTS ventas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cliente_id INTEGER,
            libro TEXT,
            cantidad INTEGER,
            precio_unitario REAL,
            fecha TEXT,
            FOREIGN KEY (cliente_id) REFERENCES clientes(id)
        )
    """)

    # Tabla de abonos
    c.execute("""
        CREATE TABLE IF NOT EXISTS abonos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cliente_id INTEGER,
            monto REAL,
            fecha TEXT,
            comentario TEXT,
            FOREIGN KEY (cliente_id) REFERENCES clientes(id)
        )
    """)

    # Tabla de devoluciones
    c.execute("""
        CREATE TABLE IF NOT EXISTS devoluciones (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cliente_id INTEGER,
            libro TEXT,
            cantidad INTEGER,
            fecha TEXT,
            FOREIGN KEY (cliente_id) REFERENCES clientes(id)
        )
    """)

    conn.commit()
    conn.close()

@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        conn = sqlite3.connect(DATABASE)
        c = conn.cursor()
        c.execute("SELECT * FROM admin WHERE email=? AND password=?", (email, password))
        user = c.fetchone()
        conn.close()
        if user:
            session['admin'] = user[1]
            session['rol'] = user[4]  # columna 4 = rol

            if user[4] == 'admin':
                return redirect(url_for('dashboard'))
            else:
                return redirect(url_for('dashboard_usuario'))

        else:
            flash("Credenciales incorrectas", "danger")
    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    if 'admin' not in session:
        return redirect(url_for('login'))
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute("SELECT * FROM libros")
    libros = c.fetchall()
    conn.close()
    return render_template('dashboard.html', libros=libros)

@app.route('/agregar_libro', methods=['POST'])
def agregar_libro():
    if 'admin' not in session:
        return redirect(url_for('login'))
    nombre = request.form['nombre']
    precio = float(request.form['precio'])
    imagen = request.files['imagen']
    filename = secure_filename(imagen.filename)
    imagen.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute("INSERT INTO libros (nombre, precio, imagen) VALUES (?, ?, ?)", (nombre, precio, filename))
    conn.commit()
    conn.close()
    return redirect(url_for('dashboard'))

@app.route('/libros')
def vista_libros():
    if 'admin' not in session:
        return redirect(url_for('login'))
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute("SELECT * FROM libros")
    libros = c.fetchall()
    conn.close()
    return render_template('libros.html', libros=libros)

@app.route('/usuarios')
def vista_usuarios():
    if 'admin' not in session:
        return redirect(url_for('login'))
    return render_template('usuarios.html')

@app.route('/registrar_usuario', methods=['POST'])
def registrar_usuario():
    if 'admin' not in session:
        return redirect(url_for('login'))

    nombre = request.form['nombre']
    email = request.form['email']
    password = request.form['password']

    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute("INSERT INTO admin (nombre, email, password) VALUES (?, ?, ?)", (nombre, email, password))
    conn.commit()
    conn.close()

    return redirect(url_for('dashboard'))

@app.route('/dashboard_usuario')
def dashboard_usuario():
    if 'admin' not in session or session.get('rol') != 'usuario':
        return redirect(url_for('login'))

    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute("SELECT * FROM libros")
    libros = c.fetchall()
    conn.close()
    return render_template('dashboard_usuario.html', libros=libros)

@app.route('/clientes')
def clientes():
    if 'admin' not in session or session.get('rol') != 'usuario':
        return redirect(url_for('login'))

    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute("SELECT * FROM clientes")
    clientes = c.fetchall()
    conn.close()
    return render_template('clientes.html', clientes=clientes)

@app.route('/agregar_cliente', methods=['POST'])
def agregar_cliente():
    if 'admin' not in session or session.get('rol') != 'usuario':
        return redirect(url_for('login'))

    nombre = request.form['nombre']
    foto_file = request.files.get('foto')
    foto_nombre = None

    if foto_file and foto_file.filename != '':
        from werkzeug.utils import secure_filename
        foto_nombre = secure_filename(foto_file.filename)
        foto_file.save(os.path.join('static/images', foto_nombre))

    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute("INSERT INTO clientes (nombre, foto) VALUES (?, ?)", (nombre, foto_nombre))
    conn.commit()
    conn.close()
    return redirect(url_for('clientes'))


@app.route('/ver_cliente/<int:cliente_id>')
def ver_cliente(cliente_id):
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute("SELECT * FROM clientes WHERE id = ?", (cliente_id,))
    cliente = c.fetchone()
    conn.close()

    if not cliente:
        flash("Cliente no encontrado", "danger")
        return redirect(url_for('clientes'))

    # Obtener movimientos financieros
    entregas = obtener_entregas(cliente_id)
    devoluciones = obtener_devoluciones(cliente_id)
    abonos = obtener_abonos(cliente_id)

    # DEBUG: Verifica el contenido de entregas
    print("▶️ ENTREGAS:")
    for e in entregas:
        print("Registro:", e)

    # Calcular totales con índices correctos
    try:
        total_entregado = sum(float(e[2]) * float(e[3]) for e in entregas)
    except Exception as ex:
        print("❌ Error al calcular total_entregado:", ex)
        total_entregado = 0.0

    try:
        total_devoluciones = sum(float(d[3]) * float(precio_del_libro(d[2])) for d in devoluciones)

    except Exception as ex:
        print("❌ Error al calcular total_devoluciones:", ex)
        total_devoluciones = 0.0


    try:
        total_abonos = sum(float(a[2]) for a in abonos)
    except:
        total_abonos = 0.0

    total_deuda = total_entregado - total_devoluciones - total_abonos

    return render_template(
        'ver_cliente.html',
        cliente=cliente,
        entregas=entregas,
        devoluciones=devoluciones,
        abonos=abonos,
        total_entregado=round(total_entregado, 2),
        total_devoluciones=round(total_devoluciones, 2),
        total_abonos=round(total_abonos, 2),
        total_deuda=round(total_deuda, 2)
    )


@app.route('/eliminar_cliente/<int:cliente_id>', methods=['POST'])
def eliminar_cliente(cliente_id):
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute("DELETE FROM clientes WHERE id = ?", (cliente_id,))
    conn.commit()
    conn.close()
    flash("Cliente eliminado", "success")
    return redirect(url_for('clientes'))

@app.route('/cliente/<int:cliente_id>/agregar_entrega', methods=['POST'])
def agregar_entrega(cliente_id):
    fecha = request.form['fecha']
    nota = request.form['nota']
    materias = request.form.getlist('materias[]')  # lista de materias
    cantidades = request.form.getlist('cantidades[]')  # lista de cantidades
    guardar_entrega(cliente_id, fecha, nota, materias, cantidades)
    return redirect(url_for('ver_cliente', cliente_id=cliente_id))

@app.route('/cliente/<int:cliente_id>/agregar_devolucion', methods=['POST'])
def agregar_devolucion(cliente_id):
    fecha = request.form['fecha']
    materias = request.form.getlist('materias[]')
    cantidades = request.form.getlist('cantidades[]')

    for materia, cantidad in zip(materias, cantidades):
        if materia and int(cantidad) > 0:
            guardar_devolucion(cliente_id, fecha, materia, int(cantidad))

    return redirect(url_for('ver_cliente', cliente_id=cliente_id))

@app.route('/cliente/<int:cliente_id>/agregar_abono', methods=['POST'])
def agregar_abono(cliente_id):
    fecha = request.form['fecha']
    valor = float(request.form['valor'])
    referencia = request.form['referencia']
    
    archivo = request.files.get('comprobante')
    nombre_archivo = None

    if archivo and archivo.filename:
        from werkzeug.utils import secure_filename
        nombre_archivo = secure_filename(archivo.filename)
        archivo.save(os.path.join('static/comprobantes', nombre_archivo))

    # Guarda el abono incluyendo el nombre del archivo
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute("""
        INSERT INTO abonos (cliente_id, monto, fecha, comentario, comprobante)
        VALUES (?, ?, ?, ?, ?)
    """, (cliente_id, valor, fecha, referencia, nombre_archivo))
    conn.commit()
    conn.close()

    return redirect(url_for('ver_cliente', cliente_id=cliente_id))


@app.route('/cliente/<int:cliente_id>/descargar_pdf')
def descargar_pdf(cliente_id):
    cliente = obtener_cliente(cliente_id)
    entregas = obtener_entregas(cliente_id)
    devoluciones = obtener_devoluciones(cliente_id)
    abonos = obtener_abonos(cliente_id)
    pdf = generar_estado_cuenta_pdf(cliente, entregas, devoluciones, abonos)
    return send_file(pdf, download_name=f'estado_cuenta_{cliente[1]}.pdf', as_attachment=True)

@app.route('/cliente/<int:cliente_id>/eliminar_nota', methods=['POST'])
def eliminar_nota(cliente_id):
    nota = request.form['nota']
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute("DELETE FROM ventas WHERE cliente_id = ? AND nota = ?", (cliente_id, nota))
    conn.commit()
    conn.close()
    flash("Nota eliminada correctamente", "success")
    return redirect(url_for('ver_entregas', cliente_id=cliente_id))

@app.route('/cliente/<int:cliente_id>/eliminar_nota_devolucion', methods=['POST'])
def eliminar_nota_devolucion(cliente_id):
    nota = request.form['nota']

    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute("DELETE FROM devoluciones WHERE cliente_id = ? AND fecha = ?", (cliente_id, nota))
    conn.commit()
    conn.close()

    flash("Devolución eliminada correctamente", "success")
    return redirect(url_for('ver_devoluciones', cliente_id=cliente_id))

@app.route('/cliente/<int:cliente_id>/eliminar_comprobante/<int:abono_id>', methods=['POST'])
def eliminar_comprobante(cliente_id, abono_id):
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()

    # Obtener nombre del archivo
    c.execute("SELECT comprobante FROM abonos WHERE id = ?", (abono_id,))
    resultado = c.fetchone()
    if resultado and resultado[0]:
        archivo_path = os.path.join('static/comprobantes', resultado[0])
        if os.path.exists(archivo_path):
            os.remove(archivo_path)

    # Borrar referencia al archivo en la base de datos
    c.execute("UPDATE abonos SET comprobante = NULL WHERE id = ?", (abono_id,))
    conn.commit()
    conn.close()

    flash("Comprobante eliminado correctamente", "success")
    return redirect(url_for('ver_abonos', cliente_id=cliente_id))

@app.route('/cliente/<int:cliente_id>/eliminar_abono/<int:abono_id>', methods=['POST'])
def eliminar_abono(cliente_id, abono_id):
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()

    # Obtener comprobante para eliminar archivo
    c.execute("SELECT comprobante FROM abonos WHERE id = ?", (abono_id,))
    resultado = c.fetchone()
    if resultado and resultado[0]:
        archivo_path = os.path.join('static/comprobantes', resultado[0])
        if os.path.exists(archivo_path):
            os.remove(archivo_path)

    # Eliminar el abono completo
    c.execute("DELETE FROM abonos WHERE id = ?", (abono_id,))
    conn.commit()
    conn.close()

    flash("Abono eliminado correctamente", "success")
    return redirect(url_for('ver_abonos', cliente_id=cliente_id))


@app.route('/logout')
def logout():
    session.pop('admin', None)
    return redirect(url_for('login'))

@app.route('/cliente/<int:cliente_id>/entregas')
def ver_entregas(cliente_id):
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()

    # Obtener cliente
    c.execute("SELECT * FROM clientes WHERE id = ?", (cliente_id,))
    cliente = c.fetchone()

    # Obtener entregas agrupadas
    c.execute("""
        SELECT fecha, nota, libro, SUM(cantidad) as cantidad
        FROM ventas
        WHERE cliente_id = ?
        GROUP BY fecha, nota, libro
        ORDER BY fecha DESC
    """, (cliente_id,))
    entregas = c.fetchall()

    # Obtener lista de libros
    c.execute("SELECT * FROM libros")
    libros = c.fetchall()

    # Calcular totales por materia
    totales = {}
    total_general = 0.0
    for libro in libros:
        nombre = libro[1]
        precio = libro[2]
        cantidad_total = sum(e[3] for e in entregas if e[2] == nombre)
        totales[nombre] = {'cantidad': cantidad_total}
        total_general += cantidad_total * precio

    # Agrupar por nota
    detalle_notas = {}
    for entrega in entregas:
        fecha, nota, materia, cantidad = entrega
        nota = nota if nota else 'Sin Nota'

        if nota not in detalle_notas:
            detalle_notas[nota] = {
                'fecha': fecha,
                'materias': {}
            }

        if materia in detalle_notas[nota]['materias']:
            detalle_notas[nota]['materias'][materia] += cantidad
        else:
            detalle_notas[nota]['materias'][materia] = cantidad

    conn.close()

    return render_template(
        'ver_entregas.html',
        cliente=cliente,
        entregas=entregas,
        libros=libros,
        totales=totales,
        total_general=total_general,
        detalle_notas=detalle_notas
    )


    cliente = obtener_cliente(cliente_id)
    devoluciones = obtener_devoluciones(cliente_id)
    return render_template('ver_devoluciones.html', cliente=cliente, devoluciones=devoluciones)

@app.route('/cliente/<int:cliente_id>/devoluciones')
def ver_devoluciones(cliente_id):
    cliente = obtener_cliente(cliente_id)
    devoluciones = obtener_devoluciones(cliente_id)

    # Obtener lista de libros
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute("SELECT * FROM libros")
    libros = c.fetchall()
    conn.close()

    # Total general
    total_general = 0.0

    # Calcular totales por libro
    totales = {}
    for libro in libros:
        nombre = libro[1]
        precio = libro[2]
        cantidad_total = sum(d[3] for d in devoluciones if d[2] == nombre)
        totales[nombre] = {'cantidad': cantidad_total}
        total_general += cantidad_total * precio

    # Agrupar devoluciones por fecha
    detalle_notas = {}
    for d in devoluciones:
        fecha = d[4]  # fecha
        libro = d[2]  # nombre del libro
        cantidad = d[3]

        if fecha not in detalle_notas:
            detalle_notas[fecha] = {}

        if libro in detalle_notas[fecha]:
            detalle_notas[fecha][libro] += cantidad
        else:
            detalle_notas[fecha][libro] = cantidad

    return render_template(
        'ver_devoluciones.html',
        cliente=cliente,
        devoluciones=devoluciones,
        libros=libros,
        total_general=total_general,
        detalle_notas=detalle_notas,
        totales=totales
    )


@app.route('/cliente/<int:cliente_id>/abonos')
def ver_abonos(cliente_id):
    cliente = obtener_cliente(cliente_id)
    abonos = obtener_abonos(cliente_id)
    return render_template('ver_abonos.html', cliente=cliente, abonos=abonos)

def precio_del_libro(nombre_libro):
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute("SELECT precio FROM libros WHERE nombre = ?", (nombre_libro,))
    resultado = c.fetchone()
    conn.close()
    return resultado[0] if resultado else 0.0


@app.route('/proveedores')
def vista_proveedores():
    conn = sqlite3.connect(DATABASE)  # ✅ Uso correcto de la base de datos principal
    c = conn.cursor()
    c.execute("SELECT * FROM proveedores")
    proveedores = c.fetchall()
    conn.close()
    return render_template('proveedores.html', proveedores=proveedores)


@app.route('/agregar_proveedor', methods=['POST'])
def agregar_proveedor():
    if 'admin' not in session:
        return redirect(url_for('login'))

    nombre = request.form['nombre']
    contacto = request.form['contacto']
    telefono = request.form['telefono']
    direccion = request.form['direccion']

    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute("INSERT INTO proveedores (nombre, contacto, telefono, direccion) VALUES (?, ?, ?, ?)",
              (nombre, contacto, telefono, direccion))
    conn.commit()
    conn.close()

    flash("Proveedor agregado correctamente", "success")
    return redirect(url_for('vista_proveedores'))

@app.route('/proveedor/<int:proveedor_id>')
def detalle_proveedor(proveedor_id):
    if 'admin' not in session:
        return redirect(url_for('login'))

    conn = sqlite3.connect('database/editorial.db')
    c = conn.cursor()

    # Obtener datos del proveedor
    c.execute("SELECT * FROM proveedores WHERE id = ?", (proveedor_id,))
    proveedor = c.fetchone()

    # Obtener deudas del proveedor
    c.execute("SELECT fecha, valor, descripcion FROM deudas_proveedor WHERE proveedor_id = ?", (proveedor_id,))
    deudas = c.fetchall()

    # Obtener abonos realizados
    c.execute("SELECT fecha, valor, descripcion FROM abonos_proveedor WHERE proveedor_id = ?", (proveedor_id,))
    abonos = c.fetchall()

    # Calcular resumen
    total_deuda = sum([d[1] for d in deudas])
    total_abonos = sum([a[1] for a in abonos])
    saldo_pendiente = total_deuda - total_abonos

    conn.close()

    return render_template("detalle_proveedor.html", proveedor=proveedor, deudas=deudas, abonos=abonos,
                           total_deuda=total_deuda, total_abonos=total_abonos, saldo_pendiente=saldo_pendiente)

@app.route('/proveedor/<int:proveedor_id>/agregar_deuda', methods=['POST'])
def agregar_deuda_proveedor(proveedor_id):
    fecha = request.form['fecha']
    valor = float(request.form['valor'])
    descripcion = request.form['descripcion']

    conn = sqlite3.connect('database/editorial.db')
    c = conn.cursor()
    c.execute("INSERT INTO deudas_proveedor (proveedor_id, fecha, valor, descripcion) VALUES (?, ?, ?, ?)",
              (proveedor_id, fecha, valor, descripcion))
    conn.commit()
    conn.close()

    flash("Deuda agregada correctamente", "success")
    return redirect(url_for('detalle_proveedor', proveedor_id=proveedor_id))

@app.route('/proveedor/<int:proveedor_id>/agregar_abono', methods=['POST'])
def agregar_abono_proveedor(proveedor_id):
    fecha = request.form['fecha']
    valor = float(request.form['valor'])
    descripcion = request.form['descripcion']

    conn = sqlite3.connect('database/editorial.db')
    c = conn.cursor()
    c.execute("INSERT INTO abonos_proveedor (proveedor_id, fecha, valor, descripcion) VALUES (?, ?, ?, ?)",
              (proveedor_id, fecha, valor, descripcion))
    conn.commit()
    conn.close()

    flash("Abono registrado correctamente", "success")
    return redirect(url_for('detalle_proveedor', proveedor_id=proveedor_id))

@app.route('/eliminar_proveedor/<int:proveedor_id>', methods=['POST'])
def eliminar_proveedor(proveedor_id):
    conn = sqlite3.connect('database/editorial.db')
    c = conn.cursor()
    c.execute("DELETE FROM proveedores WHERE id=?", (proveedor_id,))
    conn.commit()
    conn.close()
    flash("Proveedor eliminado exitosamente", "success")
    return redirect(url_for('vista_proveedores'))


if __name__ == '__main__':
    os.makedirs('database', exist_ok=True)
    os.makedirs('static/images', exist_ok=True)
    os.makedirs('templates', exist_ok=True)
    init_db()

    # Crear usuario administrador por defecto
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute("SELECT * FROM admin WHERE email = 'admin@editorial.com'")
    if not c.fetchone():
        c.execute("INSERT INTO admin (nombre, email, password, rol) VALUES (?, ?, ?, ?)", 
          ('Admin', 'admin@editorial.com', 'Vero69', 'admin'))

        conn.commit()
    conn.close()

    app.run(debug=True)
