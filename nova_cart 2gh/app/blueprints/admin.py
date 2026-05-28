"""Admin blueprint - fully secured secret panel"""
from flask import (Blueprint, render_template, request, redirect,
                   url_for, session, flash, jsonify, abort)
from utils.storage import (get_collection, find_record, save_record, delete_record,
                           get_all_settings, save_setting, get_record, find_records,
                           create_backup, list_backups, _read_data)
from utils.auth import hash_password, check_password
from utils.files import save_uploaded_file, delete_file
from utils.slugify import slugify
import secrets, time, json

admin_bp = Blueprint('admin', __name__)

# ── Security constants ─────────────────────────────────────────
MAX_LOGIN_ATTEMPTS = 5
LOCKOUT_SECONDS = 300          # 5 min lockout
ADMIN_SESSION_KEY = 'admin_v'
ADMIN_SESSION_TS  = 'admin_ts'
ADMIN_SESSION_TTL = 3600       # 1 hour session TTL
_login_attempts = {}           # ip -> [timestamps]


def _get_ip():
    return request.headers.get('X-Forwarded-For', request.remote_addr or 'local')


def _is_locked(ip):
    now = time.time()
    attempts = [t for t in _login_attempts.get(ip, []) if now - t < LOCKOUT_SECONDS]
    _login_attempts[ip] = attempts
    return len(attempts) >= MAX_LOGIN_ATTEMPTS


def _record_attempt(ip):
    _login_attempts.setdefault(ip, []).append(time.time())


def _clear_attempts(ip):
    _login_attempts.pop(ip, None)


def admin_login_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get(ADMIN_SESSION_KEY):
            return redirect(url_for('admin.login'))
        # Check session TTL
        ts = session.get(ADMIN_SESSION_TS, 0)
        if time.time() - ts > ADMIN_SESSION_TTL:
            session.pop(ADMIN_SESSION_KEY, None)
            flash('Session expired. Please log in again.', 'warning')
            return redirect(url_for('admin.login'))
        # Refresh timestamp on activity
        session[ADMIN_SESSION_TS] = time.time()
        return f(*args, **kwargs)
    return decorated


# ── Auth ───────────────────────────────────────────────────────
@admin_bp.route('/login', methods=['GET', 'POST'])
def login():
    if session.get(ADMIN_SESSION_KEY):
        return redirect(url_for('admin.dashboard'))

    ip = _get_ip()
    locked = _is_locked(ip)
    error = None

    if request.method == 'POST':
        if locked:
            error = f'Too many failed attempts. Try again in {LOCKOUT_SECONDS//60} minutes.'
        else:
            email    = request.form.get('email', '').strip().lower()
            password = request.form.get('password', '')
            pin      = request.form.get('admin_pin', '').strip()

            user = find_record('users', email=email, role='admin')
            stored_pin = get_all_settings().get('admin_pin', '')

            if user and check_password(password, user.get('password', '')):
                # Check PIN if set
                if stored_pin and pin != stored_pin:
                    _record_attempt(ip)
                    error = 'Invalid admin PIN.'
                else:
                    _clear_attempts(ip)
                    session[ADMIN_SESSION_KEY] = True
                    session[ADMIN_SESSION_TS]  = time.time()
                    session['user_id'] = user['id']
                    session.permanent = True
                    # Log admin login
                    save_record('admin_log', {
                        'action': 'login', 'user_email': email,
                        'ip': ip, 'ts': time.time()
                    })
                    flash('Welcome to Admin Panel!', 'success')
                    return redirect(url_for('admin.dashboard'))
            else:
                _record_attempt(ip)
                remaining = MAX_LOGIN_ATTEMPTS - len(_login_attempts.get(ip, []))
                error = f'Invalid credentials. {remaining} attempts remaining.'

    remaining_attempts = MAX_LOGIN_ATTEMPTS - len(_login_attempts.get(ip, []))
    has_pin = bool(get_all_settings().get('admin_pin', ''))
    return render_template('admin/login.html',
        error=error, locked=locked,
        remaining_attempts=remaining_attempts,
        has_pin=has_pin)


@admin_bp.route('/logout')
def logout():
    ip = _get_ip()
    save_record('admin_log', {'action': 'logout', 'ip': ip, 'ts': time.time()})
    session.pop(ADMIN_SESSION_KEY, None)
    session.pop(ADMIN_SESSION_TS, None)
    flash('Logged out from admin.', 'info')
    return redirect(url_for('main.index'))


