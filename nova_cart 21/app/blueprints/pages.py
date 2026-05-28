"""Custom pages blueprint"""
from flask import Blueprint, render_template
from utils.storage import find_record
import json

pages_bp = Blueprint('pages', __name__)


def _b(btype, d):
    """Render a single block dict to HTML string."""

    if btype == 'heading':
        t = d.get('level','h2')
        fw = '800' if d.get('bold', True) else '400'
        st = f"text-align:{d.get('align','left')};color:{d.get('color','#2D3748')};font-size:{d.get('size','2rem')};font-weight:{fw};margin:.75rem 0"
        return f"<{t} style='{st}'>{d.get('text','')}</{t}>"

    if btype == 'paragraph':
        st = f"text-align:{d.get('align','left')};color:{d.get('color','#718096')};font-size:{d.get('size','1rem')};line-height:1.8;margin:.5rem 0"
        return f"<p style='{st}'>{d.get('text','')}</p>"

    if btype == 'richtext':
        return f"<div style='line-height:1.8'>{d.get('html','')}</div>"

    if btype == 'quote':
        c = d.get('color','#6C63FF')
        return (f"<blockquote style='border-left:4px solid {c};padding:1rem 1.5rem;margin:1rem 0;"
                f"background:rgba(108,99,255,.05);border-radius:0 8px 8px 0'>"
                f"<p style='font-style:italic;font-size:1.1rem;margin:0 0 .5rem'>\"{d.get('text','')}\"</p>"
                f"<cite style='font-size:.85rem;font-weight:600;color:{c}'>— {d.get('author','')}</cite></blockquote>")

    if btype == 'divider':
        return f"<hr style='border:none;border-top:2px solid {d.get('color','#E2E8F0')};margin:{d.get('margin','2rem')} 0'>"

    if btype == 'image':
        src = d.get('src','')
        if not src:
            return ''
        cap = f"<p style='font-size:.85rem;color:#718096;margin-top:.5rem'>{d.get('caption','')}</p>" if d.get('caption') else ''
        return (f"<div style='text-align:{d.get('align','center')};margin:1rem 0'>"
                f"<img src='{src}' alt='{d.get('alt','')}' style='max-width:{d.get('width','100%')};border-radius:8px'>{cap}</div>")

    if btype == 'video':
        return (f"<div style='position:relative;padding-bottom:56.25%;height:0;border-radius:8px;overflow:hidden;margin:1rem 0'>"
                f"<iframe src='{d.get('url','')}' style='position:absolute;top:0;left:0;width:100%;height:100%;border:none' allowfullscreen></iframe></div>")

    if btype == 'hero':
        bg_img = d.get('bg_image','')
        bg = f"url({bg_img}) center/cover" if bg_img else d.get('bg_color','#6C63FF')
        tc = d.get('text_color','#fff')
        bc = d.get('bg_color','#6C63FF')
        align = d.get('align','center')
        jc = 'flex-start' if align == 'left' else 'center'
        btn1 = (f"<a href='{d.get('btn_url','#')}' style='background:#fff;color:{bc};"
                f"padding:.75rem 2rem;border-radius:8px;font-weight:700;text-decoration:none;display:inline-block'>"
                f"{d.get('btn_text','')}</a>") if d.get('btn_text') else ''
        btn2 = (f"<a href='{d.get('btn2_url','#')}' style='background:transparent;color:#fff;"
                f"border:2px solid #fff;padding:.75rem 2rem;border-radius:8px;font-weight:700;"
                f"text-decoration:none;display:inline-block'>{d.get('btn2_text','')}</a>") if d.get('btn2_text') else ''
        return (f"<div style='background:{bg};color:{tc};text-align:{align};"
                f"padding:{d.get('padding','5rem 2rem')};position:relative;border-radius:12px;margin:1rem 0'>"
                f"<h1 style='font-size:2.5rem;font-weight:800;margin-bottom:1rem'>{d.get('title','')}</h1>"
                f"<p style='font-size:1.1rem;opacity:.9;margin-bottom:2rem'>{d.get('subtitle','')}</p>"
                f"<div style='display:flex;gap:1rem;justify-content:{jc};flex-wrap:wrap'>{btn1}{btn2}</div></div>")

    if btype == 'cta':
        bg = d.get('bg_color','#F0EEFF')
        tc = d.get('text_color','#1A1A2E')
        bc = d.get('btn_color','#6C63FF')
        btn1 = (f"<a href='{d.get('btn_url','#')}' style='background:{bc};color:#fff;"
                f"padding:.75rem 2rem;border-radius:8px;font-weight:700;text-decoration:none;display:inline-block'>"
                f"{d.get('btn_text','')}</a>") if d.get('btn_text') else ''
        btn2 = (f"<a href='{d.get('btn2_url','#')}' style='background:transparent;color:{bc};"
                f"border:2px solid {bc};padding:.75rem 2rem;border-radius:8px;font-weight:700;"
                f"text-decoration:none;display:inline-block'>{d.get('btn2_text','')}</a>") if d.get('btn2_text') else ''
        return (f"<div style='background:{bg};text-align:center;padding:3rem 2rem;border-radius:12px;margin:1rem 0'>"
                f"<h2 style='color:{tc};font-size:1.8rem;font-weight:800;margin-bottom:.5rem'>{d.get('title','')}</h2>"
                f"<p style='color:{tc};opacity:.7;margin-bottom:1.5rem'>{d.get('subtitle','')}</p>"
                f"<div style='display:flex;gap:1rem;justify-content:center;flex-wrap:wrap'>{btn1}{btn2}</div></div>")

    if btype == 'cta_btn':
        sizes = {'sm':'.4rem 1rem','md':'.65rem 1.5rem','lg':'.85rem 2rem'}
        p = sizes.get(d.get('size','lg'),'.85rem 2rem')
        w = 'width:100%;text-align:center;display:block;' if d.get('full_width') else 'display:inline-block;'
        al = d.get('align','center')
        c = d.get('color','#6C63FF')
        tc = d.get('text_color','#fff')
        r = d.get('radius','8px')
        return (f"<div style='text-align:{al};margin:1rem 0'>"
                f"<a href='{d.get('url','#')}' style='background:{c};color:{tc};"
                f"padding:{p};border-radius:{r};font-weight:700;text-decoration:none;{w}'>"
                f"{d.get('text','Button')}</a></div>")

    if btype == 'columns2':
        g = d.get('gap','2rem')
        return (f"<div style='display:grid;grid-template-columns:1fr 1fr;gap:{g};margin:1rem 0'>"
                f"<div>{d.get('col1','')}</div><div>{d.get('col2','')}</div></div>")

    if btype == 'columns3':
        return (f"<div style='display:grid;grid-template-columns:1fr 1fr 1fr;gap:1.5rem;margin:1rem 0'>"
                f"<div>{d.get('col1','')}</div><div>{d.get('col2','')}</div><div>{d.get('col3','')}</div></div>")

    if btype == 'feature_row':
        ic = d.get('icon_color','#6C63FF')
        return (f"<div style='display:flex;align-items:flex-start;gap:1.25rem;margin:1rem 0;"
                f"padding:1rem;background:#F8F9FF;border-radius:12px'>"
                f"<div style='width:52px;height:52px;border-radius:12px;background:{ic}22;"
                f"display:flex;align-items:center;justify-content:center;flex-shrink:0'>"
                f"<i class='{d.get('icon','fas fa-star')}' style='color:{ic};font-size:1.3rem'></i></div>"
                f"<div><strong style='font-size:1rem'>{d.get('title','')}</strong>"
                f"<p style='color:#718096;margin-top:.25rem'>{d.get('text','')}</p></div></div>")

    if btype == 'testimonial':
        stars = '⭐' * int(d.get('rating',5))
        c = d.get('color','#6C63FF')
        return (f"<div style='background:#F8F9FF;border-radius:12px;padding:1.5rem;"
                f"margin:1rem 0;border-left:4px solid {c}'>"
                f"<div style='margin-bottom:.75rem'>{stars}</div>"
                f"<p style='font-style:italic;line-height:1.7;margin-bottom:1rem'>\"{d.get('text','')}\"</p>"
                f"<strong>{d.get('author','')}</strong>"
                f"<span style='color:#718096;font-size:.85rem'> — {d.get('role','Verified Buyer')}</span></div>")

    if btype == 'faq':
        op = 'open' if d.get('open') else ''
        return (f"<details style='border:1px solid #E2E8F0;border-radius:8px;margin:.5rem 0;overflow:hidden' {op}>"
                f"<summary style='padding:1rem;font-weight:600;cursor:pointer;background:#F8F9FA'>"
                f"{d.get('question','')}</summary>"
                f"<div style='padding:1rem;line-height:1.7;color:#718096'>{d.get('answer','')}</div></details>")

    if btype == 'pricing_card':
        c = d.get('color','#6C63FF')
        popular = d.get('popular', False)
        pop_badge = (f"<div style='background:{c};color:#fff;text-align:center;"
                     f"padding:.4rem;font-size:.8rem;font-weight:700'>★ MOST POPULAR</div>") if popular else ''
        border = f"2px solid {c}" if popular else "2px solid #E2E8F0"
        feats = ''.join([f"<li style='padding:.35rem 0;border-bottom:1px solid #f0f0f0;font-size:.9rem'>"
                         f"<i class='fas fa-check' style='color:{c};margin-right:.5rem'></i>{f}</li>"
                         for f in (d.get('features','') or '').split('\n') if f.strip()])
        return (f"<div style='max-width:320px;margin:1rem auto;border:{border};border-radius:16px;overflow:hidden'>"
                f"{pop_badge}<div style='padding:2rem;text-align:center'>"
                f"<h3 style='font-size:1.2rem;font-weight:700'>{d.get('name','Plan')}</h3>"
                f"<div style='font-size:2.5rem;font-weight:800;color:{c};margin:.5rem 0'>"
                f"{d.get('price','₹0')}<span style='font-size:1rem;color:#718096'>{d.get('period','/mo')}</span></div>"
                f"<ul style='list-style:none;text-align:left;margin:1rem 0;padding:0'>{feats}</ul>"
                f"<a href='{d.get('btn_url','#')}' style='background:{c};color:#fff;padding:.75rem 2rem;"
                f"border-radius:8px;font-weight:700;text-decoration:none;display:block;margin-top:.5rem'>"
                f"{d.get('btn_text','Choose Plan')}</a></div></div>")

    if btype == 'product_grid':
        from utils.storage import get_collection as gc, find_record as fr
        limit = int(d.get('limit', 4))
        cat_slug = d.get('category_slug','')
        prods = [p for p in gc('products') if p.get('is_active')]
        if cat_slug:
            cat = fr('categories', slug=cat_slug)
            if cat:
                prods = [p for p in prods if p.get('category_id') == cat['id']]
        prods = prods[:limit]
        title_h = f"<h2 style='font-size:1.5rem;font-weight:700;margin-bottom:1.25rem'>{d.get('title','')}</h2>" if d.get('title') else ''
        cards = ''
        for p in prods:
            imgs = p.get('images',[])
            img_src = imgs[0] if imgs else '/static/images/no-image.png'
            price = p.get('discount_price') or p.get('price',0)
            orig = (f"<span style='text-decoration:line-through;color:#718096;font-size:.85rem'>₹{int(p['price'])}</span>"
                    if p.get('discount_price') else '')
            cards += (f"<div style='background:#fff;border:1px solid #E2E8F0;border-radius:12px;overflow:hidden'>"
                      f"<img src='{img_src}' alt='{p.get('name','')}' style='width:100%;height:160px;object-fit:cover'>"
                      f"<div style='padding:.85rem'><p style='font-size:.9rem;font-weight:600;margin-bottom:.4rem'>{p['name'][:40]}</p>"
                      f"<div style='display:flex;gap:.4rem;align-items:center'>"
                      f"<span style='font-weight:700;color:#6C63FF'>₹{int(price)}</span>{orig}</div>"
                      f"<a href='/shop/product/{p.get('slug','')}' style='background:#6C63FF;color:#fff;padding:.4rem .75rem;"
                      f"border-radius:8px;font-weight:600;text-decoration:none;display:block;text-align:center;margin-top:.6rem;font-size:.85rem'>"
                      f"Add to Cart</a></div></div>")
        return (f"<div style='margin:1.5rem 0'>{title_h}"
                f"<div style='display:grid;grid-template-columns:repeat(auto-fill,minmax(200px,1fr));gap:1rem'>{cards}</div></div>")

    if btype == 'countdown':
        end_date = d.get('end_date','')
        color = d.get('color','#FF6584')
        cid = f"cd{abs(hash(end_date))}"
        return (f"<div style='text-align:center;padding:1.5rem;background:#FFF5F8;border-radius:12px;margin:1rem 0'>"
                f"<p style='font-weight:700;margin-bottom:.75rem'>{d.get('title','Offer Ends In')}</p>"
                f"<div id='{cid}' style='display:flex;gap:.75rem;justify-content:center;"
                f"font-size:1.5rem;font-weight:800;color:{color}'>Loading…</div></div>"
                f"<script>(function(){{var el=document.getElementById('{cid}');"
                f"setInterval(function(){{var diff=new Date('{end_date}').getTime()-Date.now();"
                f"if(!el||diff<=0){{if(el)el.textContent='Ended';return;}}"
                f"var h=Math.floor(diff/3600000),m=Math.floor((diff%3600000)/60000),s=Math.floor((diff%60000)/1000);"
                f"el.innerHTML='<span>'+h+'h</span> <span>'+m+'m</span> <span>'+s+'s</span>';}},1000);}})();</script>")

    if btype == 'spacer':
        return f"<div style='height:{d.get('height','3rem')}'></div>"

    return ''


def render_builder_blocks(content):
    if not content:
        return content
    try:
        blocks = json.loads(content)
        if not isinstance(blocks, list):
            return content
    except (json.JSONDecodeError, TypeError):
        return content
    return '\n'.join(_b(bl.get('type',''), bl.get('data',{})) for bl in blocks)


@pages_bp.route('/<slug>')
def show_page(slug):
    page = find_record('pages', slug=slug, is_published=True)
    if not page:
        return render_template('404.html'), 404
    rendered_content = render_builder_blocks(page.get('content',''))
    return render_template('pages/page.html', page=page, rendered_content=rendered_content)
