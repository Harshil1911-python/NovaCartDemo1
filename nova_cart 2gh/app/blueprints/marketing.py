"""Marketing blueprint - email campaigns, referrals, loyalty, notifications"""
from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify
from utils.storage import (get_collection, find_record, save_record, delete_record,
                           get_record, find_records, get_setting, save_setting)
import secrets, time
from datetime import datetime

marketing_bp = Blueprint('marketing', __name__)


# ── Loyalty Points ────────────────────────────────────────────
def get_user_points(user_id):
    rec = find_record('loyalty', user_id=user_id)
    return rec.get('points', 0) if rec else 0


def add_points(user_id, points, reason='purchase'):
    rec = find_record('loyalty', user_id=user_id)
    if rec:
        rec['points'] = rec.get('points', 0) + points
        rec['history'] = rec.get('history', [])
        rec['history'].append({'pts': points, 'reason': reason,
                               'ts': datetime.utcnow().isoformat()})
        save_record('loyalty', rec)
    else:
        save_record('loyalty', {
            'user_id': user_id, 'points': points,
            'history': [{'pts': points, 'reason': reason,
                         'ts': datetime.utcnow().isoformat()}]
        })


def redeem_points(user_id, points):
    rec = find_record('loyalty', user_id=user_id)
    if not rec or rec.get('points', 0) < points:
        return False
    rec['points'] -= points
    rec.setdefault('history', []).append({
        'pts': -points, 'reason': 'redeemed',
        'ts': datetime.utcnow().isoformat()
    })
    save_record('loyalty', rec)
    return True


@marketing_bp.route('/loyalty')
def loyalty_dashboard():
    uid = session.get('user_id')
    if not uid:
        return redirect(url_for('auth.login'))
    user = get_record('users', uid)
    rec = find_record('loyalty', user_id=uid)
    points = rec.get('points', 0) if rec else 0
    history = (rec.get('history', []) if rec else [])[-10:][::-1]
    points_value = round(points * float(get_setting('points_value', '0.5')), 2)
    return render_template('shop/loyalty.html', user=user, points=points,
                           history=history, points_value=points_value)


# ── Referral System ───────────────────────────────────────────
@marketing_bp.route('/referral')
def referral():
    uid = session.get('user_id')
    if not uid:
        return redirect(url_for('auth.login'))
    user = get_record('users', uid)
    code = user.get('referral_code') or ''
    if not code:
        code = 'NC' + secrets.token_hex(4).upper()
        user['referral_code'] = code
        save_record('users', user)
    referrals = find_records('referrals', referrer_id=uid)
    earned = sum(r.get('points_earned', 0) for r in referrals)
    return render_template('shop/referral.html', user=user, code=code,
                           referrals=referrals, earned=earned)


@marketing_bp.route('/referral/use', methods=['POST'])
def use_referral():
    uid = session.get('user_id')
    if not uid:
        return jsonify({'status': 'error', 'msg': 'Login required'})
    code = request.json.get('code', '').strip().upper()
    referrer = find_record('users', referral_code=code)
    if not referrer or referrer['id'] == uid:
        return jsonify({'status': 'error', 'msg': 'Invalid referral code'})
    if find_record('referrals', referred_id=uid):
        return jsonify({'status': 'error', 'msg': 'You have already used a referral code'})
    bonus = int(get_setting('referral_bonus', '100'))
    save_record('referrals', {
        'referrer_id': referrer['id'], 'referred_id': uid,
        'code': code, 'points_earned': bonus,
        'ts': datetime.utcnow().isoformat()
    })
    add_points(referrer['id'], bonus, 'referral_bonus')
    add_points(uid, bonus, 'referral_signup')
    return jsonify({'status': 'ok', 'msg': f'Referral applied! You got {bonus} points.'})


# ── Notifications ─────────────────────────────────────────────
@marketing_bp.route('/notifications')
def notifications():
    uid = session.get('user_id')
    if not uid:
        return redirect(url_for('auth.login'))
    notifs = sorted(
        find_records('notifications', user_id=uid),
        key=lambda x: x.get('created_at', ''), reverse=True
    )[:30]
    # Mark all as read
    for n in notifs:
        if not n.get('read'):
            n['read'] = True
            save_record('notifications', n)
    return render_template('shop/notifications.html', notifications=notifs)


@marketing_bp.route('/notifications/count')
def notif_count():
    uid = session.get('user_id')
    if not uid:
        return jsonify({'count': 0})
    count = len([n for n in find_records('notifications', user_id=uid)
                 if not n.get('read')])
    return jsonify({'count': count})


def send_notification(user_id, title, message, notif_type='info', link=''):
    save_record('notifications', {
        'user_id': user_id, 'title': title, 'message': message,
        'type': notif_type, 'link': link, 'read': False
    })
