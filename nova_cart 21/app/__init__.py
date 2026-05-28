"""Nova Cart - Flask Application Factory"""
import os, sys, hmac, hashlib, secrets, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from flask import Flask, session, request, abort, jsonify

CSRF_EXEMPT = ['/api/', '/cart/add/', '/cart/update/', '/cart/remove/',
               '/cart/apply-coupon', '/cart/remove-coupon',
               '/shop/wishlist/', '/shop/review/', '/marketing/referral/use',
               '/marketing/notifications/']

def create_app():
    # Use absolute paths so it works both locally and on Render
    _base = os.path.dirname(os.path.abspath(__file__))
    _tmpl = os.path.join(_base, 'templates')
    _static = os.path.join(_base, 'static')
    app = Flask(__name__,
                template_folder=_tmpl,
                static_folder=_static)

    # Register all template subdirectories explicitly for Render compatibility
    from jinja2 import FileSystemLoader, ChoiceLoader
    subdirs = []
    for root, dirs, files in os.walk(_tmpl):
        subdirs.append(root)
    app.jinja_loader = ChoiceLoader([
        FileSystemLoader(subdirs),
        FileSystemLoader(_tmpl),
    ])
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'nova-cart-ultra-secret-2024-change-me')
    app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
    app.config['SESSION_COOKIE_HTTPONLY'] = True
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

    def generate_csrf():
        if '_csrf' not in session:
            session['_csrf'] = secrets.token_hex(24)
        return session['_csrf']

    def validate_csrf(token):
        expected = session.get('_csrf', '')
        if not expected: return True
        return hmac.compare_digest(expected, token or '')

    app.jinja_env.globals['csrf_token'] = generate_csrf

    @app.before_request
    def csrf_protect():
        if request.method not in ('POST', 'PUT', 'DELETE', 'PATCH'): return
        path = request.path
        for exempt in CSRF_EXEMPT:
            if path.startswith(exempt) or path == exempt.rstrip('/'): return
        token = (request.form.get('csrf_token') or
                 request.headers.get('X-CSRFToken') or
                 request.headers.get('X-Csrf-Token', ''))
        if not validate_csrf(token):
            if request.is_json:
                return jsonify({'status': 'error', 'msg': 'Session expired, please refresh'}), 403
            abort(403)

    from utils.storage import init_storage
    init_storage()
    from utils.seed import seed_defaults
    seed_defaults()

    from app.blueprints.main import main_bp
    from app.blueprints.auth import auth_bp
    from app.blueprints.shop import shop_bp
    from app.blueprints.cart import cart_bp
    from app.blueprints.admin import admin_bp
    from app.blueprints.seller import seller_bp
    from app.blueprints.pages import pages_bp
    from app.blueprints.api import api_bp
    from app.blueprints.marketing import marketing_bp
    from app.blueprints.analytics_bp import analytics_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(shop_bp, url_prefix='/shop')
    app.register_blueprint(cart_bp, url_prefix='/cart')
    app.register_blueprint(admin_bp, url_prefix='/x-admin-9f3k2')
    app.register_blueprint(seller_bp, url_prefix='/seller')
    app.register_blueprint(pages_bp, url_prefix='/page')
    app.register_blueprint(api_bp, url_prefix='/api')
    app.register_blueprint(marketing_bp, url_prefix='/marketing')
    app.register_blueprint(analytics_bp, url_prefix='/analytics')

    from app.context import inject_globals
    app.context_processor(inject_globals)

    from utils.storage import get_record
    app.jinja_env.globals['get_product'] = lambda pid: get_record('products', pid)

    @app.errorhandler(404)
    def not_found(e):
        from flask import render_template
        return render_template('404.html'), 404

    @app.errorhandler(403)
    def forbidden(e):
        from flask import render_template
        if request.is_json:
            return jsonify({'status': 'error', 'msg': 'Forbidden'}), 403
        return render_template('403.html'), 403

    return app
