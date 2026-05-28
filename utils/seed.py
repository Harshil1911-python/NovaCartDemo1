"""Seed default data into data.dat on first launch"""
from utils.storage import get_collection, save_record, save_setting, find_record
from utils.auth import hash_password
from utils.slugify import slugify


def seed_defaults():
    _seed_settings()
    _seed_admin()
    _seed_categories()
    _seed_products()
    _seed_nav_links()
    _seed_pages()
    _seed_testimonials()


def _seed_settings():
    defaults = {
        # Branding
        'site_name': 'Nova Cart',
        'site_tagline': 'Your Daily Shopping Destination',
        'site_logo': '',
        'site_favicon': '',
        'site_email': 'hello@novacart.com',
        'site_phone': '+91 98765 43210',
        'site_address': 'Mumbai, Maharashtra, India',
        'whatsapp_number': '919876543210',
        # Theme
        'primary_color': '#6C63FF',
        'secondary_color': '#FF6584',
        'accent_color': '#43E97B',
        'bg_color': '#F8F9FA',
        'navbar_color': '#FFFFFF',
        'footer_color': '#1A1A2E',
        'text_color': '#2D3748',
        'font_family': 'Inter, sans-serif',
        'button_radius': '8px',
        'card_radius': '12px',
        'dark_mode': 'false',
        'custom_css': '',
        'custom_js': '',
        # Homepage sections (enabled/disabled)
        'section_hero': 'true',
        'section_categories': 'true',
        'section_trending': 'true',
        'section_featured': 'true',
        'section_new_arrivals': 'true',
        'section_ads': 'true',
        'section_testimonials': 'true',
        'section_flash_sale': 'true',
        # Social
        'social_facebook': 'https://facebook.com',
        'social_instagram': 'https://instagram.com',
        'social_twitter': 'https://twitter.com',
        'social_youtube': '',
        'social_whatsapp': '',
        # Misc
        'currency_symbol': '₹',
        'currency_code': 'INR',
        'maintenance_mode': 'false',
        'maintenance_message': 'We are upgrading Nova Cart. Back soon!',
        'announcement_text': '🎉 Free Shipping on orders above ₹499! Use code FREESHIP',
        'announcement_active': 'true',
        'popup_title': '',
        'popup_message': '',
        'popup_active': 'false',
        'flash_sale_end': '',
        'live_visitors': '0',
        # Customization
        'show_whatsapp_fab': 'true',
        'show_social_proof': 'true',
        'show_live_visitors': 'false',
        'navbar_sticky': 'true',
        'loader_active': 'false',
        'loader_color': '#6C63FF',
        'show_rating_in_card': 'true',
        'show_stock_in_card': 'false',
        'show_breadcrumb': 'true',
        'product_zoom': 'true',
        'products_per_row': '4',
        'btn_style': 'rounded',
        'product_card_style': 'default',
        'footer_style': 'dark',
        'card_shadow': 'default',
        'hero_gradient_from': '#1A1A2E',
        'hero_gradient_to': '#0F3460',
        'custom_badge_text': '{pct}% OFF',
        'sale_badge_color': '#FF6584',
        'header_scripts': '',
        'body_end_scripts': '',
        'netlify_about': '',
        'netlify_contact': '',
        'netlify_privacy': '',
        'netlify_refund': '',
        'netlify_shipping': '',
        'admin_pin': '',
        # Marketing
        'points_value': '0.5',
        'referral_bonus': '100',
    }
    for key, value in defaults.items():
        if not find_record('settings', key=key):
            save_setting(key, value)


def _seed_admin():
    if not find_record('users', email='admin@novacart.com'):
        save_record('users', {
            'name': 'Admin',
            'email': 'admin@novacart.com',
            'password': hash_password('admin@123'),
            'role': 'admin',
            'is_active': True,
            'avatar': '',
            'phone': '',
        })


def _seed_categories():
    if get_collection('categories'):
        return
    cats = [
        {'name': 'Electronics', 'icon': 'fas fa-bolt', 'color': '#6C63FF'},
        {'name': 'Daily Essentials', 'icon': 'fas fa-shopping-basket', 'color': '#43E97B'},
        {'name': 'Perfumes', 'icon': 'fas fa-spray-can', 'color': '#FF6584'},
        {'name': 'Car Accessories', 'icon': 'fas fa-car', 'color': '#F093FB'},
        {'name': 'Smart Gadgets', 'icon': 'fas fa-microchip', 'color': '#4FACFE'},
        {'name': 'Kitchen', 'icon': 'fas fa-utensils', 'color': '#43E97B'},
        {'name': 'Lifestyle', 'icon': 'fas fa-heart', 'color': '#FF6584'},
        {'name': 'Accessories', 'icon': 'fas fa-gem', 'color': '#F093FB'},
    ]
    for c in cats:
        save_record('categories', {
            'name': c['name'],
            'slug': slugify(c['name']),
            'icon': c['icon'],
            'color': c['color'],
            'image': '',
            'description': f'Shop the best {c["name"]} on Nova Cart',
            'is_active': True,
            'sort_order': 0,
        })


