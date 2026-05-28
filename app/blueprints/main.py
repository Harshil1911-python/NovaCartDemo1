"""Main / Homepage blueprint"""
from flask import Blueprint, render_template
from utils.storage import get_collection, find_records, get_all_settings, get_setting
from datetime import datetime

main_bp = Blueprint('main', __name__)


def get_sponsored_products():
    now = datetime.utcnow().isoformat()
    sponsored_ids = [
        s['product_id'] for s in get_collection('sponsored')
        if s.get('is_active') and s.get('expires_at', '') > now
    ]
    if not sponsored_ids:
        return []
    products = get_collection('products')
    return [p for p in products if p.get('id') in sponsored_ids and p.get('is_active')]


@main_bp.route('/')
def index():
    settings = get_all_settings()
    if settings.get('maintenance_mode') == 'true':
        return render_template('maintenance.html', settings=settings)

    products = [p for p in get_collection('products') if p.get('is_active')]
    trending = [p for p in products if p.get('is_trending')][:8]
    featured = [p for p in products if p.get('is_featured')][:8]
    new_arrivals = sorted(
        [p for p in products if p.get('is_new_arrival')],
        key=lambda x: x.get('created_at', ''), reverse=True
    )[:8]
    sponsored = get_sponsored_products()[:4]

    # Active banners
    now = datetime.utcnow().isoformat()
    banners = [
        b for b in get_collection('banners')
        if b.get('is_active') and
        (not b.get('start_date') or b.get('start_date', '') <= now) and
        (not b.get('end_date') or b.get('end_date', '') >= now)
    ]

    # Active ads
    ads = [a for a in get_collection('ads') if a.get('is_active')]
    ads_homepage = [a for a in ads if a.get('placement') == 'homepage']

    # Testimonials
    testimonials = [t for t in get_collection('testimonials') if t.get('is_active')]

    # Flash sale
    flash_sale_end = settings.get('flash_sale_end', '')
    flash_products = [p for p in products if p.get('is_flash_sale')][:6]

    return render_template('shop/home.html',
        trending=trending,
        featured=featured,
        new_arrivals=new_arrivals,
        sponsored=sponsored,
        banners=banners,
        ads_homepage=ads_homepage,
        testimonials=testimonials,
        flash_sale_end=flash_sale_end,
        flash_products=flash_products,
    )


@main_bp.route('/sitemap.xml')
def sitemap():
    products = [p for p in get_collection('products') if p.get('is_active')]
    categories = [c for c in get_collection('categories') if c.get('is_active')]
    pages = [p for p in get_collection('pages') if p.get('is_published')]
    from flask import make_response
    xml = render_template('sitemap.xml', products=products, categories=categories, pages=pages)
    resp = make_response(xml)
    resp.headers['Content-Type'] = 'application/xml'
    return resp


@main_bp.route('/robots.txt')
def robots():
    from flask import make_response
    txt = "User-agent: *\nAllow: /\nDisallow: /x-admin-9f3k2/\nDisallow: /seller/dashboard\n"
    resp = make_response(txt)
    resp.headers['Content-Type'] = 'text/plain'
    return resp
