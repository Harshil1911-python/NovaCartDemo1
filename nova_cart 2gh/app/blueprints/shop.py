"""Shop blueprint"""
from flask import Blueprint, render_template, request, redirect, url_for, session, jsonify
from utils.storage import get_collection, find_record, save_record, find_records, get_record, delete_record

shop_bp = Blueprint('shop', __name__)


def _enrich(p):
    cat = find_record('categories', id=p.get('category_id'))
    p['category_name'] = cat['name'] if cat else ''
    p['category_slug'] = cat['slug'] if cat else ''
    p['_reviews'] = find_records('reviews', product_id=p['id'])
    return p


@shop_bp.route('/')
def listing():
    products = [p for p in get_collection('products') if p.get('is_active')]
    category_slug = request.args.get('category', '')
    min_price = request.args.get('min_price', 0, type=float)
    max_price = request.args.get('max_price', 999999, type=float)
    sort = request.args.get('sort', 'newest')
    sale_only = request.args.get('sale', '')
    rating_filter = request.args.get('rating', 0, type=int)
    q = request.args.get('q', '').strip().lower()
    page = request.args.get('page', 1, type=int)
    per_page = 16

    selected_category = None
    if category_slug:
        selected_category = find_record('categories', slug=category_slug)
        if selected_category:
            products = [p for p in products if p.get('category_id') == selected_category['id']]

    if q:
        products = [p for p in products if
            q in p.get('name', '').lower() or q in p.get('tags', '').lower() or
            q in p.get('description', '').lower()]

    if sale_only:
        products = [p for p in products if p.get('discount_price')]

    products = [p for p in products if
        (p.get('discount_price') or p.get('price', 0)) >= min_price and
        (p.get('discount_price') or p.get('price', 0)) <= max_price]

    # Enrich (needed for rating filter)
    products = [_enrich(p) for p in products]

    if rating_filter:
        def avg_rating(p):
            reviews = p.get('_reviews', [])
            return (sum(r['rating'] for r in reviews) / len(reviews)) if reviews else 0
        products = [p for p in products if avg_rating(p) >= rating_filter]

    if sort == 'price_asc':
        products.sort(key=lambda x: x.get('discount_price') or x.get('price', 0))
    elif sort == 'price_desc':
        products.sort(key=lambda x: x.get('discount_price') or x.get('price', 0), reverse=True)
    elif sort == 'newest':
        products.sort(key=lambda x: x.get('created_at', ''), reverse=True)
    elif sort == 'popular':
        products.sort(key=lambda x: x.get('views', 0), reverse=True)
    elif sort == 'rating':
        products.sort(key=lambda x: (sum(r['rating'] for r in x.get('_reviews',[])) / len(x.get('_reviews',[]))) if x.get('_reviews') else 0, reverse=True)

    total = len(products)
    total_pages = max(1, (total + per_page - 1) // per_page)
    products = products[(page - 1) * per_page: page * per_page]
    categories = [c for c in get_collection('categories') if c.get('is_active')]

    return render_template('shop/listing.html',
        products=products, categories=categories,
        selected_category=selected_category, category_slug=category_slug,
        sort=sort, q=q, page=page, total_pages=total_pages, total=total,
        min_price=min_price, max_price=max_price, rating_filter=rating_filter,
        sale_only=sale_only)


@shop_bp.route('/category/<slug>')
def category(slug):
    return redirect(url_for('shop.listing', category=slug))


@shop_bp.route('/product/<slug>')
def product_detail(slug):
    product = find_record('products', slug=slug)
    if not product or not product.get('is_active'):
        return render_template('404.html'), 404

    product['views'] = product.get('views', 0) + 1
    save_record('products', product)

    category = find_record('categories', id=product.get('category_id'))
    related = [_enrich(p) for p in get_collection('products')
               if p.get('category_id') == product.get('category_id')
               and p['id'] != product['id'] and p.get('is_active')][:6]
    reviews = find_records('reviews', product_id=product['id'])
    seller = find_record('sellers', id=product['seller_id']) if product.get('seller_id') else None
    uid = session.get('user_id')
    in_wishlist = bool(uid and find_record('wishlist', user_id=uid, product_id=product['id']))
    from datetime import datetime
    is_sponsored = bool(find_record('sponsored', product_id=product['id'], is_active=True))

    # Recently viewed - store in session
    rv = session.get('recently_viewed', [])
    if product['id'] not in rv:
        rv.insert(0, product['id'])
    session['recently_viewed'] = rv[:8]

    # Recently viewed products (excluding current)
    rv_products = []
    for pid in session.get('recently_viewed', []):
        if pid != product['id']:
            rp = get_record('products', pid)
            if rp and rp.get('is_active'):
                rv_products.append(_enrich(rp))
    rv_products = rv_products[:4]

    # Build variant options from product
    variants = product.get('variants', [])  # list of {name, options:[]}
    size_chart = product.get('size_chart', '')

    return render_template('shop/product.html',
        product=product, category=category, related=related,
        reviews=reviews, seller=seller, in_wishlist=in_wishlist,
        is_sponsored=is_sponsored, recently_viewed=rv_products,
        variants=variants, size_chart=size_chart)


@shop_bp.route('/search')
def search():
    return redirect(url_for('shop.listing', q=request.args.get('q', '')))


@shop_bp.route('/wishlist/toggle/<int:product_id>', methods=['POST'])
def toggle_wishlist(product_id):
    uid = session.get('user_id')
    if not uid:
        return jsonify({'status': 'login_required'})
    existing = find_record('wishlist', user_id=uid, product_id=product_id)
    if existing:
        delete_record('wishlist', existing['id'])
        return jsonify({'status': 'removed'})
    save_record('wishlist', {'user_id': uid, 'product_id': product_id})
    return jsonify({'status': 'added'})


@shop_bp.route('/review/<int:product_id>', methods=['POST'])
def add_review(product_id):
    uid = session.get('user_id')
    if not uid:
        flash('Please login to review.', 'warning')
        return redirect(request.referrer or '/')
    user = get_record('users', uid)
    rating = request.form.get('rating', 5, type=int)
    comment = request.form.get('comment', '').strip()
    if comment:
        save_record('reviews', {
            'product_id': product_id, 'user_id': uid,
            'user_name': user.get('name', 'Customer'),
            'rating': max(1, min(5, rating)), 'comment': comment,
        })
    product = find_record('products', id=product_id)
    return redirect(url_for('shop.product_detail', slug=product['slug']) if product else '/')


@shop_bp.route('/store/<seller_slug>')
def seller_store(seller_slug):
    seller = find_record('sellers', slug=seller_slug)
    if not seller:
        return render_template('404.html'), 404
    products = [_enrich(p) for p in find_records('products', seller_id=seller['id']) if p.get('is_active')]
    seller_user = get_record('users', seller.get('user_id'))
    return render_template('shop/store.html', seller=seller, products=products, seller_user=seller_user)


@shop_bp.route('/compare')
def compare():
    ids_str = request.args.get('ids', '')
    ids = [int(i) for i in ids_str.split(',') if i.strip().isdigit()][:3]
    products = [_enrich(get_record('products', i)) for i in ids if get_record('products', i)]
    return render_template('shop/compare.html', products=products)
