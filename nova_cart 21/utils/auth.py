"""Auth utilities for Nova Cart"""
import hashlib
import secrets
import re
from functools import wraps
from flask import session, redirect, url_for, flash, abort
from utils.storage import get_record, find_record


def hash_password(password):
    salt = secrets.token_hex(16)
    hashed = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 260000)
    return f"{salt}${hashed.hex()}"


def check_password(password, stored):
    try:
        salt, hashed = stored.split('$', 1)
        check = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 260000)
        return check.hex() == hashed
    except Exception:
        return False


def get_current_user():
    uid = session.get('user_id')
    if not uid:
        return None
    return get_record('users', uid)


def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('user_id'):
            flash('Please log in to continue.', 'warning')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated


def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        uid = session.get('user_id')
        if not uid:
            return redirect(url_for('auth.login'))
        user = get_record('users', uid)
        if not user or user.get('role') != 'admin':
            abort(403)
        return f(*args, **kwargs)
    return decorated


def seller_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        uid = session.get('user_id')
        if not uid:
            flash('Please log in to continue.', 'warning')
            return redirect(url_for('auth.login'))
        user = get_record('users', uid)
        if not user or user.get('role') not in ('seller', 'admin'):
            flash('Seller account required.', 'danger')
            return redirect(url_for('main.index'))
        return f(*args, **kwargs)
    return decorated


def is_valid_email(email):
    return bool(re.match(r'^[^@\s]+@[^@\s]+\.[^@\s]+$', email))


def sanitize_input(text):
    """Basic XSS prevention"""
    if not isinstance(text, str):
        return text
    return text.replace('<', '&lt;').replace('>', '&gt;').replace('"', '&quot;')
