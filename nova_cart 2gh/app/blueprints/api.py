"""API blueprint - AJAX endpoints"""
from flask import Blueprint, jsonify, request, session
from utils.storage import get_record, save_record, get_collection, find_records, find_record

api_bp = Blueprint('api', __name__)


@api_bp.route('/ad-click/<int:ad_id>', methods=['POST'])
def ad_click(ad_id):
    ad = get_record('ads', ad_id)
    if ad:
        ad['clicks'] = ad.get('clicks', 0) + 1
        save_record('ads', ad)
    return jsonify({'ok': True})


@api_bp.route('/search-suggestions')
def search_suggestions():
    q = request.args.get('q', '').lower().strip()
    if len(q) < 2:
        return jsonify([])
    products = get_collection('products')
    results = []
    for p in products:
        if q in p.get('name', '').lower() and p.get('is_active'):
            results.append({
                'name': p['name'], 'slug': p['slug'],
                'price': p.get('discount_price') or p.get('price', 0),
                'img': p['images'][0] if p.get('images') else '/static/images/no-image.png'
            })
        if len(results) >= 6:
            break
    return jsonify(results)


@api_bp.route('/cart/count')
def cart_count():
    uid = session.get('user_id')
    count = len(find_records('cart', user_id=uid)) if uid else 0
    return jsonify({'count': count})


@api_bp.route('/newsletter', methods=['POST'])
def newsletter():
    email = (request.json.get('email') if request.is_json else request.form.get('email', '')).strip().lower()
    if not email or '@' not in email:
        return jsonify({'status': 'error', 'msg': 'Invalid email'})
    if find_record('newsletter', email=email):
        return jsonify({'status': 'exists', 'msg': 'Already subscribed!'})
    save_record('newsletter', {'email': email})
    return jsonify({'status': 'ok', 'msg': 'Subscribed! Thank you. 🎉'})
