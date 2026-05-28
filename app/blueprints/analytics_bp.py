"""Analytics blueprint - charts, reports, insights"""
from flask import Blueprint, render_template, jsonify, session
from utils.storage import get_collection, find_records, get_record
from datetime import datetime, timedelta
import time

analytics_bp = Blueprint('analytics_bp', __name__)


def _admin_required(f):
    from functools import wraps
    from flask import redirect, url_for
    @wraps(f)
    def dec(*a, **kw):
        if not session.get('admin_v'):
            return redirect(url_for('admin.login'))
        return f(*a, **kw)
    return dec


@analytics_bp.route('/admin-analytics')
@_admin_required
def admin_analytics():
    orders = get_collection('orders')
    products = get_collection('products')
    users = get_collection('users')

    # Revenue by day (last 30 days)
    now = datetime.utcnow()
    daily = {}
    for i in range(30):
        d = (now - timedelta(days=i)).strftime('%Y-%m-%d')
        daily[d] = 0
    for o in orders:
        if o.get('status') == 'cancelled':
            continue
        ts = o.get('created_at', '')[:10]
        if ts in daily:
            daily[ts] = daily.get(ts, 0) + o.get('total', 0)
    daily_labels = sorted(daily.keys())
    daily_values = [round(daily[d], 2) for d in daily_labels]

    # Top products by revenue
    prod_revenue = {}
    for o in orders:
        if o.get('status') == 'cancelled':
            continue
        for item in o.get('order_lines', o.get('items', [])):
            pid = item.get('product_id')
            prod_revenue[pid] = prod_revenue.get(pid, 0) + item.get('subtotal', 0)
    top_products = sorted(prod_revenue.items(), key=lambda x: x[1], reverse=True)[:10]
    top_product_data = []
    for pid, rev in top_products:
        p = get_record('products', pid)
        if p:
            top_product_data.append({'name': p['name'][:25], 'revenue': round(rev, 2),
                                     'slug': p['slug']})

    # Category breakdown
    cat_revenue = {}
    cats = {c['id']: c['name'] for c in get_collection('categories')}
    for p in products:
        cid = p.get('category_id')
        cat_revenue[cid] = cat_revenue.get(cid, 0)
    for o in orders:
        if o.get('status') == 'cancelled':
            continue
        for item in o.get('order_lines', o.get('items', [])):
            pid = item.get('product_id')
            prod = get_record('products', pid)
            if prod:
                cid = prod.get('category_id')
                cat_revenue[cid] = cat_revenue.get(cid, 0) + item.get('subtotal', 0)

    # Order status breakdown
    status_counts = {}
    for o in orders:
        s = o.get('status', 'unknown')
        status_counts[s] = status_counts.get(s, 0) + 1

    # New users by day (last 14)
    user_daily = {}
    for i in range(14):
        d = (now - timedelta(days=i)).strftime('%Y-%m-%d')
        user_daily[d] = 0
    for u in users:
        ts = u.get('created_at', '')[:10]
        if ts in user_daily:
            user_daily[ts] = user_daily.get(ts, 0) + 1
    user_labels = sorted(user_daily.keys())
    user_values = [user_daily[d] for d in user_labels]

    # Summary stats
    total_rev = sum(o.get('total', 0) for o in orders if o.get('status') != 'cancelled')
    avg_order = total_rev / len(orders) if orders else 0
    total_customers = len([u for u in users if u.get('role') == 'customer'])

    stats = {
        'total_revenue': round(total_rev, 2),
        'total_orders': len(orders),
        'avg_order_value': round(avg_order, 2),
        'total_customers': total_customers,
        'total_products': len([p for p in products if p.get('is_active')]),
        'newsletter_subs': len(get_collection('newsletter')),
        'loyalty_users': len(get_collection('loyalty')),
    }

    return render_template('admin/analytics_full.html',
        stats=stats,
        daily_labels=daily_labels[-14:],
        daily_values=daily_values[-14:],
        user_labels=user_labels,
        user_values=user_values,
        top_products=top_product_data,
        cat_revenue={cats.get(k, 'Unknown'): round(v, 2)
                     for k, v in cat_revenue.items() if v > 0},
        status_counts=status_counts,
    )
