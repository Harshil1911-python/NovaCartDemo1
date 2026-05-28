"""File/image upload utilities"""
import os
import secrets
from PIL import Image
from werkzeug.utils import secure_filename

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'app', 'static', 'images', 'uploads')
# Ensure upload folder always exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
MAX_IMAGE_SIZE = (1200, 1200)


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def save_uploaded_file(file, subfolder='general'):
    if not file or not allowed_file(file.filename):
        return None
    os.makedirs(os.path.join(UPLOAD_FOLDER, subfolder), exist_ok=True)
    ext = file.filename.rsplit('.', 1)[1].lower()
    filename = secrets.token_hex(12) + '.' + ext
    filepath = os.path.join(UPLOAD_FOLDER, subfolder, filename)
    file.save(filepath)
    # Compress
    try:
        img = Image.open(filepath)
        img.thumbnail(MAX_IMAGE_SIZE, Image.LANCZOS)
        if ext in ('jpg', 'jpeg'):
            img.save(filepath, 'JPEG', quality=85, optimize=True)
        else:
            img.save(filepath, optimize=True)
    except Exception:
        pass
    return f'/static/images/uploads/{subfolder}/{filename}'


def delete_file(url_path):
    if not url_path:
        return
    rel = url_path.lstrip('/')
    full = os.path.join(BASE_DIR, 'app', rel)
    if os.path.exists(full):
        os.remove(full)
