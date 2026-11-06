import sqlite3
from flask import Flask, render_template, request, jsonify, redirect, url_for

app = Flask(__name__)
DB_NAME = "restaurant.db"

def init_db():
    """Sets up database tables and initial sample menu."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    # Menu table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS menu (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            category TEXT NOT NULL,
            price REAL NOT NULL
        )
    ''')

    # Orders table (Estructura original limpia con waiter_name añadido)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            table_number INTEGER NOT NULL,
            waiter_name TEXT,
            item_id INTEGER NOT NULL,
            notes TEXT,
            status TEXT DEFAULT 'Pending', -- Pending, Ready, Paid
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (item_id) REFERENCES menu (id)
        )
    ''')

    # Insert initial sample menu if empty
    cursor.execute("SELECT COUNT(*) FROM menu")
    if cursor.fetchone()[0] == 0:
        sample_items = [
            ('Sopa', 'Sides', 8.00),
            ('Bandeja paisa', 'Mains', 23.00),
            ('Cochino frito', 'Mains', 12.00),
            ('Parrilla para 2', 'Mains', 28.00),
            ('Pollo a la plancha', 'Mains', 12.00),
            ('Gordon blue pollo', 'Mains', 12.00),
            ('Hamburguesa de pollo', 'Mains', 7.00),
            ('Hamburguesa de carne', 'Mains', 7.00),
            ('Pandebonos', 'Mains', 1.00),
            ('Buñuelos', 'Mains', 1.00),
            ('10 Arepas de maiz', 'Mains', 3.00),
            ('Racion de tocineta con tostones', 'Mains', 6.00),
            ('Agua', 'Drinks', 1.00),
            ('Jugos naturales', 'Drinks', 2.50),
            ('Papelon', 'Drinks', 2.00),
            ('Refrescos', 'Drinks', 2.00),
            ('Refrescos pequeño', 'Drinks', 1.50),
            ('Malta', 'Drinks', 1.00),
            ('Cerveza', 'Drinks', 1.00),
            ('Caroreña', 'Drinks', 2.50),
            ('Tiramisu', 'Dessert', 3.00),
            ('Quesillo', 'Dessert', 6.00),
            ('Marqueza', 'Dessert', 3.00),
        ]
        cursor.executemany("INSERT INTO menu (name, category, price) VALUES (?, ?, ?)", sample_items)

    conn.commit()
    conn.close()

# Initialize DB on start
init_db()

# --- ROUTES ---

@app.route('/')
def waiter_page():
    """Waitstaff order taking interface."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM menu")
    menu = cursor.fetchall()
    conn.close()
    return render_template('waiter.html', menu=menu)

@app.route('/submit_order', methods=['POST'])
def submit_order():
    """API endpoint to receive order from waiter UI."""
    data = request.json
    table_num = data.get('table_number')
    items = data.get('items', [])
    
    if not table_num or not items:
        return jsonify({"success": False, "message": "Missing table or items"}), 400

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    for item in items:
        cursor.execute(
            "INSERT INTO orders (table_number, item_id, notes) VALUES (?, ?, ?)",
            (table_num, item['id'], item.get('notes', ''))
        )
    conn.commit()
    conn.close()
    return jsonify({"success": True})

@app.route('/cocina')
def kitchen_page():
    """Kitchen Display System UI."""
    return render_template('cocina.html')

@app.route('/api/kitchen_orders')
def get_kitchen_orders():
    """API endpoint for live kitchen orders."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT orders.id, orders.table_number, menu.name, orders.notes, orders.timestamp 
        FROM orders 
        JOIN menu ON orders.item_id = menu.id 
        WHERE orders.status = 'Pending'
        ORDER BY orders.timestamp ASC
    ''')
    rows = cursor.fetchall()
    conn.close()

    orders = []
    for r in rows:
        orders.append({
            "id": r[0], "table": r[1], "item": r[2], "notes": r[3], "time": r[4]
        })
    return jsonify(orders)

@app.route('/api/complete_order/<int:order_id>', methods=['POST'])
def complete_order(order_id):
    """Marks an item as Ready."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("UPDATE orders SET status = 'Ready' WHERE id = ?", (order_id,))
    conn.commit()
    conn.close()
    return jsonify({"success": True})

@app.route('/cuenta/<int:table_num>')
def bill_page(table_num):
    """Calculates unpaid total for a table."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT menu.name, menu.price, orders.id 
        FROM orders 
        JOIN menu ON orders.item_id = menu.id 
        WHERE orders.table_number = ? AND orders.status != 'Paid'
    ''', (table_num,))
    items = cursor.fetchall()

    total = sum(i[1] for i in items)
    conn.close()
    return render_template('cuenta.html', table=table_num, items=items, total=total)

@app.route('/pay_bill/<int:table>', methods=['POST'])
def pay_bill(table):
    """Actualiza las órdenes de la mesa a 'Paid' y asigna el mesero."""
    waiter_name = request.form.get('waiter_name')

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    # Actualizamos las órdenes pendientes de esta mesa colocándolas como 'Paid' y guardando el mesero
    cursor.execute(
        "UPDATE orders SET status = 'Paid', waiter_name = ? WHERE table_number = ? AND status != 'Paid'",
        (waiter_name, table)
    )
    conn.commit()
    conn.close()

    return redirect(url_for('waiter_page'))

@app.route('/gerente')
def manager_page():
    """Manager Dashboard showing total sales and paid orders history."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute('''
        SELECT SUM(menu.price) 
        FROM orders 
        JOIN menu ON orders.item_id = menu.id 
        WHERE orders.status = 'Paid'
    ''')
    total_sales = cursor.fetchone()[0]
    total_sales = total_sales if total_sales is not None else 0.0

    cursor.execute('''
        SELECT orders.table_number, menu.name, menu.price, orders.timestamp 
        FROM orders 
        JOIN menu ON orders.item_id = menu.id 
        WHERE orders.status = 'Paid'
        ORDER BY orders.timestamp DESC
    ''')
    paid_orders = cursor.fetchall()

    conn.close()
    return render_template('gerente.html', total_sales=total_sales, paid_orders=paid_orders)

@app.route('/reporte-meseros')
def reporte_meseros():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    # Calculamos el total de ventas por mesero sumando el precio de los items pagados por él
    cursor.execute('''
        SELECT orders.waiter_name, SUM(menu.price) as total_ventas, COUNT(orders.id) as total_ordenes 
        FROM orders 
        JOIN menu ON orders.item_id = menu.id
        WHERE orders.status = 'Paid' AND orders.waiter_name IS NOT NULL 
        GROUP BY orders.waiter_name
    ''')
    reporte = cursor.fetchall()
    conn.close()

    return render_template('reporte_meseros.html', reporte=reporte)

if __name__ == '__main__':
    # Borramos la base de datos vieja con errores para que se cree limpia con la estructura correcta
    import os
    if os.path.exists(DB_NAME):
        os.remove(DB_NAME)

    init_db()
    app.run(host='0.0.0.0', port=8080, debug=True)
