/* ═══════════════════════════════════════════════════════════
   Nova Cart - Main JavaScript
   ═══════════════════════════════════════════════════════════ */

// ── CSRF Token ───────────────────────────────────────────────
function getCsrf() {
  const meta = document.querySelector('meta[name="csrf-token"]');
  if (meta) return meta.content;
  const inp = document.querySelector('input[name="csrf_token"]');
  return inp ? inp.value : '';
}

// ── Cart Badge ───────────────────────────────────────────────
function updateCartBadge(count) {
  let badge = document.querySelector('.cart-badge');
  const icon = document.querySelector('.cart-icon');
  if (!icon) return;
  if (count > 0) {
    if (!badge) {
      badge = document.createElement('span');
      badge.className = 'cart-badge';
      icon.appendChild(badge);
    }
    badge.textContent = count;
  } else if (badge) {
    badge.remove();
  }
}

// ── Add to Cart ──────────────────────────────────────────────
function addToCart(productId, btn) {
  if (btn) {
    btn.disabled = true;
    btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Adding...';
  }
  fetch('/cart/add/' + productId, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-CSRFToken': getCsrf()
    },
    body: JSON.stringify({ quantity: 1 })
  })
  .then(r => r.json())
  .then(data => {
    if (data.status === 'login_required') {
      window.location.href = '/auth/login';
      return;
    }
    if (data.status === 'added') {
      updateCartBadge(data.cart_count);
      showToast('Added to cart!', 'success');
    }
  })
  .catch(() => showToast('Something went wrong', 'error'))
  .finally(() => {
    if (btn) {
      btn.disabled = false;
      btn.innerHTML = '<i class="fas fa-cart-plus"></i> Add to Cart';
    }
  });
}

// ── Wishlist Toggle ──────────────────────────────────────────
function toggleWishlist(productId, btn) {
  fetch('/shop/wishlist/toggle/' + productId, {
    method: 'POST',
    headers: { 'X-CSRFToken': getCsrf() }
  })
  .then(r => r.json())
  .then(data => {
    if (data.status === 'login_required') {
      window.location.href = '/auth/login';
      return;
    }
    const icon = btn.querySelector('i');
    if (data.status === 'added') {
      if (icon) { icon.className = 'fas fa-heart'; }
      btn.classList.add('wishlisted');
      showToast('Added to wishlist!', 'success');
    } else {
      if (icon) { icon.className = 'far fa-heart'; }
      btn.classList.remove('wishlisted');
      showToast('Removed from wishlist', 'info');
    }
  })
  .catch(() => showToast('Something went wrong', 'error'));
}

// ── Toast Notifications ──────────────────────────────────────
function showToast(message, type = 'success') {
  let container = document.querySelector('.flash-container');
  if (!container) {
    container = document.createElement('div');
    container.className = 'flash-container';
    document.body.appendChild(container);
  }
  const toast = document.createElement('div');
  toast.className = `flash flash-${type}`;
  toast.innerHTML = `<span>${message}</span><button class="flash-close" onclick="this.parentElement.remove()">&times;</button>`;
  container.appendChild(toast);
  setTimeout(() => toast.remove(), 4000);
}

// ── Nav Toggle (mobile) ──────────────────────────────────────
document.addEventListener('DOMContentLoaded', function () {
  const toggle = document.getElementById('navToggle');
  const links = document.getElementById('navLinks');
  if (toggle && links) {
    toggle.addEventListener('click', () => links.classList.toggle('open'));
  }

  // Auto-dismiss flash messages
  document.querySelectorAll('.flash').forEach(f => {
    setTimeout(() => f.remove(), 5000);
  });

  // Search suggestions (basic)
  const searchInput = document.querySelector('.search-input');
  if (searchInput) {
    searchInput.addEventListener('keydown', e => {
      if (e.key === 'Enter') e.target.closest('form').submit();
    });
  }

  // Sticky navbar shadow
  window.addEventListener('scroll', () => {
    const nav = document.getElementById('mainNav');
    if (nav) nav.style.boxShadow = window.scrollY > 10 ? '0 4px 20px rgba(0,0,0,.12)' : '';
  });

  // Lazy loading images
  if ('IntersectionObserver' in window) {
    const imgs = document.querySelectorAll('img[loading="lazy"]');
    const obs = new IntersectionObserver((entries) => {
      entries.forEach(e => {
        if (e.isIntersecting) {
          const img = e.target;
          if (img.dataset.src) img.src = img.dataset.src;
          obs.unobserve(img);
        }
      });
    });
    imgs.forEach(img => obs.observe(img));
  }

  // Password toggle helper
  window.togglePass = function(id) {
    const inp = document.getElementById(id);
    if (!inp) return;
    inp.type = inp.type === 'password' ? 'text' : 'password';
  };

  // Recently purchased social proof popup
  const proofData = [
    { name: 'Rahul S.', city: 'Mumbai', product: 'Wireless Earbuds' },
    { name: 'Priya M.', city: 'Delhi', product: 'Fast Charger 65W' },
    { name: 'Arjun K.', city: 'Bangalore', product: 'Oud Perfume' },
    { name: 'Sneha R.', city: 'Pune', product: 'Smart LED Bulb' },
    { name: 'Vikram T.', city: 'Chennai', product: 'Fitness Tracker' },
  ];
  let proofIndex = 0;

  function showSocialProof() {
    const item = proofData[proofIndex % proofData.length];
    proofIndex++;
    let el = document.getElementById('socialProofPopup');
    if (!el) {
      el = document.createElement('div');
      el.id = 'socialProofPopup';
      el.style.cssText = `position:fixed;bottom:5.5rem;left:1.5rem;background:#fff;border:1px solid #E2E8F0;
        border-radius:12px;padding:.9rem 1.1rem;box-shadow:0 8px 30px rgba(0,0,0,.12);
        z-index:998;max-width:260px;font-size:.85rem;animation:slideIn .4s ease;`;
      document.body.appendChild(el);
    }
    el.innerHTML = `<div style="display:flex;align-items:center;gap:.6rem">
      <div style="width:36px;height:36px;border-radius:50%;background:linear-gradient(135deg,#6C63FF,#FF6584);
        color:#fff;display:flex;align-items:center;justify-content:center;font-weight:700;flex-shrink:0">
        ${item.name[0]}
      </div>
      <div>
        <strong>${item.name}</strong> from ${item.city}<br>
        just bought <strong>${item.product}</strong> 🎉
      </div>
    </div>`;
    el.style.display = 'block';
    setTimeout(() => { if (el) el.style.display = 'none'; }, 4000);
  }

  // Show proof popups on shop pages
  if (document.querySelector('.products-grid')) {
    setTimeout(showSocialProof, 5000);
    setInterval(showSocialProof, 18000);
  }

  // Live visitor counter (simulated)
  const visitorEl = document.getElementById('liveVisitors');
  if (visitorEl) {
    const base = 24 + Math.floor(Math.random() * 30);
    visitorEl.textContent = base;
    setInterval(() => {
      const change = Math.floor(Math.random() * 5) - 2;
      const current = parseInt(visitorEl.textContent || '24');
      visitorEl.textContent = Math.max(10, current + change);
    }, 8000);
  }
});

// ── PWA Service Worker Registration ─────────────────────────
if ('serviceWorker' in navigator) {
  window.addEventListener('load', () => {
    navigator.serviceWorker.register('/static/js/sw.js').catch(() => {});
  });
}