# ── Dashboard ──────────────────────────────────────────────────
@admin_bp.route('/')
@admin_login_required
def dashboard():
    stats = {
        'total_products': len(get_collection('products')),
        'total_orders':   len(get_collection('orders')),
        'total_users':    len([u for u in get_collection('users') if u.get('role') == 'customer']),
        'total_sellers':  len(get_collection('sellers')),
        'total_revenue':  sum(o.get('total', 0) for o in get_collection('orders')
                              if o.get('status') != 'cancelled'),
        'pending_orders': len(find_records('orders', status='pending')),
        'low_stock':      [p for p in get_collection('products')
                           if p.get('stock', 0) < 10 and p.get('is_active')],
        'newsletter_subs': len(get_collection('newsletter')),
    }
    recent_orders = sorted(get_collection('orders'),
                           key=lambda x: x.get('created_at', ''), reverse=True)[:10]
    return render_template('admin/dashboard.html', stats=stats, recent_orders=recent_orders)


# ── Products ───────────────────────────────────────────────────
@admin_bp.route('/products')
@admin_login_required
def products():
    items = sorted(get_collection('products'),
                   key=lambda x: x.get('created_at', ''), reverse=True)
    cats = {c['id']: c['name'] for c in get_collection('categories')}
    for p in items:
        p['category_name'] = cats.get(p.get('category_id'), '')
    return render_template('admin/products.html', products=items)


@admin_bp.route('/products/add', methods=['GET', 'POST'])
@admin_login_required
def add_product():
    categories = [c for c in get_collection('categories') if c.get('is_active')]
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        slug_base = slugify(name); slug = slug_base; c = 1
        while find_record('products', slug=slug):
            slug = f"{slug_base}-{c}"; c += 1
        images = []
        for f in request.files.getlist('images'):
            url = save_uploaded_file(f, 'products')
            if url: images.append(url)
        dp = request.form.get('discount_price', '').strip()
        # Build variants
        vnames = request.form.getlist('variant_name[]')
        vopts = request.form.getlist('variant_options[]')
        variants = [{'name': n.strip(), 'options': [o.strip() for o in opts.split(',') if o.strip()]}
                    for n, opts in zip(vnames, vopts) if n.strip()]
        # Build specs
        skeys = request.form.getlist('spec_key[]')
        svals = request.form.getlist('spec_value[]')
        specs = [{'key': k.strip(), 'value': v.strip()} for k, v in zip(skeys, svals) if k.strip()]
        save_record('products', {
            'name': name, 'slug': slug,
            'description': request.form.get('description', ''),
            'short_description': request.form.get('short_description', ''),
            'price': float(request.form.get('price', 0)),
            'discount_price': float(dp) if dp else None,
            'stock': int(request.form.get('stock', 0)),
            'sku': request.form.get('sku') or 'SKU-' + secrets.token_hex(4).upper(),
            'tags': request.form.get('tags', ''),
            'category_id': int(request.form.get('category_id', 0)),
            'seller_id': None, 'is_active': 'is_active' in request.form,
            'is_featured': 'is_featured' in request.form,
            'is_trending': 'is_trending' in request.form,
            'is_new_arrival': 'is_new_arrival' in request.form,
            'is_flash_sale': 'is_flash_sale' in request.form,
            'images': images, 'meta_title': request.form.get('meta_title', name),
            'meta_description': request.form.get('meta_description', ''),
            'variants': variants, 'specifications': specs,
            'size_chart': request.form.get('size_chart', ''),
            'views': 0,
        })
        flash('Product added!', 'success')
        return redirect(url_for('admin.products'))
    return render_template('admin/product_form.html', product=None, categories=categories)


