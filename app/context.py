"""Global template context processor"""
from flask import session
from utils.storage import get_all_settings, get_collection, get_record, find_record, find_records
from datetime import datetime


def get_ads_for(placement):
    return [a for a in get_collection('ads')
            if a.get('is_active') and a.get('placement') == placement]


def inject_globals():
    settings = get_all_settings()

    navbar_links = sorted(
        [l for l in get_collection('nav_links') if l.get('location') == 'navbar' and l.get('is_active')],
        key=lambda x: x.get('sort_order', 0))
    footer_links = sorted(
        [l for l in get_collection('nav_links') if l.get('location') == 'footer' and l.get('is_active')],
        key=lambda x: x.get('sort_order', 0))
    categories = sorted(
        [c for c in get_collection('categories') if c.get('is_active')],
        key=lambda x: x.get('sort_order', 0))

    uid = session.get('user_id')
    cart_count = len(find_records('cart', user_id=uid)) if uid else 0
    current_user = get_record('users', uid) if uid else None

    current_seller = None
    if uid and current_user and current_user.get('role') in ('seller', 'admin', 'pending_seller'):
        current_seller = find_record('sellers', user_id=uid)

    announcement = (settings.get('announcement_text', '')
                    if settings.get('announcement_active') == 'true' else '')

    # Notification count
    notif_count = 0
    loyalty_points = 0
    if uid:
        notif_count = len([n for n in find_records('notifications', user_id=uid) if not n.get('read')])
        loyalty_rec = find_record('loyalty', user_id=uid)
        loyalty_points = loyalty_rec.get('points', 0) if loyalty_rec else 0

    # External links
    external_links = []
    for key, label in [('netlify_about','About Us'),('netlify_contact','Contact'),
                       ('netlify_privacy','Privacy'),('netlify_refund','Refunds'),
                       ('netlify_shipping','Shipping')]:
        url = settings.get(key, '')
        if url and url.startswith('http'):
            external_links.append({'label': label, 'url': url})
    for i in range(1, 4):
        lbl = settings.get(f'custom_link_{i}_label', '')
        url = settings.get(f'custom_link_{i}_url', '')
        if lbl and url:
            external_links.append({'label': lbl, 'url': url})

    return dict(
        settings=settings,
        navbar_links=navbar_links,
        footer_links=footer_links,
        categories=categories,
        cart_count=cart_count,
        current_user=current_user,
        current_seller=current_seller,
        announcement=announcement,
        external_links=external_links,
        get_ads=get_ads_for,
        notif_count=notif_count,
        loyalty_points=loyalty_points,
    )
