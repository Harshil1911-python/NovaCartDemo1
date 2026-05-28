"""Seller portal blueprint"""
from flask import (Blueprint, render_template, request, redirect,
                   url_for, session, flash, jsonify)
from utils.storage import (find_record, save_record, get_record,
                           find_records, get_collection, delete_record)
from utils.auth import hash_password, check_password, is_valid_email
from utils.files import save_uploaded_file
from utils.slugify import slugify
import secrets

seller_bp = Blueprint('seller', __name__)

SELLER_SESSION = 'seller_verified'


def seller_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        uid = session.get('user_id')
        if not uid:
            flash('Please login to your seller account.', 'warning')
            return redirect(url_for('seller.login'))
        user = get_record('users', uid)
        if not user or user.get('role') not in ('seller', 'admin'):
            flash('Seller account required.', 'danger')
            return redirect(url_for('seller.login'))
        seller = find_record('sellers', user_id=uid)
        if not seller:
            flash('Seller profile not found.', 'danger')
            return redirect(url_for('seller.login'))
        if not seller.get('is_approved') and user.get('role') != 'admin':
            return redirect(url_for('seller.pending'))
        return f(*args, **kwargs)
    return decorated


# ── Seller Auth ───────────────────────────────────────────────
@seller_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        user = find_record('users', email=email)
        if user and check_password(password, user.get('password', '')):
            if user.get('role') not in ('seller', 'admin', 'pending_seller'):
                flash('This account is not a seller account.', 'danger')
                return render_template('seller/login.html')
            if not user.get('is_active', True):
                flash('Account suspended.', 'danger')
                return render_template('seller/login.html')
            session['user_id'] = user['id']
            seller = find_record('sellers', user_id=user['id'])
            if seller and not seller.get('is_approved'):
                return redirect(url_for('seller.pending'))
            flash(f'Welcome back, {user["name"]}!', 'success')
            return redirect(url_for('seller.dashboard'))
        flash('Invalid email or password.', 'danger')
    return render_template('seller/login.html')


@seller_bp.route('/logout')
def logout():
    session.clear()
    flash('Logged out from seller portal.', 'info')
    return redirect(url_for('seller.login'))


@seller_bp.route('/register', methods=['GET', 'POST'])
def register():
    error = None
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        shop_name = request.form.get('shop_name', '').strip()
        if not all([name, email, password, shop_name]):
            error = 'All fields are required.'
        elif find_record('users', email=email):
            error = 'Email already registered.'
        elif len(password) < 6:
            error = 'Password must be at least 6 characters.'
        else:
            user = save_record('users', {
                'name': name, 'email': email,
                'password': hash_password(password),
                'role': 'pending_seller', 'is_active': True,
                'avatar': '', 'phone': request.form.get('phone', ''),
            })
            slug = slugify(shop_name)
            base_slug = slug; c = 1
            while find_record('sellers', slug=slug):
                slug = f"{base_slug}-{c}"; c += 1
            save_record('sellers', {
                'user_id': user['id'], 'shop_name': shop_name, 'slug': slug,
                'description': request.form.get('description', ''),
                'contact_email': email, 'contact_phone': request.form.get('phone', ''),
                'is_approved': False, 'total_earnings': 0.0, 'logo': '', 'banner': '',
            })
            session['user_id'] = user['id']
            flash('Application submitted! Awaiting admin approval.', 'success')
            return redirect(url_for('seller.pending'))
    return render_template('seller/register.html', error=error)


@seller_bp.route('/pending')
def pending():
    return render_template('seller/pending.html')


# ── Dashboard ─────────────────────────────────────────────────
@seller_bp.route('/dashboard')
@seller_required
def dashboard():
    uid = session.get('user_id')
    seller = find_record('sellers', user_id=uid)
    products = find_records('products', seller_id=seller['id'])
    orders_raw = get_collection('orders')
    seller_product_ids = {p['id'] for p in products}
    seller_orders = []
    revenue = 0
    product_earnings = {p['id']: {'name': p['name'], 'units': 0, 'revenue': 0} for p in products}
    for o in orders_raw:
        added = False
        for item in o.get('order_lines', o.get('items', [])):
            pid = item.get('product_id')
            if pid in seller_product_ids:
                if not added:
                    seller_orders.append(o)
                    added = True
                sub = item.get('subtotal', 0)
                revenue += sub
                if pid in product_earnings:
                    product_earnings[pid]['units'] += item.get('quantity', 1)
                    product_earnings[pid]['revenue'] += sub
    earnings_breakdown = sorted(
        [v for v in product_earnings.values() if v['revenue'] > 0],
        key=lambda x: x['revenue'], reverse=True)
    stats = {
        'total_products': len(products),
        'total_orders': len(seller_orders),
        'revenue': revenue,
        'low_stock': [p for p in products if p.get('stock', 0) < 10],
    }
    return render_template('seller/dashboard.html', seller=seller, stats=stats,
                           recent_orders=seller_orders[-10:][::-1],
                           products=products[:6], earnings_breakdown=earnings_breakdown)


# ── Products ──────────────────────────────────────────────────
@seller_bp.route('/products')
@seller_required
def products():
    uid = session.get('user_id')
    seller = find_record('sellers', user_id=uid)
    items = find_records('products', seller_id=seller['id'])
    return render_template('seller/products.html', products=items, seller=seller)