@admin_bp.route('/products/edit/<int:pid>', methods=['GET', 'POST'])
@admin_login_required
def edit_product(pid):
    product = get_record('products', pid)
    if not product:
        flash('Product not found.', 'danger'); return redirect(url_for('admin.products'))
    categories = [c for c in get_collection('categories') if c.get('is_active')]
    if request.method == 'POST':
        product['name'] = request.form.get('name', '').strip()
        product['description'] = request.form.get('description', '')
        product['short_description'] = request.form.get('short_description', '')
        product['price'] = float(request.form.get('price', 0))
        dp = request.form.get('discount_price', '').strip()
        product['discount_price'] = float(dp) if dp else None
        product['stock'] = int(request.form.get('stock', 0))
        product['tags'] = request.form.get('tags', '')
        product['category_id'] = int(request.form.get('category_id', 0))
        product['is_active'] = 'is_active' in request.form
        product['is_featured'] = 'is_featured' in request.form
        product['is_trending'] = 'is_trending' in request.form
        product['is_new_arrival'] = 'is_new_arrival' in request.form
        product['is_flash_sale'] = 'is_flash_sale' in request.form
        product['meta_title'] = request.form.get('meta_title', '')
        product['meta_description'] = request.form.get('meta_description', '')
        imgs = list(product.get('images', []))
        for f in request.files.getlist('images'):
            url = save_uploaded_file(f, 'products')
            if url: imgs.append(url)
        # Handle image deletions
        remove = request.form.getlist('remove_image')
        imgs = [i for i in imgs if i not in remove]
        product['images'] = imgs
        save_record('products', product)
        flash('Product updated!', 'success')
        return redirect(url_for('admin.products'))
    return render_template('admin/product_form.html', product=product, categories=categories)


@admin_bp.route('/products/delete/<int:pid>', methods=['POST'])
@admin_login_required
def delete_product(pid):
    delete_record('products', pid)
    flash('Product deleted.', 'info')
    return redirect(url_for('admin.products'))


# ── Categories ─────────────────────────────────────────────────
@admin_bp.route('/categories', methods=['GET', 'POST'])
@admin_login_required
def categories():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        slug = slugify(name)
        save_record('categories', {
            'name': name, 'slug': slug,
            'icon': request.form.get('icon', 'fas fa-tag'),
            'color': request.form.get('color', '#6C63FF'),
            'description': request.form.get('description', ''),
            'is_active': True, 'sort_order': int(request.form.get('sort_order', 0)),
        })
        flash('Category added!', 'success')
    return render_template('admin/categories.html', categories=get_collection('categories'))


@admin_bp.route('/categories/delete/<int:cid>', methods=['POST'])
@admin_login_required
def delete_category(cid):
    delete_record('categories', cid)
    flash('Category deleted.', 'info')
    return redirect(url_for('admin.categories'))


# ── Orders ─────────────────────────────────────────────────────
@admin_bp.route('/orders')
@admin_login_required
def orders():
    all_orders = sorted(get_collection('orders'),
                        key=lambda x: x.get('created_at', ''), reverse=True)
    return render_template('admin/orders.html', orders=all_orders)


@admin_bp.route('/orders/<int:oid>/status', methods=['POST'])
@admin_login_required
def update_order_status(oid):
    order = get_record('orders', oid)
    if order:
        order['status'] = request.form.get('status', order['status'])
        save_record('orders', order)
        flash('Order status updated.', 'success')
    return redirect(url_for('admin.orders'))


# ── Users ──────────────────────────────────────────────────────
@admin_bp.route('/users')
@admin_login_required
def users():
    all_users = get_collection('users')
    return render_template('admin/users.html', users=all_users)


@admin_bp.route('/users/<int:uid>/detail')
@admin_login_required
def user_detail(uid):
    user = get_record('users', uid)
    if not user:
        return jsonify({'error': 'Not found'}), 404
    orders = find_records('orders', user_id=uid)
    addresses = find_records('addresses', user_id=uid)
    cart = find_records('cart', user_id=uid)
    wishlist = find_records('wishlist', user_id=uid)
    total_spent = sum(o.get('total', 0) for o in orders)
    return jsonify({
        'id': user['id'], 'name': user.get('name', ''),
        'email': user.get('email', ''), 'phone': user.get('phone', ''),
        'role': user.get('role', ''), 'is_active': user.get('is_active', True),
        'created_at': user.get('created_at', '')[:10] if user.get('created_at') else '',
        'total_orders': len(orders), 'total_spent': round(total_spent, 2),
        'cart_items': len(cart), 'wishlist_items': len(wishlist),
        'addresses': addresses, 'recent_orders': orders[-5:][::-1],
        'password_hash': user.get('password', '')[:30] + '…',
    })


@admin_bp.route('/users/<int:uid>/toggle', methods=['POST'])
@admin_login_required
def toggle_user(uid):
    user = get_record('users', uid)
    if user:
        user['is_active'] = not user.get('is_active', True)
        save_record('users', user)
    return redirect(url_for('admin.users'))


# ── Sellers ────────────────────────────────────────────────────
@admin_bp.route('/sellers')
@admin_login_required
def sellers():
    return render_template('admin/sellers.html', sellers=get_collection('sellers'))


