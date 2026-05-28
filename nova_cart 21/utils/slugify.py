"""Pure stdlib slug generator — no external deps needed"""
import re
import unicodedata


def slugify(text, separator='-'):
    """Convert text to URL-safe slug."""
    if not text:
        return ''
    # Normalize unicode
    text = unicodedata.normalize('NFKD', str(text))
    text = text.encode('ascii', 'ignore').decode('ascii')
    text = text.lower().strip()
    # Replace non-alphanumeric with separator
    text = re.sub(r'[^a-z0-9]+', separator, text)
    text = text.strip(separator)
    return text or 'item'
