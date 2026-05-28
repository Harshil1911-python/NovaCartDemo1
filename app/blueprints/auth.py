"""Auth blueprint"""
from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from utils.storage import find_record, save_record, get_collection
from utils.auth import hash_password, check_password, is_valid_email, get_current_user
import secrets

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if session.get('user_id'):
        return redirect(url_for('main.index'))
    error = None
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        user = find_record('users', email=email)
        if user and check_password(password, user.get('password', '')):
            if not user.get('is_active', True):
                error = 'Your account has been suspended.'
            else:
                session['user_id'] = user['id']
                session.permanent = True
                flash('Welcome back, ' + user['name'] + '!', 'success')
                next_url = request.args.get('next') or url_for('main.index')
                return redirect(next_url)
        else:
            error = 'Invalid email or password.'
    return render_template('auth/login.html', error=error)


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if session.get('user_id'):
        return redirect(url_for('main.index'))
    error = None
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        confirm = request.form.get('confirm_password', '')
        if not name or not email or not password:
            error = 'All fields are required.'
        elif not is_valid_email(email):
            error = 'Invalid email address.'
        elif len(password) < 6:
            error = 'Password must be at least 6 characters.'
        elif password != confirm:
            error = 'Passwords do not match.'
        elif find_record('users', email=email):
            error = 'Email already registered.'
        else:
            save_record('users', {
                'name': name, 'email': email,
                'password': hash_password(password),
                'role': 'customer', 'is_active': True,
                'avatar': '', 'phone': '',
            })
            user = find_record('users', email=email)
            session['user_id'] = user['id']
            flash('Account created! Welcome to Nova Cart.', 'success')
            return redirect(url_for('main.index'))
    return render_template('auth/register.html', error=error)


@auth_bp.route('/logout')
def logout():
    session.clear()
    flash('Logged out successfully.', 'info')
    return redirect(url_for('main.index'))


@auth_bp.route('/profile', methods=['GET', 'POST'])
def profile():
    uid = session.get('user_id')
    if not uid:
        return redirect(url_for('auth.login'))
    from utils.storage import get_record
    user = get_record('users', uid)
    if request.method == 'POST':
        user['name'] = request.form.get('name', user['name']).strip()
        user['phone'] = request.form.get('phone', '').strip()
        save_record('users', user)
        flash('Profile updated!', 'success')
    from utils.storage import find_records
    orders = find_records('orders', user_id=uid)
    wishlist = find_records('wishlist', user_id=uid)
    addresses = find_records('addresses', user_id=uid)
    return render_template('auth/profile.html', user=user, orders=orders, wishlist=wishlist, addresses=addresses)