@admin_bp.route('/sellers/<int:sid>/detail')
@admin_login_required
def seller_detail(sid):
    seller = get_record('sellers', sid)
    if not seller: return jsonify({'error': 'Not found'}), 404
    user = get_record('users', seller.get('user_id'))
    products = find_records('products', seller_id=sid)
    orders_raw = get_collection('orders')
    pids = {p['id'] for p in products}
    revenue = sum(
        item.get('subtotal', 0)
        for o in orders_raw
        for item in o.get('order_lines', o.get('items', []))
        if item.get('product_id') in pids
    )
    return jsonify({
        'id': seller['id'], 'shop_name': seller.get('shop_name', ''),
        'slug': seller.get('slug', ''), 'is_approved': seller.get('is_approved', False),
        'contact_email': seller.get('contact_email', ''),
        'contact_phone': seller.get('contact_phone', ''),
        'description': seller.get('description', ''),
        'created_at': seller.get('created_at', '')[:10] if seller.get('created_at') else '',
        'total_products': len(products), 'total_revenue': round(revenue, 2),
        'user_email': user.get('email', '') if user else '',
        'user_name': user.get('name', '') if user else '',
        'password_hash': (user.get('password', '')[:30] + '…') if user else '',
    })


@admin_bp.route('/sellers/<int:sid>/approve', methods=['POST'])
@admin_login_required
def approve_seller(sid):
    seller = get_record('sellers', sid)
    if seller:
        seller['is_approved'] = True
        save_record('sellers', seller)
        user = get_record('users', seller.get('user_id'))
        if user:
            user['role'] = 'seller'
            save_record('users', user)
        flash('Seller approved!', 'success')
    return redirect(url_for('admin.sellers'))


@admin_bp.route('/sellers/<int:sid>/reject', methods=['POST'])
@admin_login_required
def reject_seller(sid):
    seller = get_record('sellers', sid)
    if seller:
        seller['is_approved'] = False
        save_record('sellers', seller)
        flash('Seller rejected.', 'info')
    return redirect(url_for('admin.sellers'))


# ── Settings ───────────────────────────────────────────────────
@admin_bp.route('/settings', methods=['GET', 'POST'])
@admin_login_required
def settings():
    if request.method == 'POST':
        for key, value in request.form.items():
            if key == 'csrf_token': continue
            save_setting(key, value)
        for field in ['site_logo', 'site_favicon']:
            f = request.files.get(field)
            if f and f.filename:
                url = save_uploaded_file(f, 'branding')
                if url: save_setting(field, url)
        flash('Settings saved!', 'success')
    return render_template('admin/settings.html', s=get_all_settings())


# ── Theme ──────────────────────────────────────────────────────
@admin_bp.route('/theme', methods=['GET', 'POST'])
@admin_login_required
def theme():
    if request.method == 'POST':
        for key in ['primary_color','secondary_color','accent_color','bg_color',
                    'navbar_color','footer_color','text_color','font_family',
                    'button_radius','card_radius','dark_mode','custom_css','custom_js']:
            val = request.form.get(key)
            if val is not None: save_setting(key, val)
        if 'dark_mode' not in request.form: save_setting('dark_mode','false')
        flash('Theme updated!', 'success')
    return render_template('admin/theme.html', s=get_all_settings())


# ── Customize ──────────────────────────────────────────────────
@admin_bp.route('/customize', methods=['GET', 'POST'])
@admin_login_required
def customize():
    if request.method == 'POST':
        text_keys = [
            'hero_gradient_from','hero_gradient_to','card_shadow',
            'product_card_style','homepage_layout','loader_color',
            'custom_badge_text','sale_badge_color','footer_style',
            'currency_symbol','products_per_row','btn_style',
            'netlify_about','netlify_contact','netlify_privacy',
            'netlify_refund','netlify_shipping','netlify_custom_1',
            'netlify_custom_2','netlify_custom_3',
            'custom_link_1_label','custom_link_1_url',
            'custom_link_2_label','custom_link_2_url',
            'custom_link_3_label','custom_link_3_url',
            'header_scripts','body_end_scripts',
            'product_zoom','show_breadcrumb','cart_style',
        ]
        for k in text_keys:
            v = request.form.get(k)
            if v is not None: save_setting(k, v)
        # Checkboxes
        for k in ['navbar_sticky','show_live_visitors','show_social_proof',
                  'show_whatsapp_fab','loader_active','show_rating_in_card',
                  'show_stock_in_card','product_zoom','show_breadcrumb']:
            save_setting(k, 'true' if k in request.form else 'false')
        flash('Customization saved!', 'success')
    return render_template('admin/customize.html', s=get_all_settings())


