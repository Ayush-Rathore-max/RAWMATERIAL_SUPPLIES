from flask import Flask, render_template, request, jsonify, session
import sqlite3
import os
import json
import urllib.parse

app = Flask(__name__)
app.secret_key = 'rawmaterials-secret-key-change-this'

DB_PATH = 'store.db'

WHATSAPP_NUMBER = '917838133167'  # Priya didi's number

# ── DATABASE SETUP ──
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    c = conn.cursor()

    c.execute('''
        CREATE TABLE IF NOT EXISTS products (
            id       INTEGER PRIMARY KEY AUTOINCREMENT,
            name     TEXT NOT NULL,
            category TEXT NOT NULL,
            price    INTEGER NOT NULL,
            emoji    TEXT DEFAULT '🧶',
            color    TEXT DEFAULT '#f9c4d2',
            stock    INTEGER DEFAULT 100
        )
    ''')

    c.execute('''
        CREATE TABLE IF NOT EXISTS orders (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            name       TEXT NOT NULL,
            phone      TEXT NOT NULL,
            address    TEXT NOT NULL,
            total      INTEGER NOT NULL,
            items_json TEXT NOT NULL,
            status     TEXT DEFAULT 'Pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    c.execute('SELECT COUNT(*) FROM products')
    if c.fetchone()[0] == 0:
        sample_products = [
            ('Glass Beads',       'Beads',         10,  '📿', '#f9c4d2'),
            ('Pipe Cleaners',     'Pipe Cleaners', 5,   '🌈', '#c4e4f9'),
            ('Small Lock',        'Locks',         15,  '🔒', '#f9e4c4'),
            ('Earring Hooks',     'Earrings',      8,   '💎', '#e4c4f9'),
            ('Jump Rings',        'Charms',        5,   '⭕', '#c4f9e4'),
            ('Crystal Beads',     'Beads',         20,  '✨', '#f9f4c4'),
        ]
        c.executemany(
            'INSERT INTO products (name, category, price, emoji, color) VALUES (?,?,?,?,?)',
            sample_products
        )

    conn.commit()
    conn.close()

def generate_whatsapp_message(order_id, name, phone, address, items, total):
    lines = []
    lines.append(f"🛍️ *New Order Received!*")
    lines.append(f"━━━━━━━━━━━━━━━━━━")
    lines.append(f"📋 *Order ID:* #{order_id}")
    lines.append(f"👤 *Customer Name:* {name}")
    lines.append(f"📞 *Phone:* {phone}")
    lines.append(f"📍 *Address:* {address}")
    lines.append(f"━━━━━━━━━━━━━━━━━━")
    lines.append(f"🛒 *Items Ordered:*")
    for item in items:
        lines.append(f"  • {item['name']} x{item['qty']} = ₹{item['price'] * item['qty']}")
    lines.append(f"━━━━━━━━━━━━━━━━━━")
    lines.append(f"💰 *Total Amount: ₹{total}*")
    lines.append(f"⚠️ Minimum order ₹300 | No COD/Return/Exchange")
    return "\n".join(lines)

# ── ROUTES ──

@app.route('/')
def home():
    conn = get_db()
    products = conn.execute('SELECT * FROM products').fetchall()
    conn.close()
    return render_template('index.html', products=products)


@app.route('/api/products')
def api_products():
    category = request.args.get('category')
    conn = get_db()
    if category:
        products = conn.execute(
            'SELECT * FROM products WHERE category = ?', (category,)
        ).fetchall()
    else:
        products = conn.execute('SELECT * FROM products').fetchall()
    conn.close()
    result = []
    for p in products:
        d = dict(p)
        d["bg"] = d.get("color", "#f9c4d2")
        result.append(d)
    return jsonify(result)


@app.route('/api/order', methods=['POST'])
def place_order():
    data    = request.get_json()
    name    = data.get('name', '').strip()
    phone   = data.get('phone', '').strip()
    address = data.get('address', '').strip()
    items   = data.get('items', [])
    total   = data.get('total', 0)

    if not name or not phone or not address or not items:
        return jsonify({'success': False, 'error': 'Please fill all fields!'}), 400

    if total < 300:
        return jsonify({'success': False, 'error': 'Minimum order amount is ₹300!'}), 400

    items_json = json.dumps(items)

    conn = get_db()
    conn.execute(
        'INSERT INTO orders (name, phone, address, total, items_json) VALUES (?,?,?,?,?)',
        (name, phone, address, total, items_json)
    )
    conn.commit()
    order_id = conn.execute('SELECT last_insert_rowid()').fetchone()[0]
    conn.close()

    # Generate WhatsApp link
    message = generate_whatsapp_message(order_id, name, phone, address, items, total)
    encoded_message = urllib.parse.quote(message)
    whatsapp_url = f"https://wa.me/{WHATSAPP_NUMBER}?text={encoded_message}"

    return jsonify({
        'success': True,
        'order_id': order_id,
        'whatsapp_url': whatsapp_url,
        'message': f'Order #{order_id} placed successfully!'
    })


@app.route('/admin')
def admin():
    conn = get_db()
    products = conn.execute('SELECT * FROM products').fetchall()
    orders   = conn.execute('SELECT * FROM orders ORDER BY created_at DESC').fetchall()
    conn.close()
    return render_template('admin.html', products=products, orders=orders)


@app.route('/admin/add-product', methods=['POST'])
def add_product():
    name     = request.form.get('name')
    category = request.form.get('category')
    price    = request.form.get('price')
    emoji    = request.form.get('emoji', '🧶')
    color    = request.form.get('color', '#f9c4d2')
    conn = get_db()
    conn.execute(
        'INSERT INTO products (name, category, price, emoji, color) VALUES (?,?,?,?,?)',
        (name, category, int(price), emoji, color)
    )
    conn.commit()
    conn.close()
    return jsonify({'success': True, 'message': 'Product added successfully!'})


@app.route('/admin/delete-product/<int:pid>', methods=['DELETE'])
def delete_product(pid):
    conn = get_db()
    conn.execute('DELETE FROM products WHERE id = ?', (pid,))
    conn.commit()
    conn.close()
    return jsonify({'success': True, 'message': 'Product deleted successfully!'})


@app.route('/admin/update-order-status/<int:oid>', methods=['POST'])
def update_order_status(oid):
    data   = request.get_json()
    status = data.get('status', 'Pending')
    conn = get_db()
    conn.execute('UPDATE orders SET status = ? WHERE id = ?', (status, oid))
    conn.commit()
    conn.close()
    return jsonify({'success': True, 'message': 'Order status updated!'})


# ── RUN ──
if __name__ == '__main__':
    init_db()
    print("✅ Database ready!")
    print("🚀 Server running at: http://127.0.0.1:5000")
    print("📦 Admin panel: http://127.0.0.1:5000/admin")
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))