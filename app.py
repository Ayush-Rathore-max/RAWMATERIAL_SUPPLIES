from flask import Flask, render_template, request, jsonify, session, redirect
import sqlite3
import os
import json
import urllib.parse
from werkzeug.utils import secure_filename
import uuid

UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

app = Flask(__name__)
app.secret_key = 'rawmaterials-secret-key-change-this'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max

# Create upload folder
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

DB_PATH = 'store.db'
WHATSAPP_NUMBER = '917838133167'

ADMIN_USERNAME = 'Ayush'
ADMIN_PASSWORD = '@yush@2006'

# ── DATABASE ──
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    c = conn.cursor()

    # Categories table
    c.execute('''CREATE TABLE IF NOT EXISTS categories (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE
    )''')

    # Products table — with images, variants, description, mrp, stock
    c.execute('''CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        category TEXT NOT NULL,
        price INTEGER NOT NULL,
        mrp INTEGER DEFAULT 0,
        emoji TEXT DEFAULT "🌸",
        color TEXT DEFAULT "#fce7f3",
        description TEXT DEFAULT "",
        images TEXT DEFAULT "[]",
        variants TEXT DEFAULT "[]",
        stock INTEGER DEFAULT 100,
        shipping_days TEXT DEFAULT "3-4 days",
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')

    # Orders table
    c.execute('''CREATE TABLE IF NOT EXISTS orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        phone TEXT NOT NULL,
        address TEXT NOT NULL,
        total INTEGER NOT NULL,
        items_json TEXT NOT NULL,
        status TEXT DEFAULT "Pending",
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')

    # Reviews table
    c.execute('''CREATE TABLE IF NOT EXISTS reviews (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        product_id INTEGER,
        reviewer_name TEXT NOT NULL,
        rating INTEGER NOT NULL,
        review_text TEXT DEFAULT "",
        image_url TEXT DEFAULT "",
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')

    # Default categories
    default_cats = ['Charms', 'Beads', 'Locks', 'Earrings', 'Pipe Cleaners', 'Glass Beads']
    for cat in default_cats:
        try:
            c.execute('INSERT INTO categories (name) VALUES (?)', (cat,))
        except:
            pass

    # Sample products

    # ── MIGRATE: add new columns if missing ──
    existing = [row[1] for row in c.execute("PRAGMA table_info(products)").fetchall()]
    migrations = {
        'mrp':           'ALTER TABLE products ADD COLUMN mrp INTEGER DEFAULT 0',
        'images':        "ALTER TABLE products ADD COLUMN images TEXT DEFAULT '[]'",
        'variants':      "ALTER TABLE products ADD COLUMN variants TEXT DEFAULT '[]'",
        'description':   "ALTER TABLE products ADD COLUMN description TEXT DEFAULT ''",
        'shipping_days': "ALTER TABLE products ADD COLUMN shipping_days TEXT DEFAULT '3-4 days'",
    }
    for col, sql in migrations.items():
        if col not in existing:
            c.execute(sql)

    c.execute('SELECT COUNT(*) FROM products')
    if c.fetchone()[0] == 0:
        sample = [
            ('Mini Headphone Charms', 'Charms', 10, 15, '🎧', '#fef3c7',
             '10rs each - cute mini charms for jewellery making',
             '[]', '[{"label":"1pc","price":10},{"label":"10pcs","price":80}]', 50, '3-4 days'),
            ('Crystal Strawberry', 'Charms', 45, 60, '🍓', '#fce7f3',
             'Beautiful crystal strawberry charms',
             '[]', '[{"label":"1pc","price":45},{"label":"10pcs","price":400}]', 30, '3-4 days'),
            ('Glass Seed Beads', 'Glass Beads', 29, 40, '💎', '#ede9fe',
             'Mixed colour glass seed beads',
             '[]', '[{"label":"1 pack","price":29},{"label":"5 packs","price":130}]', 80, '3-4 days'),
            ('Heart Lock Set', 'Locks', 49, 65, '🔒', '#fce7f3',
             'Cute heart shaped locks for bags & pouches',
             '[]', '[{"label":"1pc","price":49},{"label":"5pcs","price":220}]', 40, '3-4 days'),
        ]
        c.executemany('''INSERT INTO products
            (name, category, price, mrp, emoji, color, description, images, variants, stock, shipping_days)
            VALUES (?,?,?,?,?,?,?,?,?,?,?)''', sample)

    conn.commit()
    conn.close()

def generate_whatsapp_message(order_id, name, phone, address, items, total):
    lines = [
        f"🛍️ *New Order!*",
        f"━━━━━━━━━━━━━━",
        f"📋 *Order:* #{order_id}",
        f"👤 *Name:* {name}",
        f"📞 *Phone:* {phone}",
        f"📍 *Address:* {address}",
        f"━━━━━━━━━━━━━━",
        f"🛒 *Items:*"
    ]
    for item in items:
        variant = f" ({item.get('variant','')})" if item.get('variant') else ''
        lines.append(f"  • {item['name']}{variant} x{item['qty']} = ₹{item['price']*item['qty']}")
    lines.append(f"━━━━━━━━━━━━━━")
    lines.append(f"💰 *Total: ₹{total}*")
    lines.append(f"⚠️ Min order ₹300 | No COD/Return")
    return "\n".join(lines)

# ── FILE UPLOAD ──
@app.route('/api/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'success': False, 'error': 'No file'}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({'success': False, 'error': 'No file selected'}), 400
    if file and allowed_file(file.filename):
        ext = file.filename.rsplit('.', 1)[1].lower()
        filename = str(uuid.uuid4()) + '.' + ext
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        url = '/static/uploads/' + filename
        return jsonify({'success': True, 'url': url})
    return jsonify({'success': False, 'error': 'File type not allowed'}), 400

# ── AUTH ──
@app.route('/admin/login', methods=['GET','POST'])
def admin_login():
    if session.get('admin_logged_in'):
        return redirect('/admin')
    if request.method == 'POST':
        u = request.form.get('username','').strip()
        p = request.form.get('password','').strip()
        if u == ADMIN_USERNAME and p == ADMIN_PASSWORD:
            session['admin_logged_in'] = True
            return redirect('/admin')
        return render_template('admin_login.html', error='❌ Wrong username or password!')
    return render_template('admin_login.html', error=None)

@app.route('/admin/logout')
def admin_logout():
    session.pop('admin_logged_in', None)
    return redirect('/admin/login')

# ── MAIN ROUTES ──
@app.route('/')
def home():
    conn = get_db()
    products = conn.execute('SELECT * FROM products').fetchall()
    categories = conn.execute('SELECT * FROM categories ORDER BY name').fetchall()
    conn.close()
    return render_template('index.html', products=products, categories=categories)

@app.route('/product/<int:pid>')
def product_detail(pid):
    conn = get_db()
    product = conn.execute('SELECT * FROM products WHERE id=?', (pid,)).fetchone()
    reviews = conn.execute('SELECT * FROM reviews WHERE product_id=? ORDER BY created_at DESC', (pid,)).fetchall()
    conn.close()
    if not product:
        return redirect('/')
    return render_template('product.html', product=dict(product), reviews=reviews)

@app.route('/api/products')
def api_products():
    category = request.args.get('category')
    conn = get_db()
    if category and category != 'all':
        products = conn.execute('SELECT * FROM products WHERE category=?', (category,)).fetchall()
    else:
        products = conn.execute('SELECT * FROM products').fetchall()
    conn.close()
    result = []
    for p in products:
        d = dict(p)
        d['images'] = json.loads(d.get('images','[]'))
        d['variants'] = json.loads(d.get('variants','[]'))
        result.append(d)
    return jsonify(result)

@app.route('/api/order', methods=['POST'])
def place_order():
    data = request.get_json()
    name = data.get('name','').strip()
    phone = data.get('phone','').strip()
    address = data.get('address','').strip()
    items = data.get('items',[])
    total = data.get('total',0)

    if not name or not phone or not address or not items:
        return jsonify({'success':False,'error':'Sab fields bharo!'}),400
    if total < 300:
        return jsonify({'success':False,'error':'Minimum order ₹300 hai!'}),400

    conn = get_db()
    conn.execute('INSERT INTO orders (name,phone,address,total,items_json) VALUES (?,?,?,?,?)',
        (name, phone, address, total, json.dumps(items)))
    conn.commit()
    order_id = conn.execute('SELECT last_insert_rowid()').fetchone()[0]
    conn.close()

    message = generate_whatsapp_message(order_id, name, phone, address, items, total)
    wa_url = f"https://wa.me/{WHATSAPP_NUMBER}?text={urllib.parse.quote(message)}"

    return jsonify({'success':True,'order_id':order_id,'whatsapp_url':wa_url})

# ── REVIEWS ──
@app.route('/api/review', methods=['POST'])
def add_review():
    data = request.get_json()
    pid = data.get('product_id')
    name = data.get('name','').strip()
    rating = data.get('rating', 5)
    text = data.get('text','').strip()
    image_url = data.get('image_url','').strip()
    if not name or not pid:
        return jsonify({'success':False,'error':'Invalid data'}),400
    conn = get_db()
    conn.execute('INSERT INTO reviews (product_id,reviewer_name,rating,review_text,image_url) VALUES (?,?,?,?,?)',
        (pid, name, rating, text, image_url))
    conn.commit()
    conn.close()
    return jsonify({'success':True})

@app.route('/api/reviews/<int:pid>')
def get_reviews(pid):
    conn = get_db()
    reviews = conn.execute('SELECT * FROM reviews WHERE product_id=? ORDER BY created_at DESC', (pid,)).fetchall()
    conn.close()
    return jsonify([dict(r) for r in reviews])

# ── ADMIN ──
@app.route('/admin')
def admin():
    if not session.get('admin_logged_in'):
        return redirect('/admin/login')
    conn = get_db()
    products = [dict(p) for p in conn.execute('SELECT * FROM products').fetchall()]
    orders = [dict(o) for o in conn.execute('SELECT * FROM orders ORDER BY created_at DESC').fetchall()]
    categories = [dict(c) for c in conn.execute('SELECT * FROM categories ORDER BY name').fetchall()]
    reviews = [dict(r) for r in conn.execute('SELECT * FROM reviews ORDER BY created_at DESC').fetchall()]
    conn.close()
    return render_template('admin.html', products=products, orders=orders, categories=categories, reviews=reviews)

@app.route('/admin/add-product', methods=['POST'])
def add_product():
    if not session.get('admin_logged_in'):
        return jsonify({'success':False}),401
    name = request.form.get('name','').strip()
    category = request.form.get('category','').strip()
    price = int(request.form.get('price',0))
    mrp = int(request.form.get('mrp',0))
    emoji = request.form.get('emoji','🌸')
    color = request.form.get('color','#fce7f3')
    description = request.form.get('description','').strip()
    images_raw = request.form.get('images','').strip()
    variants_raw = request.form.get('variants','').strip()
    stock = int(request.form.get('stock',100))
    shipping_days = request.form.get('shipping_days','3-4 days').strip()

    # Parse images — comma separated URLs
    images = [x.strip() for x in images_raw.split(',') if x.strip()]

    # Parse variants — "1pc:10,10pcs:80"
    variants = []
    for v in variants_raw.split(','):
        v = v.strip()
        if ':' in v:
            parts = v.split(':')
            try:
                variants.append({'label': parts[0].strip(), 'price': int(parts[1].strip())})
            except:
                pass

    conn = get_db()
    conn.execute('''INSERT INTO products
        (name,category,price,mrp,emoji,color,description,images,variants,stock,shipping_days)
        VALUES (?,?,?,?,?,?,?,?,?,?,?)''',
        (name, category, price, mrp, emoji, color, description,
         json.dumps(images), json.dumps(variants), stock, shipping_days))
    conn.commit()
    conn.close()
    return jsonify({'success':True})

@app.route('/admin/edit-product/<int:pid>', methods=['POST'])
def edit_product(pid):
    if not session.get('admin_logged_in'):
        return jsonify({'success':False}),401
    name = request.form.get('name','').strip()
    category = request.form.get('category','').strip()
    price = int(request.form.get('price',0))
    mrp = int(request.form.get('mrp',0))
    emoji = request.form.get('emoji','🌸')
    color = request.form.get('color','#fce7f3')
    description = request.form.get('description','').strip()
    images_raw = request.form.get('images','').strip()
    variants_raw = request.form.get('variants','').strip()
    stock = int(request.form.get('stock',100))
    shipping_days = request.form.get('shipping_days','3-4 days').strip()

    images = [x.strip() for x in images_raw.split(',') if x.strip()]
    variants = []
    for v in variants_raw.split(','):
        v = v.strip()
        if ':' in v:
            parts = v.split(':')
            try:
                variants.append({'label': parts[0].strip(), 'price': int(parts[1].strip())})
            except:
                pass

    conn = get_db()
    conn.execute('''UPDATE products SET name=?,category=?,price=?,mrp=?,emoji=?,color=?,
        description=?,images=?,variants=?,stock=?,shipping_days=? WHERE id=?''',
        (name, category, price, mrp, emoji, color, description,
         json.dumps(images), json.dumps(variants), stock, shipping_days, pid))
    conn.commit()
    conn.close()
    return jsonify({'success':True})

@app.route('/admin/delete-product/<int:pid>', methods=['DELETE'])
def delete_product(pid):
    if not session.get('admin_logged_in'):
        return jsonify({'success':False}),401
    conn = get_db()
    conn.execute('DELETE FROM products WHERE id=?', (pid,))
    conn.commit()
    conn.close()
    return jsonify({'success':True})

@app.route('/admin/update-order-status/<int:oid>', methods=['POST'])
def update_order_status(oid):
    if not session.get('admin_logged_in'):
        return jsonify({'success':False}),401
    data = request.get_json()
    status = data.get('status','Pending')
    conn = get_db()
    conn.execute('UPDATE orders SET status=? WHERE id=?', (status, oid))
    conn.commit()
    conn.close()
    return jsonify({'success':True})

@app.route('/admin/reset-orders', methods=['POST'])
def reset_orders():
    if not session.get('admin_logged_in'):
        return jsonify({'success':False}),401
    conn = get_db()
    conn.execute('DELETE FROM orders')
    try:
        conn.execute("DELETE FROM sqlite_sequence WHERE name='orders'")
    except:
        pass
    conn.commit()
    conn.close()
    return jsonify({'success':True})

# ── CATEGORIES ──
@app.route('/admin/add-category', methods=['POST'])
def add_category():
    if not session.get('admin_logged_in'):
        return jsonify({'success':False}),401
    name = request.form.get('name','').strip()
    if not name:
        return jsonify({'success':False,'error':'Name required'}),400
    conn = get_db()
    try:
        conn.execute('INSERT INTO categories (name) VALUES (?)', (name,))
        conn.commit()
    except:
        conn.close()
        return jsonify({'success':False,'error':'Category already exists!'})
    conn.close()
    return jsonify({'success':True})

@app.route('/admin/delete-category/<int:cid>', methods=['DELETE'])
def delete_category(cid):
    if not session.get('admin_logged_in'):
        return jsonify({'success':False}),401
    conn = get_db()
    conn.execute('DELETE FROM categories WHERE id=?', (cid,))
    conn.commit()
    conn.close()
    return jsonify({'success':True})

@app.route('/admin/delete-review/<int:rid>', methods=['DELETE'])
def delete_review(rid):
    if not session.get('admin_logged_in'):
        return jsonify({'success':False}),401
    conn = get_db()
    conn.execute('DELETE FROM reviews WHERE id=?', (rid,))
    conn.commit()
    conn.close()
    return jsonify({'success':True})

if __name__ == '__main__':
    init_db()
    print("✅ Database ready!")
    print("🚀 Server: http://127.0.0.1:5000")
    print("🔐 Admin: http://127.0.0.1:5000/admin")
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))