# ── Banners ────────────────────────────────────────────────────
@admin_bp.route('/banners', methods=['GET', 'POST'])
@admin_login_required
def banners():
    if request.method == 'POST':
        f = request.files.get('image')
        url = save_uploaded_file(f, 'banners') if f and f.filename else ''
        save_record('banners', {
            'title': request.form.get('title',''),
            'subtitle': request.form.get('subtitle',''),
            'button_text': request.form.get('button_text',''),
            'button_url': request.form.get('button_url',''),
            'image': url, 'is_active': True,
            'sort_order': int(request.form.get('sort_order',0)),
        })
        flash('Banner added!', 'success')
    return render_template('admin/banners.html', banners=get_collection('banners'))


@admin_bp.route('/banners/delete/<int:bid>', methods=['POST'])
@admin_login_required
def delete_banner(bid):
    delete_record('banners', bid)
    return redirect(url_for('admin.banners'))


# ── Ads ────────────────────────────────────────────────────────
@admin_bp.route('/ads', methods=['GET', 'POST'])
@admin_login_required
def ads():
    if request.method == 'POST':
        f = request.files.get('image')
        url = save_uploaded_file(f, 'ads') if f and f.filename else ''
        save_record('ads', {
            'title': request.form.get('title',''),
            'image': url, 'link': request.form.get('link',''),
            'placement': request.form.get('placement','homepage'),
            'is_active': True, 'clicks': 0, 'impressions': 0,
        })
        flash('Ad created!', 'success')
    return render_template('admin/ads.html', ads=get_collection('ads'))


@admin_bp.route('/ads/toggle/<int:aid>', methods=['POST'])
@admin_login_required
def toggle_ad(aid):
    ad = get_record('ads', aid)
    if ad:
        ad['is_active'] = not ad.get('is_active', True)
        save_record('ads', ad)
    return redirect(url_for('admin.ads'))


@admin_bp.route('/ads/delete/<int:aid>', methods=['POST'])
@admin_login_required
def delete_ad(aid):
    delete_record('ads', aid)
    return redirect(url_for('admin.ads'))


# ── Pages ──────────────────────────────────────────────────────
@admin_bp.route('/pages', methods=['GET', 'POST'])
@admin_login_required
def pages():
    if request.method == 'POST':
        title = request.form.get('title','').strip()
        save_record('pages', {
            'title': title, 'slug': slugify(title),
            'content': request.form.get('content',''),
            'meta_title': request.form.get('meta_title', title),
            'meta_description': request.form.get('meta_description',''),
            'is_published': 'is_published' in request.form,
        })
        flash('Page created!', 'success')
    return render_template('admin/pages.html', pages=get_collection('pages'))


@admin_bp.route('/pages/edit/<int:pid>', methods=['GET', 'POST'])
@admin_login_required
def edit_page(pid):
    page = get_record('pages', pid)
    if not page: return redirect(url_for('admin.pages'))
    if request.method == 'POST':
        page['title'] = request.form.get('title','').strip()
        page['content'] = request.form.get('content','')
        page['meta_title'] = request.form.get('meta_title','')
        page['meta_description'] = request.form.get('meta_description','')
        page['is_published'] = 'is_published' in request.form
        save_record('pages', page)
        flash('Page updated!', 'success')
        return redirect(url_for('admin.pages'))
    return render_template('admin/page_form.html', page=page)


@admin_bp.route('/pages/delete/<int:pid>', methods=['POST'])
@admin_login_required
def delete_page(pid):
    delete_record('pages', pid)
    return redirect(url_for('admin.pages'))


# ── Nav Links ──────────────────────────────────────────────────
@admin_bp.route('/nav-links', methods=['GET', 'POST'])
@admin_login_required
def nav_links():
    if request.method == 'POST':
        save_record('nav_links', {
            'label': request.form.get('label',''),
            'url': request.form.get('url',''),
            'location': request.form.get('location','navbar'),
            'sort_order': int(request.form.get('sort_order',0)),
            'is_active': True,
        })
        flash('Link added!', 'success')
    return render_template('admin/nav_links.html', links=get_collection('nav_links'))


