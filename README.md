# DRAPE Fashion Store 🛍️
### Flask + SQLite eCommerce Starter

---

## 📁 Project Structure

```
my-fashion-store/
├── app.py                  ← Main Flask server
├── store.db                ← SQLite database (auto-banta hai)
├── requirements.txt        ← Dependencies
└── templates/
    ├── index.html          ← Customer-facing store
    └── admin.html          ← Admin panel
```

---

## ⚙️ Setup (Step by Step)

### 1. Folder banao aur files daalo
```
my-fashion-store/
├── app.py
└── templates/
    ├── index.html
    └── admin.html
```

### 2. Flask install karo
```bash
pip install flask
```

### 3. Server chalaao
```bash
python app.py
```

### 4. Browser mein open karo
- **Store:**  http://127.0.0.1:5000
- **Admin:**  http://127.0.0.1:5000/admin

---

## ✅ Features

| Feature | Status |
|---|---|
| Product listing (DB se) | ✅ |
| Category filter | ✅ |
| Add to Cart | ✅ |
| Cart drawer | ✅ |
| Checkout form | ✅ |
| Order save in DB | ✅ |
| Admin panel | ✅ |
| Add/Delete products | ✅ |
| Orders dashboard | ✅ |

---

## 🚀 Next Steps (Phase 2)

1. **User Login** → Flask-Login use karo
2. **Images** → Product photos upload karna
3. **Razorpay** → Real payment integration
4. **Deploy** → Render.com pe free hosting

---

Made with ❤️ using Flask + SQLite
