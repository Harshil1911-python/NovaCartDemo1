# 🛍️ Nova Cart — Ecommerce Marketplace

A complete, production-ready multi-seller ecommerce platform built with Python Flask.
Uses **file-based storage** (`data.dat` + JSON) — no SQL database required.

---

## ✨ Features

- 🏪 **Multi-seller marketplace** — sellers register, sell, manage their store
- 🎨 **Full admin customization** — colors, fonts, themes, layout, all from dashboard
- 📦 **Product system** — images, pricing, discounts, stock, categories, reviews
- 🛒 **Cart & checkout** — COD support, address saving, order history
- 🔐 **Secret admin access** — click footer "Nova Cart" 5 times to reveal login
- 📢 **Ads manager** — upload, schedule, place, track ads
- 📄 **Custom page builder** — About, Privacy, Blog pages
- 🎯 **Sponsored products** — sellers can boost products
- 📱 **PWA ready** — installable web app
- 🔍 **SEO optimized** — meta tags, sitemap, robots.txt
- 💾 **Auto backup** — versioned `data.dat` backups

---

## 🚀 Quick Start (Local)

### 1. Clone / unzip the project
```bash
cd nova_cart
```

### 2. Create a virtual environment
```bash
python -m venv venv
source venv/bin/activate        # Linux/Mac
venv\Scripts\activate           # Windows
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Run the development server
```bash
python run.py
```

Open **http://localhost:5000** in your browser.

---

## 🔑 Default Admin Credentials

| Field    | Value                  |
|----------|------------------------|
| Email    | `admin@novacart.com`   |
| Password | `admin@123`            |

**Change these immediately after first login via Admin → Settings.**

### 🔒 Accessing the Admin Panel
Click the **"Nova Cart"** text in the website footer **5 times quickly**.
A hidden admin login link will appear.

Or navigate directly to: `/x-admin-9f3k2/login`

---

## 📁 Project Structure

```
nova_cart/
├── run.py                    # Entry point
├── requirements.txt
├── Procfile                  # Render/Gunicorn
├── runtime.txt
│
├── app/
│   ├── __init__.py           # App factory
│   ├── context.py            # Template globals
│   ├── blueprints/
│   │   ├── main.py           # Homepage
│   │   ├── auth.py           # Login/Register
│   │   ├── shop.py           # Products, reviews, wishlist
│   │   ├── cart.py           # Cart & checkout
│   │   ├── admin.py          # Admin dashboard
│   │   ├── seller.py         # Seller portal
│   │   ├── pages.py          # Custom pages
│   │   └── api.py            # AJAX endpoints
│   ├── templates/
│   │   ├── base.html         # Master layout
│   │   ├── admin/            # Admin templates
│   │   ├── seller/           # Seller templates
│   │   ├── auth/             # Auth templates
│   │   ├── shop/             # Shop templates
│   │   ├── pages/            # Custom page template
│   │   └── partials/         # Reusable components
│   └── static/
│       ├── css/main.css      # Main stylesheet
│       ├── css/admin.css     # Admin stylesheet
│       ├── js/main.js        # Main JS
│       ├── js/admin.js       # Admin JS
│       └── images/           # Static images + uploads/
│
├── utils/
│   ├── storage.py            # File-based DB engine
│   ├── auth.py               # Password hashing, decorators
│   ├── files.py              # Upload handling
│   ├── seed.py               # Default data seeder
│   └── slugify.py            # URL slug generator
│
└── storage/
    ├── data.dat              # Main database (JSON)
    └── csv/                  # CSV exports
```

---

## ☁️ Deploy on Render

### 1. Push to GitHub
```bash
git init && git add . && git commit -m "Nova Cart"
git remote add origin https://github.com/YOUR_USERNAME/nova-cart.git
git push -u origin main
```

### 2. Create a new Web Service on Render
- Go to [render.com](https://render.com) → New → Web Service
- Connect your GitHub repo
- Configure:

| Setting          | Value                      |
|------------------|----------------------------|
| **Runtime**      | Python 3                   |
| **Build Command**| `pip install -r requirements.txt` |
| **Start Command**| `gunicorn run:app`         |

### 3. Add Environment Variables
| Key           | Value                            |
|---------------|----------------------------------|
| `SECRET_KEY`  | (generate a strong random string)|

### 4. Persistent Storage
On Render's free plan, the filesystem resets on deploy.
To persist `data.dat`, use Render **Disks** (paid) or add an export/import step.
For production, mount a persistent disk at `/data` and set:
```
STORAGE_PATH=/data/storage
```

---

## ⚙️ Admin Dashboard Guide

| Section       | What you can do                          |
|---------------|------------------------------------------|
| **Dashboard** | Stats, low stock alerts, recent orders   |
| **Products**  | Add/edit/delete products, images, flags  |
| **Categories**| Add custom categories with icons/colors  |
| **Orders**    | View orders, update status               |
| **Users**     | View/ban customers                       |
| **Sellers**   | Approve/reject seller applications       |
| **Banners**   | Upload hero banners                      |
| **Ads**       | Create and place ads                     |
| **Pages**     | Create About/Policy/Blog pages           |
| **Nav Links** | Edit navbar and footer links             |
| **Theme**     | Change colors, fonts, dark mode          |
| **Settings**  | Site name, logo, WhatsApp, social links  |
| **Backup**    | Create/view data.dat backups             |

---

## 🔧 Environment Variables

| Variable      | Default                           | Description          |
|---------------|-----------------------------------|----------------------|
| `SECRET_KEY`  | (dev key)                         | Flask secret key     |
| `PORT`        | 5000                              | Server port          |
| `FLASK_DEBUG` | false                             | Enable debug mode    |

---

## 📦 Data Storage

All data is stored in `storage/data.dat` as a JSON file.

Collections stored:
- `users` — customer and admin accounts
- `sellers` — seller shop profiles
- `products` — product catalog
- `categories` — product categories
- `orders` — customer orders
- `cart` — active cart items
- `wishlist` — customer wishlists
- `reviews` — product reviews
- `addresses` — saved delivery addresses
- `banners` — hero banner images
- `ads` — advertisement records
- `pages` — custom static pages
- `nav_links` — navbar/footer links
- `settings` — all site configuration
- `sponsored` — sponsored product records
- `testimonials` — homepage testimonials

Backups are saved automatically to `backups/data_YYYYMMDD_HHMMSS.dat`.

---

## 🛡️ Security Notes

- Passwords hashed with PBKDF2-HMAC-SHA256 (260,000 iterations)
- CSRF protection on all POST forms
- Session cookie HTTPOnly + SameSite=Lax
- File upload type validation (images only)
- Admin route not publicly linked
- XSS prevention via Jinja2 auto-escaping

---

## 📞 Default Seeded Data

On first run, the following is created automatically:
- **Admin account** — `admin@novacart.com` / `admin@123`
- **8 categories** — Electronics, Perfumes, Kitchen, etc.
- **8 sample products** — earbuds, charger, perfume, gadgets, etc.
- **5 navbar links** — Home, Shop, Electronics, Deals, Sell
- **5 footer links** — About, Contact, Policies

---

*Built with ❤️ using Python Flask + file-based storage. Zero SQL required.*