@admin_bp.route('/nav-links/delete/<int:lid>', methods=['POST'])
@admin_login_required
def delete_nav_link(lid):
    delete_record('nav_links', lid)
    return redirect(url_for('admin.nav_links'))


# ── Testimonials ───────────────────────────────────────────────
@admin_bp.route('/testimonials', methods=['GET', 'POST'])
@admin_login_required
def testimonials():
    if request.method == 'POST':
        save_record('testimonials', {
            'name': request.form.get('name',''),
            'location': request.form.get('location',''),
            'rating': int(request.form.get('rating',5)),
            'comment': request.form.get('comment',''),
            'is_active': True,
        })
        flash('Testimonial added!', 'success')
    return render_template('admin/testimonials.html',
                           testimonials=get_collection('testimonials'))


@admin_bp.route('/testimonials/delete/<int:tid>', methods=['POST'])
@admin_login_required
def delete_testimonial(tid):
    delete_record('testimonials', tid)
    return redirect(url_for('admin.testimonials'))


# ── Coupons ────────────────────────────────────────────────────
@admin_bp.route('/coupons', methods=['GET', 'POST'])
@admin_login_required
def coupons():
    if request.method == 'POST':
        save_record('coupons', {
            'code': request.form.get('code','').strip().upper(),
            'discount_type': request.form.get('discount_type','percent'),
            'discount_value': float(request.form.get('discount_value',0)),
            'min_order': float(request.form.get('min_order',0)),
            'is_active': True, 'usage_count': 0,
        })
        flash('Coupon created!', 'success')
    return render_template('admin/coupons.html', coupons=get_collection('coupons'))


@admin_bp.route('/coupons/delete/<int:cid>', methods=['POST'])
@admin_login_required
def delete_coupon(cid):
    delete_record('coupons', cid)
    return redirect(url_for('admin.coupons'))


# ── Analytics ──────────────────────────────────────────────────
@admin_bp.route('/analytics', methods=['GET', 'POST'])
@admin_bp.route('/analytics-settings', methods=['GET', 'POST'])
@admin_login_required
def analytics_view():
    if request.method == 'POST':
        save_setting('ga_tracking_id', request.form.get('ga_tracking_id',''))
        save_setting('newsletter_active', 'true' if 'newsletter_active' in request.form else 'false')
        flash('Analytics settings saved!', 'success')
    return render_template('admin/analytics.html', s=get_all_settings())


# ── Security Settings ──────────────────────────────────────────
@admin_bp.route('/security', methods=['GET', 'POST'])
@admin_login_required
def security():
    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'set_pin':
            new_pin = request.form.get('new_pin','').strip()
            if new_pin and len(new_pin) >= 4:
                save_setting('admin_pin', new_pin)
                flash('Admin PIN updated!', 'success')
            else:
                flash('PIN must be at least 4 characters.', 'danger')
        elif action == 'remove_pin':
            save_setting('admin_pin', '')
            flash('Admin PIN removed.', 'info')
        elif action == 'change_password':
            old_pw = request.form.get('old_password','')
            new_pw = request.form.get('new_password','')
            uid = session.get('user_id')
            user = get_record('users', uid)
            if user and check_password(old_pw, user.get('password','')):
                if len(new_pw) >= 6:
                    user['password'] = hash_password(new_pw)
                    save_record('users', user)
                    flash('Password changed successfully!', 'success')
                else:
                    flash('New password must be at least 6 characters.', 'danger')
            else:
                flash('Current password is incorrect.', 'danger')
    s = get_all_settings()
    logs = sorted(get_collection('admin_log'),
                  key=lambda x: x.get('ts',0), reverse=True)[:20]
    return render_template('admin/security.html', s=s, logs=logs)


# ── Backup ────────────────────────────────────────────────────
@admin_bp.route('/backup', methods=['GET', 'POST'])
@admin_login_required
def backup():
    if request.method == 'POST':
        path = create_backup()
        flash(f'Backup created!', 'success')
    return render_template('admin/backup.html', backups=list_backups())


# ── Data Vault ────────────────────────────────────────────────
@admin_bp.route('/data-vault')
@admin_login_required
def data_vault():
    raw = _read_data()
    summary = {k: len(v) if isinstance(v, list) else 1 for k, v in raw.items()}
    return render_template('admin/data_vault.html',
                           summary=summary, collections=list(raw.keys()))


