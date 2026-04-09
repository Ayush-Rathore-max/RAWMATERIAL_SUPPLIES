from flask import Flask, render_template, request, jsonify, session, redirect, url_for
import sqlite3
import os

app = Flask(__name__)
app.secret_key = 'rawmaterials-secret-2026'

DB_PATH = 'store.db'

# ── ADMIN CREDENTIALS ──
ADMIN_USERNAME = 'Ayush'
ADMIN_PASSWORD = '@yush2006'

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL, category TEXT NOT NULL,
        price INTEGER NOT NULL, emoji TEXT DEFAULT '🌸',
        color TEXT DEFAULT '#fce7f3', stock INTEGER DEFAULT 100)''')
    c.execute('''CREATE TABLE IF NOT EXISTS orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL, phone TEXT NOT NULL,
        address TEXT NOT NULL, total INTEGER NOT NULL,
        items_json TEXT NOT NULL, status TEXT DEFAULT 'Pending',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    c.execute('SELECT COUNT(*) FROM products')
    if c.fetchone()[0] == 0:
        sample = [
            ('Heart Lock Set','Locks',49,'🔒','#fce7f3'),
            ('Glass Seed Beads Mix','Glass Beads',29,'💎','#ede9fe'),
            ('Pipe Cleaners 50pcs','Pipe Cleaners',39,'🎨','#dcfce7'),
            ('Mini Headphone Charms','Charms',19,'🎧','#fef3c7'),
            ('Butterfly Earrings','Earrings',59,'🦋','#fce7f3'),
            ('Pearl Beads 100pcs','Glass Beads',45,'🫧','#e0f2fe'),
        ]
        c.executemany('INSERT INTO products (name,category,price,emoji,color) VALUES (?,?,?,?,?)', sample)
    conn.commit()
    conn.close()

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
        products = conn.execute('SELECT * FROM products WHERE category=?',(category,)).fetchall()
    else:
        products = conn.execute('SELECT * FROM products').fetchall()
    conn.close()
    return jsonify([dict(p) for p in products])

@app.route('/api/order', methods=['POST'])
def place_order():
    import json
    data = request.get_json()
    name = data.get('name','').strip()
    phone = data.get('phone','').strip()
    address = data.get('address','').strip()
    items = data.get('items',[])
    total = data.get('total',0)
    if not name or not phone or not address or not items:
        return jsonify({'success':False,'error':'Sab fields bharo!'}),400
    conn = get_db()
    conn.execute('INSERT INTO orders (name,phone,address,total,items_json) VALUES (?,?,?,?,?)',
        (name,phone,address,total,json.dumps(items)))
    conn.commit()
    order_id = conn.execute('SELECT last_insert_rowid()').fetchone()[0]
    conn.close()
    return jsonify({'success':True,'order_id':order_id})

# ── ADMIN LOGIN ──
@app.route('/admin/login', methods=['GET','POST'])
def admin_login():
    error = None
    if request.method == 'POST':
        u = request.form.get('username','').strip()
        p = request.form.get('password','').strip()
        if u == ADMIN_USERNAME and p == ADMIN_PASSWORD:
            session['admin_logged_in'] = True
            return redirect(url_for('admin'))
        else:
            error = 'Wrong username or password! ❌'
    return render_template('admin_login.html', error=error)

@app.route('/admin/logout')
def admin_logout():
    session.pop('admin_logged_in', None)
    return redirect(url_for('admin_login'))

@app.route('/admin')
def admin():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    conn = get_db()
    products = conn.execute('SELECT * FROM products').fetchall()
    orders = conn.execute('SELECT * FROM orders ORDER BY created_at DESC').fetchall()
    conn.close()
    return render_template('admin.html', products=products, orders=orders)

@app.route('/admin/add-product', methods=['POST'])
def add_product():
    if not session.get('admin_logged_in'):
        return jsonify({'success':False}),401
    name = request.form.get('name')
    category = request.form.get('category')
    price = request.form.get('price')
    emoji = request.form.get('emoji','🌸')
    conn = get_db()
    conn.execute('INSERT INTO products (name,category,price,emoji) VALUES (?,?,?,?)',
        (name,category,int(price),emoji))
    conn.commit()
    conn.close()
    return jsonify({'success':True})

@app.route('/admin/delete-product/<int:pid>', methods=['DELETE'])
def delete_product(pid):
    if not session.get('admin_logged_in'):
        return jsonify({'success':False}),401
    conn = get_db()
    conn.execute('DELETE FROM products WHERE id=?',(pid,))
    conn.commit()
    conn.close()
    return jsonify({'success':True})

@app.route('/admin/update-order/<int:oid>', methods=['POST'])
def update_order(oid):
    if not session.get('admin_logged_in'):
        return jsonify({'success':False}),401
    status = request.form.get('status')
    conn = get_db()
    conn.execute('UPDATE orders SET status=? WHERE id=?',(status,oid))
    conn.commit()
    conn.close()
    return jsonify({'success':True})

if __name__ == '__main__':
    init_db()
    print("✅ Database ready!")
    print("🚀 Server: http://127.0.0.1:5000")
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