@seller_bp.route('/products/add', methods=['GET', 'POST'])
@seller_required
def add_product():
    uid = session.get('user_id')
    seller = find_record('sellers', user_id=uid)
    categories = [c for c in get_collection('categories') if c.get('is_active')]
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        slug = slugify(name); base = slug; c = 1
        while find_record('products', slug=slug):
            slug = f"{base}-{c}"; c += 1
        images = []
        for f in request.files.getlist('images'):
            url = save_uploaded_file(f, 'products')
            if url: images.append(url)
        save_record('products', {
            'name': name, 'slug': slug,
            'description': request.form.get('description', ''),
            'short_description': request.form.get('short_description', ''),
            'price': float(request.form.get('price', 0)),
            'discount_price': float(request.form.get('discount_price') or 0) or None,
            'stock': int(request.form.get('stock', 0)),
            'sku': 'SKU-' + secrets.token_hex(4).upper(),
            'tags': request.form.get('tags', ''),
            'category_id': int(request.form.get('category_id', 0)),
            'seller_id': seller['id'], 'is_active': True,
            'is_featured': False, 'is_trending': False, 'is_new_arrival': True,
            'images': images, 'meta_title': name, 'meta_description': '', 'views': 0,
        })
        flash('Product added!', 'success')
        return redirect(url_for('seller.products'))
    return render_template('seller/product_form.html', product=None,
                           categories=categories, seller=seller)


@seller_bp.route('/products/edit/<int:pid>', methods=['GET', 'POST'])
@seller_required
def edit_product(pid):
    uid = session.get('user_id')
    seller = find_record('sellers', user_id=uid)
    product = get_record('products', pid)
    if not product or product.get('seller_id') != seller['id']:
        flash('Not authorized.', 'danger')
        return redirect(url_for('seller.products'))
    categories = [c for c in get_collection('categories') if c.get('is_active')]
    if request.method == 'POST':
        product['name'] = request.form.get('name', '').strip()
        product['description'] = request.form.get('description', '')
        product['short_description'] = request.form.get('short_description', '')
        product['price'] = float(request.form.get('price', 0))
        product['discount_price'] = float(request.form.get('discount_price') or 0) or None
        product['stock'] = int(request.form.get('stock', 0))
        product['tags'] = request.form.get('tags', '')
        product['category_id'] = int(request.form.get('category_id', 0))
        for f in request.files.getlist('images'):
            url = save_uploaded_file(f, 'products')
            if url: product.setdefault('images', []).append(url)
        save_record('products', product)
        flash('Product updated!', 'success')
        return redirect(url_for('seller.products'))
    return render_template('seller/product_form.html', product=product,
                           categories=categories, seller=seller)


@seller_bp.route('/products/delete/<int:pid>', methods=['POST'])
@seller_required
def delete_product(pid):
    uid = session.get('user_id')
    seller = find_record('sellers', user_id=uid)
    product = get_record('products', pid)
    if product and product.get('seller_id') == seller['id']:
        delete_record('products', pid)
        flash('Product deleted.', 'info')
    return redirect(url_for('seller.products'))


# ── Orders ────────────────────────────────────────────────────
@seller_bp.route('/orders')
@seller_required
def orders():
    uid = session.get('user_id')
    seller = find_record('sellers', user_id=uid)
    products = find_records('products', seller_id=seller['id'])
    seller_product_ids = {p['id'] for p in products}
    all_orders = []
    for o in get_collection('orders'):
        for item in o.get('order_lines', o.get('items', [])):
            if item.get('product_id') in seller_product_ids:
                # Attach only seller's items to this order view
                o['_seller_items'] = [
                    i for i in o.get('order_lines', o.get('items', []))
                    if i.get('product_id') in seller_product_ids
                ]
                all_orders.append(o)
                break
    all_orders.sort(key=lambda x: x.get('created_at', ''), reverse=True)
    return render_template('seller/orders.html', orders=all_orders, seller=seller)


@seller_bp.route('/orders/<int:oid>/confirm', methods=['POST'])
@seller_required
def confirm_order(oid):
    uid = session.get('user_id')
    seller = find_record('sellers', user_id=uid)
    products = find_records('products', seller_id=seller['id'])
    seller_product_ids = {p['id'] for p in products}
    order = get_record('orders', oid)
    if order:
        # Verify this order contains seller's products
        has_seller_product = any(
            i.get('product_id') in seller_product_ids
            for i in order.get('order_lines', order.get('items', []))
        )
        if has_seller_product:
            new_status = request.form.get('status', 'confirmed')
            order['status'] = new_status
            save_record('orders', order)
            flash(f'Order #{order["order_id"]} updated to {new_status}.', 'success')
    return redirect(url_for('seller.orders'))


# ── Profile ───────────────────────────────────────────────────
@seller_bp.route('/profile', methods=['GET', 'POST'])
@seller_required
def profile():
    uid = session.get('user_id')
    seller = find_record('sellers', user_id=uid)
    if request.method == 'POST':
        seller['shop_name'] = request.form.get('shop_name', seller['shop_name'])
        seller['description'] = request.form.get('description', '')
        seller['contact_email'] = request.form.get('contact_email', '')
        seller['contact_phone'] = request.form.get('contact_phone', '')
        for field in ['logo', 'banner']:
            f = request.files.get(field)
            if f and f.filename:
                url = save_uploaded_file(f, 'sellers')
                if url: seller[field] = url
        save_record('sellers', seller)
        flash('Profile updated!', 'success')
    return render_template('seller/profile.html', seller=seller)
