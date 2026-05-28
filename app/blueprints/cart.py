"""Cart and Checkout blueprint"""
from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify
from utils.storage import find_record, find_records, save_record, delete_record, get_record, get_collection, get_setting
import secrets

cart_bp = Blueprint('cart', __name__)


def _get_cart(uid):
    items = find_records('cart', user_id=uid)
    enriched = []
    for item in items:
        p = get_record('products', item['product_id'])
        if p and p.get('is_active'):
            item['product'] = p
            item['subtotal'] = (p.get('discount_price') or p.get('price', 0)) * item.get('quantity', 1)
            enriched.append(item)
    return enriched


@cart_bp.route('/')
def view_cart():
    uid = session.get('user_id')
    if not uid:
        flash('Please login to view your cart.', 'warning')
        return redirect(url_for('auth.login'))
    items = _get_cart(uid)
    total = sum(i['subtotal'] for i in items)
    # Suggested products for empty cart
    suggested = []
    if not items:
        all_p = [p for p in get_collection('products') if p.get('is_active') and p.get('is_trending')][:4]
        suggested = all_p
    return render_template('shop/cart.html', items=items, total=total, suggested=suggested)


@cart_bp.route('/add/<int:product_id>', methods=['POST'])
def add_to_cart(product_id):
    uid = session.get('user_id')
    if not uid:
        return jsonify({'status': 'login_required'})
    qty = request.json.get('quantity', 1) if request.is_json else int(request.form.get('quantity', 1))
    product = get_record('products', product_id)
    if not product or not product.get('is_active'):
        return jsonify({'status': 'error', 'msg': 'Product not found'})
    if product.get('stock', 0) <= 0:
        return jsonify({'status': 'error', 'msg': 'Out of stock'})
    existing = find_record('cart', user_id=uid, product_id=product_id)
    if existing:
        existing['quantity'] = existing.get('quantity', 1) + qty
        save_record('cart', existing)
    else:
        save_record('cart', {'user_id': uid, 'product_id': product_id, 'quantity': qty})
    cart_count = len(find_records('cart', user_id=uid))
    if request.is_json:
        return jsonify({'status': 'added', 'cart_count': cart_count})
    flash('Added to cart!', 'success')
    return redirect(request.referrer or url_for('shop.listing'))


@cart_bp.route('/update/<int:item_id>', methods=['POST'])
def update_cart(item_id):
    uid = session.get('user_id')
    if not uid:
        return jsonify({'status': 'error'})
    item = get_record('cart', item_id)
    if not item or item.get('user_id') != uid:
        return jsonify({'status': 'error'})
    qty = request.json.get('quantity', 1) if request.is_json else int(request.form.get('quantity', 1))
    if qty <= 0:
        delete_record('cart', item_id)
    else:
        item['quantity'] = qty
        save_record('cart', item)
    return jsonify({'status': 'ok'})


@cart_bp.route('/remove/<int:item_id>', methods=['POST'])
def remove_from_cart(item_id):
    uid = session.get('user_id')
    if not uid:
        return redirect(url_for('auth.login'))
    item = get_record('cart', item_id)
    if item and item.get('user_id') == uid:
        delete_record('cart', item_id)
    if request.is_json:
        return jsonify({'status': 'removed'})
    return redirect(url_for('cart.view_cart'))


@cart_bp.route('/apply-coupon', methods=['POST'])
def apply_coupon():
    code = (request.json.get('code') if request.is_json else request.form.get('code', '')).strip().upper()
    uid = session.get('user_id')
    if not uid:
        return jsonify({'status': 'error', 'msg': 'Login required'})
    coupon = find_record('coupons', code=code, is_active=True)
    if not coupon:
        return jsonify({'status': 'error', 'msg': 'Invalid or expired coupon'})
    items = _get_cart(uid)
    total = sum(i['subtotal'] for i in items)
    discount_type = coupon.get('discount_type', 'percent')
    discount_value = float(coupon.get('discount_value', 0))
    if discount_type == 'percent':
        discount = round(total * discount_value / 100, 2)
    else:
        discount = min(discount_value, total)
    session['coupon'] = {'code': code, 'discount': discount, 'type': discount_type, 'value': discount_value}
    return jsonify({'status': 'ok', 'discount': discount, 'msg': f'Coupon applied! You save ₹{discount:.0f}'})


@cart_bp.route('/remove-coupon', methods=['POST'])
def remove_coupon():
    session.pop('coupon', None)
    return jsonify({'status': 'ok'})