def _seed_products():
    if get_collection('products'):
        return
    products = [
        {
            'name': 'Premium Wireless Earbuds',
            'price': 1999, 'discount_price': 1299,
            'category_slug': 'electronics',
            'tags': 'earbuds,wireless,audio',
            'short_description': 'True wireless stereo with 30hr battery life',
            'description': 'Experience crystal-clear audio with our Premium Wireless Earbuds. Features active noise cancellation, 30-hour battery life, IPX5 water resistance, and touch controls.',
            'stock': 50, 'is_featured': True, 'is_trending': True, 'is_new_arrival': True,
        },
        {
            'name': 'Fast Charging 65W Adapter',
            'price': 899, 'discount_price': 599,
            'category_slug': 'electronics',
            'tags': 'charger,fast charge,adapter',
            'short_description': '65W GaN charger, charges phone in 30 mins',
            'description': 'Compact 65W GaN technology fast charger. Compatible with all USB-C devices. Charges your smartphone from 0-100% in just 30 minutes.',
            'stock': 100, 'is_featured': True, 'is_trending': False, 'is_new_arrival': True,
        },
        {
            'name': 'Luxury Oud Perfume 100ml',
            'price': 2499, 'discount_price': 1799,
            'category_slug': 'perfumes',
            'tags': 'perfume,oud,luxury,fragrance',
            'short_description': 'Premium oud fragrance lasting 12+ hours',
            'description': 'A rich, warm oud fragrance with notes of sandalwood, amber, and musk. Long-lasting formula that stays fresh for 12+ hours.',
            'stock': 30, 'is_featured': True, 'is_trending': True, 'is_new_arrival': False,
        },
        {
            'name': 'Car Air Freshener - Ocean Breeze',
            'price': 399, 'discount_price': 249,
            'category_slug': 'car-accessories',
            'tags': 'car,freshener,perfume',
            'short_description': 'Long-lasting ocean breeze car fragrance',
            'description': 'Keep your car smelling fresh with our Ocean Breeze air freshener. Lasts up to 60 days. Easy clip-on design.',
            'stock': 200, 'is_featured': False, 'is_trending': True, 'is_new_arrival': True,
        },
        {
            'name': 'Smart LED Bulb RGB 12W',
            'price': 799, 'discount_price': 499,
            'category_slug': 'smart-gadgets',
            'tags': 'smart,led,bulb,rgb,wifi',
            'short_description': 'WiFi controlled RGB LED, works with Alexa',
            'description': 'Transform your home lighting with our Smart RGB LED Bulb. Control via app or voice. 16 million colors, timer, and schedules.',
            'stock': 75, 'is_featured': True, 'is_trending': True, 'is_new_arrival': True,
        },
        {
            'name': 'Stainless Steel Water Bottle 1L',
            'price': 599, 'discount_price': 399,
            'category_slug': 'daily-essentials',
            'tags': 'bottle,water,steel,daily',
            'short_description': 'Double-wall insulated, keeps cold 24hrs',
            'description': 'Premium double-wall vacuum insulated stainless steel water bottle. Keeps drinks cold for 24 hours and hot for 12 hours.',
            'stock': 150, 'is_featured': False, 'is_trending': False, 'is_new_arrival': True,
        },
        {
            'name': 'Portable Blender 500ml',
            'price': 1299, 'discount_price': 899,
            'category_slug': 'kitchen',
            'tags': 'blender,portable,kitchen,smoothie',
            'short_description': 'USB rechargeable mini blender',
            'description': 'Make fresh smoothies anywhere with our USB rechargeable portable blender. 6-blade stainless steel, BPA-free, easy to clean.',
            'stock': 60, 'is_featured': True, 'is_trending': False, 'is_new_arrival': False,
        },
        {
            'name': 'Fitness Tracker Smart Band',
            'price': 2999, 'discount_price': 1999,
            'category_slug': 'lifestyle',
            'tags': 'fitness,tracker,band,health',
            'short_description': 'Heart rate, sleep, steps - all in one',
            'description': 'Track your health 24/7 with our Smart Fitness Band. Heart rate monitor, sleep tracker, step counter, and 7-day battery life.',
            'stock': 45, 'is_featured': True, 'is_trending': True, 'is_new_arrival': True,
        },
    ]
    import secrets as sec
    from utils.storage import get_collection as gc
    cats = {c['slug']: c['id'] for c in gc('categories')}
    for p in products:
        slug = slugify(p['name'])
        cat_id = cats.get(p.pop('category_slug'), 1)
        save_record('products', {
            **p,
            'slug': slug,
            'sku': 'SKU-' + sec.token_hex(4).upper(),
            'category_id': cat_id,
            'seller_id': None,
            'is_active': True,
            'images': [],
            'meta_title': p['name'],
            'meta_description': p.get('short_description', ''),
            'views': 0,
        })