@admin_bp.route('/data-vault/<collection>')
@admin_login_required
def data_vault_collection(collection):
    records = get_collection(collection)
    return render_template('admin/data_vault_collection.html',
                           collection=collection, records=records)


@admin_bp.route('/data-vault/<collection>/<int:rid>/delete', methods=['POST'])
@admin_login_required
def data_vault_delete(collection, rid):
    delete_record(collection, rid)
    flash(f'Record deleted from {collection}.', 'info')
    return redirect(url_for('admin.data_vault_collection', collection=collection))


# ── Page Builder ──────────────────────────────────────────────
@admin_bp.route('/page-builder')
@admin_login_required
def page_builder():
    return render_template('admin/page_builder.html', pages=get_collection('pages'))


@admin_bp.route('/page-builder/edit/<int:pid>')
@admin_login_required
def page_builder_edit(pid):
    page = get_record('pages', pid)
    if not page:
        flash('Page not found.', 'danger')
        return redirect(url_for('admin.page_builder'))
    return render_template('admin/page_builder_editor.html', page=page)


@admin_bp.route('/page-builder/new')
@admin_login_required
def page_builder_new():
    return render_template('admin/page_builder_editor.html', page=None)


@admin_bp.route('/page-builder/save', methods=['POST'])
@admin_login_required
def page_builder_save():
    data = request.get_json()
    pid = data.get('id')
    title = data.get('title','Untitled Page')
    content = data.get('content','')
    slug = data.get('slug') or slugify(title)
    if pid:
        page = get_record('pages', int(pid))
        if page:
            page.update({'title': title, 'content': content, 'slug': slug,
                         'meta_title': data.get('meta_title', title),
                         'meta_description': data.get('meta_description',''),
                         'is_published': data.get('is_published', True)})
            save_record('pages', page)
            return jsonify({'status':'ok','id':page['id'],'slug':page['slug']})
    page = save_record('pages', {
        'title': title, 'slug': slug, 'content': content,
        'meta_title': data.get('meta_title', title),
        'meta_description': data.get('meta_description',''),
        'is_published': data.get('is_published', True),
    })
    return jsonify({'status':'ok','id':page['id'],'slug':page['slug']})


@admin_bp.route('/ads/preview/<int:aid>')
@admin_login_required
def preview_ad(aid):
    ad = get_record('ads', aid)
    if not ad:
        return "Ad not found", 404
    return render_template('admin/ad_preview.html', ad=ad)


# ── Marketing Admin ────────────────────────────────────────────
@admin_bp.route('/marketing')
@admin_login_required
def marketing():
    from utils.storage import get_collection as gc
    stats = {
        'newsletter': len(gc('newsletter')),
        'loyalty_users': len(gc('loyalty')),
        'referrals': len(gc('referrals')),
        'total_points': sum(r.get('points',0) for r in gc('loyalty')),
        'notifications_sent': len(gc('notifications')),
    }
    newsletter_subs = gc('newsletter')
    loyalty_users = gc('loyalty')
    from utils.storage import get_all_settings
    return render_template('admin/marketing.html',
                           stats=stats, newsletter_subs=newsletter_subs,
                           loyalty_users=loyalty_users, s=get_all_settings())


@admin_bp.route('/marketing/send-notification', methods=['POST'])
@admin_login_required
def send_mass_notification():
    title = request.form.get('title','')
    message = request.form.get('message','')
    target = request.form.get('target','all')
    from utils.storage import get_collection as gc
    from app.blueprints.marketing import send_notification
    users = gc('users')
    count = 0
    for u in users:
        if target == 'all' or u.get('role') == target:
            send_notification(u['id'], title, message, 'info')
            count += 1
    flash(f'Notification sent to {count} users!', 'success')
    return redirect(url_for('admin.marketing'))


@admin_bp.route('/marketing/loyalty-settings', methods=['POST'])
@admin_login_required
def loyalty_settings():
    save_setting('points_value', request.form.get('points_value','0.5'))
    save_setting('referral_bonus', request.form.get('referral_bonus','100'))
    flash('Loyalty settings saved!', 'success')
    return redirect(url_for('admin.marketing'))


@admin_bp.route('/marketing/add-points', methods=['POST'])
@admin_login_required
def admin_add_points():
    uid = int(request.form.get('user_id',0))
    pts = int(request.form.get('points',0))
    if uid and pts:
        from app.blueprints.marketing import add_points
        add_points(uid, pts, 'admin_bonus')
        flash(f'Added {pts} points to user #{uid}!', 'success')
    return redirect(url_for('admin.marketing'))