@cart_bp.route('/checkout', methods=['GET', 'POST'])
def checkout():
    uid = session.get('user_id')
    if not uid:
        flash('Please login to checkout.', 'warning')
        return redirect(url_for('auth.login'))
    items = _get_cart(uid)
    if not items:
        flash('Your cart is empty.', 'info')
        return redirect(url_for('shop.listing'))
    subtotal = sum(i['subtotal'] for i in items)
    coupon_data = session.get('coupon', {})
    discount = coupon_data.get('discount', 0)
    total = max(0, subtotal - discount)
    user = get_record('users', uid)
    addresses = find_records('addresses', user_id=uid)
    coupons_available = [c for c in get_collection('coupons') if c.get('is_active')]

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip()
        phone = request.form.get('phone', '').strip()
        address = request.form.get('address', '').strip()
        city = request.form.get('city', '').strip()
        state = request.form.get('state', '').strip()
        pincode = request.form.get('pincode', '').strip()
        payment_method = request.form.get('payment_method', 'cod')

        if not all([name, email, phone, address, city, pincode]):
            flash('Please fill all required fields.', 'danger')
            return render_template('shop/checkout.html', items=items, subtotal=subtotal,
                                   discount=discount, total=total, user=user, addresses=addresses,
                                   coupon_data=coupon_data, coupons_available=coupons_available)

        order_id = 'NC-' + secrets.token_hex(4).upper()
        order_items = [{'product_id': i['product_id'], 'name': i['product']['name'],
                        'price': i['product'].get('discount_price') or i['product']['price'],
                        'quantity': i['quantity'], 'subtotal': i['subtotal']} for i in items]

        save_record('orders', {
            'order_id': order_id, 'user_id': uid,
            'order_lines': order_items, 'subtotal': subtotal,
            'discount': discount, 'coupon_code': coupon_data.get('code', ''),
            'total': total, 'name': name, 'email': email, 'phone': phone,
            'address': address, 'city': city, 'state': state, 'pincode': pincode,
            'payment_method': payment_method, 'status': 'pending',
            'payment_status': 'pending' if payment_method == 'cod' else 'paid',
        })

        # ── Decrement stock ──────────────────────────────────
        for item in items:
            p = get_record('products', item['product_id'])
            if p:
                p['stock'] = max(0, p.get('stock', 0) - item['quantity'])
                save_record('products', p)

        # ── Award loyalty points (1 point per ₹10 spent) ────
        try:
            from app.blueprints.marketing import add_points, send_notification
            pts = int(total // 10)
            if pts > 0:
                add_points(uid, pts, f'order_{order_id}')
                send_notification(uid, '🎉 Points Earned!',
                    f'You earned {pts} loyalty points for order #{order_id}',
                    'success', f'/marketing/loyalty')
        except Exception:
            pass

        # Save address
        if request.form.get('save_address'):
            save_record('addresses', {
                'user_id': uid, 'name': name, 'phone': phone,
                'address': address, 'city': city, 'state': state, 'pincode': pincode,
            })

        # Clear cart + coupon
        for item in items:
            delete_record('cart', item['id'])
        session.pop('coupon', None)

        flash('Order placed successfully!', 'success')
        return redirect(url_for('cart.order_confirmation', order_id=order_id))

    return render_template('shop/checkout.html', items=items, subtotal=subtotal,
                           discount=discount, total=total, user=user, addresses=addresses,
                           coupon_data=coupon_data, coupons_available=coupons_available)


@cart_bp.route('/order/<order_id>')
def order_confirmation(order_id):
    uid = session.get('user_id')
    if not uid:
        return redirect(url_for('auth.login'))
    order = find_record('orders', order_id=order_id, user_id=uid)
    if not order:
        return render_template('404.html'), 404
    order_lines = order.get('order_lines', [])
    return render_template('shop/order_confirmation.html', order=order, order_lines=order_lines)


@cart_bp.route('/track/<order_id>')
def track_order(order_id):
    uid = session.get('user_id')
    order = None
    if uid:
        order = find_record('orders', order_id=order_id, user_id=uid)
    if not order:
        # allow by order_id + email
        email = request.args.get('email', '')
        if email:
            order = find_record('orders', order_id=order_id, email=email)
    if not order:
        flash('Order not found. Check your Order ID.', 'danger')
        return redirect(url_for('main.index'))
    order_lines = order.get('order_lines', [])
    return render_template('shop/track_order.html', order=order, order_lines=order_lines)
