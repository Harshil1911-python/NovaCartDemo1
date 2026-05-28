"""
Nova Cart - File-Based Storage Engine
Handles all data persistence using data.dat (JSON) + CSV files
"""
import json
import csv
import os
import shutil
import time
import hashlib
from datetime import datetime
from threading import Lock

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_FILE = os.path.join(BASE_DIR, 'storage', 'data.dat')
BACKUP_DIR = os.path.join(BASE_DIR, 'backups')
CSV_DIR = os.path.join(BASE_DIR, 'storage', 'csv')

_lock = Lock()

# ─── INIT ─────────────────────────────────────────────────────────────────────
def init_storage():
    os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
    os.makedirs(BACKUP_DIR, exist_ok=True)
    os.makedirs(CSV_DIR, exist_ok=True)
    if not os.path.exists(DATA_FILE):
        _write_data({})

def _read_data():
    if not os.path.exists(DATA_FILE):
        return {}
    try:
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        # Attempt restore from latest backup
        restored = restore_latest_backup()
        return restored if restored else {}

def _write_data(data):
    with _lock:
        tmp = DATA_FILE + '.tmp'
        with open(tmp, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, default=str)
        os.replace(tmp, DATA_FILE)

# ─── COLLECTION CRUD ──────────────────────────────────────────────────────────
def get_collection(name):
    """Return a list of records for a collection."""
    return _read_data().get(name, [])

def save_record(collection, record):
    """Insert or update a record. Assigns 'id' if missing."""
    data = _read_data()
    col = data.get(collection, [])
    if 'id' not in record or not record['id']:
        max_id = max((r.get('id', 0) for r in col), default=0)
        record['id'] = max_id + 1
    record['updated_at'] = datetime.utcnow().isoformat()
    if 'created_at' not in record:
        record['created_at'] = datetime.utcnow().isoformat()
    # Update if exists
    for i, r in enumerate(col):
        if r.get('id') == record['id']:
            col[i] = record
            data[collection] = col
            _write_data(data)
            return record
    col.append(record)
    data[collection] = col
    _write_data(data)
    return record

def get_record(collection, record_id):
    """Get single record by id."""
    for r in get_collection(collection):
        if r.get('id') == record_id:
            return r
    return None

def find_record(collection, **kwargs):
    """Find first record matching all kwargs."""
    for r in get_collection(collection):
        if all(r.get(k) == v for k, v in kwargs.items()):
            return r
    return None

def find_records(collection, **kwargs):
    """Find all records matching kwargs."""
    results = []
    for r in get_collection(collection):
        if all(r.get(k) == v for k, v in kwargs.items()):
            results.append(r)
    return results

def delete_record(collection, record_id):
    """Delete record by id."""
    data = _read_data()
    col = data.get(collection, [])
    data[collection] = [r for r in col if r.get('id') != record_id]
    _write_data(data)

def delete_records(collection, **kwargs):
    """Delete all records matching kwargs."""
    data = _read_data()
    col = data.get(collection, [])
    data[collection] = [r for r in col if not all(r.get(k) == v for k, v in kwargs.items())]
    _write_data(data)

def count_records(collection, **kwargs):
    if kwargs:
        return len(find_records(collection, **kwargs))
    return len(get_collection(collection))

def get_setting(key, default=None):
    settings = find_record('settings', key=key)
    return settings['value'] if settings else default

def save_setting(key, value):
    existing = find_record('settings', key=key)
    record = existing or {}
    record['key'] = key
    record['value'] = value
    save_record('settings', record)

def get_all_settings():
    return {r['key']: r['value'] for r in get_collection('settings')}

# ─── BACKUP SYSTEM ────────────────────────────────────────────────────────────
def create_backup():
    if not os.path.exists(DATA_FILE):
        return None
    ts = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
    dest = os.path.join(BACKUP_DIR, f'data_{ts}.dat')
    shutil.copy2(DATA_FILE, dest)
    _cleanup_old_backups(keep=10)
    return dest

def _cleanup_old_backups(keep=10):
    backups = sorted(
        [f for f in os.listdir(BACKUP_DIR) if f.endswith('.dat')],
        reverse=True
    )
    for old in backups[keep:]:
        os.remove(os.path.join(BACKUP_DIR, old))

def restore_latest_backup():
    if not os.path.exists(BACKUP_DIR):
        return None
    backups = sorted(
        [f for f in os.listdir(BACKUP_DIR) if f.endswith('.dat')],
        reverse=True
    )
    for b in backups:
        try:
            with open(os.path.join(BACKUP_DIR, b), 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            continue
    return None

def list_backups():
    if not os.path.exists(BACKUP_DIR):
        return []
    return sorted(
        [f for f in os.listdir(BACKUP_DIR) if f.endswith('.dat')],
        reverse=True
    )

# ─── CSV EXPORT/IMPORT ────────────────────────────────────────────────────────
def export_collection_csv(collection):
    records = get_collection(collection)
    if not records:
        return None
    path = os.path.join(CSV_DIR, f'{collection}.csv')
    with open(path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=records[0].keys())
        writer.writeheader()
        writer.writerows(records)
    return path

def import_collection_csv(collection, filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            save_record(collection, dict(row))