# ── Marketing Admin ────────────────────────────────────────────
@admin_bp.route('/marketing', methods=['GET', 'POST'])
@admin_login_required
def marketing_hub():
    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'send_notification':
            from utils.storage import get_collection as gc
            title   = request.form.get('title', '')
            message = request.form.get('message', '')
            target  = request.form.get('target', 'all')
            users   = gc('users')
            count   = 0
            for u in users:
                if target == 'all' or u.get('role') == target:
                    from app.blueprints.marketing import send_notification
                    send_notification(u['id'], title, message, 'info', '/shop')
                    count += 1
            flash(f'Notification sent to {count} users!', 'success')
        elif action == 'set_loyalty':
            save_setting('points_value',   request.form.get('points_value', '0.5'))
            save_setting('referral_bonus', request.form.get('referral_bonus', '100'))
            flash('Loyalty settings saved!', 'success')
        elif action == 'add_loyalty':
            uid   = request.form.get('user_id')
            pts   = int(request.form.get('points', 0))
            reason = request.form.get('reason', 'admin_gift')
            if uid and pts:
                from app.blueprints.marketing import add_points
                add_points(int(uid), pts, reason)
                flash(f'Added {pts} points to user #{uid}', 'success')
    s        = get_all_settings()
    users    = get_collection('users')
    loyalty  = get_collection('loyalty')
    referrals = get_collection('referrals')
    notifs   = get_collection('notifications')
    newsletter = get_collection('newsletter')
    return render_template('admin/marketing.html',
        s=s, users=users, loyalty=loyalty,
        referrals=referrals, notifs=notifs, newsletter=newsletter)


# ── Inventory Management ───────────────────────────────────────
@admin_bp.route('/inventory')
@admin_login_required
def inventory():
    products = sorted(get_collection('products'),
                      key=lambda x: x.get('stock', 0))
    cats = {c['id']: c['name'] for c in get_collection('categories')}
    for p in products:
        p['category_name'] = cats.get(p.get('category_id'), '')
    low_stock   = [p for p in products if 0 < p.get('stock', 0) <= 10]
    out_of_stock = [p for p in products if p.get('stock', 0) == 0]
    in_stock     = [p for p in products if p.get('stock', 0) > 10]
    return render_template('admin/inventory.html',
        products=products, low_stock=low_stock,
        out_of_stock=out_of_stock, in_stock=in_stock)


@admin_bp.route('/inventory/update', methods=['POST'])
@admin_login_required
def update_inventory():
    for key, val in request.form.items():
        if key.startswith('stock_') and key != 'csrf_token':
            pid = int(key.replace('stock_', ''))
            p   = get_record('products', pid)
            if p:
                p['stock'] = max(0, int(val or 0))
                save_record('products', p)
    flash('Inventory updated!', 'success')
    return redirect(url_for('admin.inventory'))


# ── Bulk Order Actions ─────────────────────────────────────────
@admin_bp.route('/orders/bulk', methods=['POST'])
@admin_login_required
def bulk_orders():
    action  = request.form.get('action')
    ids     = [int(i) for i in request.form.getlist('order_ids') if i.isdigit()]
    updated = 0
    for oid in ids:
        o = get_record('orders', oid)
        if o:
            if action in ('confirm', 'ship', 'deliver', 'cancel'):
                status_map = {'confirm': 'confirmed', 'ship': 'shipped',
                              'deliver': 'delivered', 'cancel': 'cancelled'}
                o['status'] = status_map[action]
                save_record('orders', o)
                updated += 1
    flash(f'{updated} orders updated to {action}.', 'success')
    return redirect(url_for('admin.orders'))


# ── Export CSV ────────────────────────────────────────────────
@admin_bp.route('/export/<collection>')
@admin_login_required
def export_csv(collection):
    from flask import make_response
    import csv, io
    records = get_collection(collection)
    if not records:
        flash(f'No data in {collection}.', 'info')
        return redirect(url_for('admin.data_vault'))
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=records[0].keys())
    writer.writeheader()
    for r in records:
        safe = {k: str(v) if isinstance(v, (list, dict)) else v for k, v in r.items()}
        writer.writerow(safe)
    resp = make_response(output.getvalue())
    resp.headers['Content-Type'] = 'text/csv'
    resp.headers['Content-Disposition'] = f'attachment; filename={collection}.csv'
    return resp