def _seed_nav_links():
    if get_collection('nav_links'):
        return
    links = [
        {'label': 'Home', 'url': '/', 'location': 'navbar', 'sort_order': 1, 'is_active': True},
        {'label': 'Shop', 'url': '/shop', 'location': 'navbar', 'sort_order': 2, 'is_active': True},
        {'label': 'Electronics', 'url': '/shop/category/electronics', 'location': 'navbar', 'sort_order': 3, 'is_active': True},
        {'label': 'Deals', 'url': '/shop?sale=1', 'location': 'navbar', 'sort_order': 4, 'is_active': True},
        {'label': 'Sell on Nova Cart', 'url': '/seller/register', 'location': 'navbar', 'sort_order': 5, 'is_active': True},
        {'label': 'About Us', 'url': '/page/about-us', 'location': 'footer', 'sort_order': 1, 'is_active': True},
        {'label': 'Contact Us', 'url': '/page/contact-us', 'location': 'footer', 'sort_order': 2, 'is_active': True},
        {'label': 'Privacy Policy', 'url': '/page/privacy-policy', 'location': 'footer', 'sort_order': 3, 'is_active': True},
        {'label': 'Refund Policy', 'url': '/page/refund-policy', 'location': 'footer', 'sort_order': 4, 'is_active': True},
        {'label': 'Shipping Policy', 'url': '/page/shipping-policy', 'location': 'footer', 'sort_order': 5, 'is_active': True},
    ]
    for l in links:
        save_record('nav_links', l)


def _seed_pages():
    from utils.storage import find_record, save_record
    pages = [
        {'title': 'About Us', 'slug': 'about-us', 'is_published': True,
         'meta_title': 'About Nova Cart', 'meta_description': 'Learn about Nova Cart marketplace',
         'content': '<h2>About Nova Cart</h2><p>Nova Cart is a modern online marketplace bringing quality electronics, perfumes, gadgets, and daily essentials — all in one place at the best prices.</p><h3>Our Mission</h3><p>Making quality products accessible and affordable for everyone across India.</p><h3>Why Choose Us?</h3><ul><li>100% genuine products</li><li>Fast pan-India delivery</li><li>Easy 7-day returns</li><li>24/7 WhatsApp support</li></ul>'},
        {'title': 'Privacy Policy', 'slug': 'privacy-policy', 'is_published': True,
         'meta_title': 'Privacy Policy | Nova Cart', 'meta_description': 'How we handle your data',
         'content': '<h2>Privacy Policy</h2><p>Nova Cart collects only information needed to process your orders. We never sell your data to third parties.</p><h3>Data We Collect</h3><ul><li>Name, email, phone for orders</li><li>Delivery address for shipping</li></ul><h3>Your Rights</h3><p>Request deletion of your account anytime by emailing us.</p>'},
        {'title': 'Refund Policy', 'slug': 'refund-policy', 'is_published': True,
         'meta_title': 'Refund Policy | Nova Cart', 'meta_description': '7-day easy returns',
         'content': '<h2>Refund & Return Policy</h2><p>Return most items within <strong>7 days</strong> of delivery. Refunds processed within 5–7 business days.</p><h3>How to Return</h3><p>Contact us on WhatsApp with your Order ID and return reason.</p>'},
        {'title': 'Shipping Policy', 'slug': 'shipping-policy', 'is_published': True,
         'meta_title': 'Shipping Policy | Nova Cart', 'meta_description': 'Delivery timelines',
         'content': '<h2>Shipping Policy</h2><ul><li><strong>Metro Cities:</strong> 2–3 days</li><li><strong>Other Cities:</strong> 4–5 days</li></ul><p>FREE shipping on orders above ₹499.</p>'},
        {'title': 'Contact Us', 'slug': 'contact-us', 'is_published': True,
         'meta_title': 'Contact Nova Cart', 'meta_description': 'Get in touch',
         'content': '<h2>Contact Us</h2><p>We are here to help! Use the WhatsApp button for instant support, or email us at hello@novacart.com.</p>'},
    ]
    for p in pages:
        if not find_record('pages', slug=p['slug']):
            save_record('pages', p)


def _seed_testimonials():
    from utils.storage import get_collection, save_record
    if get_collection('testimonials'):
        return
    for t in [
        {'name': 'Rahul Sharma', 'location': 'Mumbai', 'rating': 5, 'comment': 'Amazing quality earbuds! Battery life is incredible. Delivery was super fast!', 'is_active': True},
        {'name': 'Priya Mehta', 'location': 'Delhi', 'rating': 5, 'comment': 'Ordered the oud perfume — absolutely divine. Long-lasting fragrance. Will order again!', 'is_active': True},
        {'name': 'Arjun Kumar', 'location': 'Bangalore', 'rating': 4, 'comment': 'Great smart LED bulbs. Easy app setup. Transforms the room ambiance completely.', 'is_active': True},
        {'name': 'Sneha Reddy', 'location': 'Hyderabad', 'rating': 5, 'comment': 'Fitness tracker is awesome! Accurate readings, week-long battery. Best purchase this year!', 'is_active': True},
        {'name': 'Vikram Patel', 'location': 'Ahmedabad', 'rating': 5, 'comment': 'COD worked perfectly. Product exactly as described. Nova Cart is my go-to now!', 'is_active': True},
    ]:
        save_record('testimonials', t)
