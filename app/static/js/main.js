/**
 * CASHON main.js — Core interactions & utilities
 * Handles: toasts, cart, wishlist, scroll reveals,
 *          add-to-cart, INR formatting, page-wide JS
 */

'use strict';

// ══════════════════════════════════════════════════════════════
// 1. INR Currency Formatter
// ══════════════════════════════════════════════════════════════
function formatINR(amount) {
  return '₹' + Number(amount).toLocaleString('en-IN', {
    maximumFractionDigits: 0
  });
}

// ══════════════════════════════════════════════════════════════
// 2. Toast Notification System
// ══════════════════════════════════════════════════════════════
const TOAST_ICONS = {
  success: 'bi-check-circle-fill',
  error:   'bi-x-circle-fill',
  info:    'bi-info-circle-fill',
  warning: 'bi-exclamation-triangle-fill',
};

window.showToast = function(type, title, message = '') {
  const container = document.getElementById('toast-container');
  if (!container) return;

  const toast = document.createElement('div');
  toast.className = `toast toast--${type}`;
  toast.setAttribute('role', 'alert');
  toast.innerHTML = `
    <div class="toast-icon"><i class="bi ${TOAST_ICONS[type] || 'bi-info-circle-fill'}"></i></div>
    <div class="toast-body">
      <div class="toast-title">${title}</div>
      ${message ? `<div class="toast-msg">${message}</div>` : ''}
    </div>
    <button class="toast-close" aria-label="Dismiss"><i class="bi bi-x"></i></button>
  `;

  container.appendChild(toast);

  toast.querySelector('.toast-close').addEventListener('click', () => dismissToast(toast));
  setTimeout(() => dismissToast(toast), 5000);
};

function dismissToast(toast) {
  if (!toast || toast.classList.contains('leaving')) return;
  toast.classList.add('leaving');
  setTimeout(() => toast.remove(), 300);
}

// ══════════════════════════════════════════════════════════════
// 3. Add-to-Cart (global handler)
// ══════════════════════════════════════════════════════════════
document.addEventListener('click', function(e) {
  const btn = e.target.closest('[data-add-cart]');
  if (!btn) return;

  const productId = btn.dataset.addCart;
  if (!productId) return;

  const originalHtml = btn.innerHTML;
  btn.classList.add('loading');
  btn.disabled = true;

  fetch('/api/cart/add', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ product_id: parseInt(productId), qty: 1 })
  })
  .then(r => r.json())
  .then(data => {
    btn.classList.remove('loading');
    btn.innerHTML = originalHtml;
    btn.disabled = false;

    if (data.ok) {
      showToast('success', 'Added to cart!', data.message || '');
      // Update all cart badges
      document.querySelectorAll('.cart-count-badge').forEach(b => {
        b.textContent = data.count;
        b.style.display = data.count > 0 ? 'flex' : 'none';
      });
      // Animate button feedback
      btn.innerHTML = '<i class="bi bi-check-lg"></i> Added!';
      btn.style.background = 'var(--c-success)';
      setTimeout(() => {
        btn.innerHTML = originalHtml;
        btn.style.background = '';
      }, 1800);
    } else if (data.login_required) {
      showToast('info', 'Sign in required', 'Please sign in to add items to your cart.');
      setTimeout(() => { window.location.href = '/account/login?next=' + encodeURIComponent(window.location.pathname); }, 1200);
    } else {
      showToast('error', 'Could not add', data.message || 'Please try again.');
      btn.innerHTML = originalHtml;
    }
  })
  .catch(() => {
    btn.classList.remove('loading');
    btn.innerHTML = originalHtml;
    btn.disabled = false;
    showToast('error', 'Network error', 'Please check your connection.');
  });
});

// ══════════════════════════════════════════════════════════════
// 4. Wishlist Toggle (global handler)
// ══════════════════════════════════════════════════════════════
document.addEventListener('click', function(e) {
  const btn = e.target.closest('[data-wishlist]');
  if (!btn) return;

  const productId = btn.dataset.wishlist;
  if (!productId) return;

  fetch('/api/wishlist/toggle', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ product_id: parseInt(productId) })
  })
  .then(r => r.json())
  .then(data => {
    if (data.ok) {
      const icon = btn.querySelector('i') || btn;
      if (data.in_wishlist) {
        btn.classList.add('wishlisted');
        icon.className = 'bi bi-heart-fill';
        icon.style.color = 'var(--c-error)';
        showToast('success', 'Added to wishlist!', '');
      } else {
        btn.classList.remove('wishlisted');
        icon.className = 'bi bi-heart';
        icon.style.color = '';
        showToast('info', 'Removed from wishlist', '');
      }
      // Animate
      btn.style.transform = 'scale(1.4)';
      setTimeout(() => { btn.style.transform = ''; }, 300);
    } else if (data.login_required) {
      showToast('info', 'Sign in required', 'Please sign in to save items.');
      setTimeout(() => { window.location.href = '/account/login'; }, 1200);
    }
  })
  .catch(() => showToast('error', 'Could not update wishlist', ''));
});

// ══════════════════════════════════════════════════════════════
// 5. Scroll Reveal (IntersectionObserver)
// ══════════════════════════════════════════════════════════════
(function initReveal() {
  if (!('IntersectionObserver' in window)) {
    document.querySelectorAll('.reveal').forEach(el => el.classList.add('visible'));
    return;
  }

  const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        entry.target.classList.add('visible');
        observer.unobserve(entry.target);
      }
    });
  }, { threshold: 0.1, rootMargin: '0px 0px -48px 0px' });

  // Set stagger indices for children of reveal-stagger containers
  document.querySelectorAll('.reveal-stagger').forEach(container => {
    container.querySelectorAll('.product-card, .category-card, .trust-item, .review-card, .deal-card').forEach((el, i) => {
      el.classList.add('reveal');
      el.style.setProperty('--i', i);
    });
  });

  document.querySelectorAll('.reveal').forEach(el => observer.observe(el));
})();

// ══════════════════════════════════════════════════════════════
// 6. Hero Parallax / Orb Mouse Tracking
// ══════════════════════════════════════════════════════════════
(function initHeroParallax() {
  const orbs = document.querySelectorAll('.hero-orb');
  if (!orbs.length) return;

  document.addEventListener('mousemove', (e) => {
    const { clientX: x, clientY: y } = e;
    const cx = window.innerWidth  / 2;
    const cy = window.innerHeight / 2;
    const dx = (x - cx) / cx;
    const dy = (y - cy) / cy;

    orbs.forEach((orb, i) => {
      const strength = (i + 1) * 12;
      orb.style.transform = `translate(${dx * strength}px, ${dy * strength}px)`;
    });
  }, { passive: true });
})();

// ══════════════════════════════════════════════════════════════
// 7. AI Assistant (homepage widget)
// ══════════════════════════════════════════════════════════════
(function initAssistant() {
  const form       = document.getElementById('assistant-form');
  const input      = document.getElementById('assistant-input');
  const messages   = document.getElementById('assistant-messages');
  const examples   = document.querySelectorAll('.assistant-example');

  if (!form || !messages) return;

  function appendMessage(text, type) {
    const div = document.createElement('div');
    div.className = `assistant-msg assistant-msg--${type}`;
    div.innerHTML = text;
    messages.appendChild(div);
    messages.scrollTop = messages.scrollHeight;
    return div;
  }

  function showTyping() {
    const div = document.createElement('div');
    div.className = 'typing-indicator';
    div.id = 'typing-indicator';
    div.innerHTML = '<div class="typing-dot"></div><div class="typing-dot"></div><div class="typing-dot"></div>';
    messages.appendChild(div);
    messages.scrollTop = messages.scrollHeight;
  }

  function hideTyping() {
    document.getElementById('typing-indicator')?.remove();
  }

  function sendQuery(query) {
    if (!query.trim()) return;
    appendMessage(query, 'user');
    if (input) input.value = '';
    showTyping();

    fetch('/api/assistant', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query })
    })
    .then(r => r.json())
    .then(data => {
      hideTyping();
      let html = `<p style="margin-bottom:var(--sp-3)">${data.response}</p>`;
      if (data.products && data.products.length) {
        html += `<div style="display:flex;flex-direction:column;gap:var(--sp-2)">`;
        data.products.slice(0, 3).forEach(p => {
          html += `
            <a href="/product/${p.slug}" style="display:flex;align-items:center;gap:var(--sp-2);
               background:var(--c-surface-2);border:1px solid var(--c-border);border-radius:var(--r-md);
               padding:var(--sp-2);text-decoration:none;transition:border-color var(--dur-fast)"
               onmouseover="this.style.borderColor='var(--c-primary)'"
               onmouseout="this.style.borderColor='var(--c-border)'">
              <img src="${p.image}" style="width:40px;height:40px;object-fit:cover;border-radius:var(--r-sm)" />
              <div style="flex:1;min-width:0">
                <div style="font-size:var(--text-xs);font-weight:700;color:var(--c-text-1);
                     white-space:nowrap;overflow:hidden;text-overflow:ellipsis">${p.name}</div>
                <div style="font-size:var(--text-xs);color:var(--c-primary);font-weight:700">${formatINR(p.sale_price || p.price)}</div>
              </div>
            </a>`;
        });
        html += `</div>`;
      }
      appendMessage(html, 'bot');
    })
    .catch(() => {
      hideTyping();
      appendMessage("I'm having trouble connecting right now. Please try again.", 'bot');
    });
  }

  form.addEventListener('submit', e => {
    e.preventDefault();
    sendQuery(input?.value || '');
  });

  examples.forEach(el => {
    el.addEventListener('click', () => sendQuery(el.textContent.trim()));
  });
})();

// ══════════════════════════════════════════════════════════════
// 8. Notification Badge Loader
// ══════════════════════════════════════════════════════════════
(function loadNotifCount() {
  const badge = document.getElementById('notif-badge');
  if (!badge) return;
  fetch('/api/notifications/count')
    .then(r => r.json())
    .then(d => {
      if (d.count > 0) {
        badge.textContent = d.count;
        badge.style.display = 'flex';
      }
    }).catch(() => {});
})();

// ══════════════════════════════════════════════════════════════
// 9. Category Theme Switcher
// ══════════════════════════════════════════════════════════════
window.setCategoryTheme = function(themeData) {
  if (!themeData) return;
  const root = document.documentElement;
  root.style.setProperty('--cat-accent',   themeData.accent   || 'var(--c-primary)');
  root.style.setProperty('--cat-accent-2', themeData.accent2  || 'var(--c-primary-dark)');
  root.style.setProperty('--cat-bg',       themeData.bg       || 'var(--c-bg)');
  root.style.setProperty('--cat-surface',  themeData.surface  || 'var(--c-surface)');
  root.style.setProperty('--cat-text',     themeData.text     || 'var(--c-text-1)');
  root.style.setProperty('--cat-label',    themeData.label_color || themeData.accent || 'var(--c-primary)');

  // Light/dark body switch
  const isLight = ['warm','editorial','elegant','premium','calm'].includes(themeData.style);
  document.body.classList.toggle('theme-light', isLight);
};

// ══════════════════════════════════════════════════════════════
// 10. Quantity Controls (product detail)
// ══════════════════════════════════════════════════════════════
document.querySelectorAll('[data-qty-inc], [data-qty-dec]').forEach(btn => {
  btn.addEventListener('click', () => {
    const target = document.getElementById(btn.dataset.qtyTarget || 'qty-input');
    if (!target) return;
    let val = parseInt(target.value) || 1;
    if (btn.dataset.qtyInc !== undefined) val++;
    if (btn.dataset.qtyDec !== undefined) val = Math.max(1, val - 1);
    target.value = val;
  });
});

// ══════════════════════════════════════════════════════════════
// 11. Smooth Scroll-to-Section
// ══════════════════════════════════════════════════════════════
document.querySelectorAll('a[href^="#"]').forEach(a => {
  a.addEventListener('click', e => {
    const target = document.querySelector(a.getAttribute('href'));
    if (!target) return;
    e.preventDefault();
    target.scrollIntoView({ behavior: 'smooth', block: 'start' });
  });
});

// 12. Product image failure handling — fall back to the bundled local product image,
// then to a clean placeholder. Also catches images that failed before this script ran.
const LOCAL_IMAGE_FALLBACKS = {
  "https://kaldunga.com/storage/app/public/product/2024-10-02-66fd36405d64b.png": "/static/img/products/samsung-galaxy-s24-ultra.png",
  "https://istore.ph/cdn/shop/files/ROSA_iPad_Air_11_M2_WiFi_Blue_PDP_Image_Position_1b.jpg?v=1717577444&width=1200": "/static/img/products/ipad-air-m2-11.png",
  "https://images.hindustantimes.com/tech/htmobile4/oneplus-12-5g/colors/flowy-emerald/oneplus-12-5g-flowy-emerald-1.jpg?height=263&width=263": "/static/img/products/oneplus-12-5g.png",
  "https://resource.logitech.com/w_544%2Ch_466%2Car_7%3A6%2Cc_pad%2Cq_auto%2Cf_auto%2Cdpr_1.0/d_transparent.gif/content/dam/logitech/en/products/mice/mx-master-3s/2025-update/mx-master-3s-bluetooth-edition-top-view-graphite-new-1.png": "/static/img/products/logitech-mx-master-3s.png",
  "https://www.boat-lifestyle.com/cdn/shop/files/AD141-FI_Black01_600x.png?v=1698391770": "/static/img/products/boat-airdopes-141.png",
  "https://down-th.img.susercontent.com/file/f3023aae7294b6c4767e6179f92ecff8": "/static/img/products/mi-65w-charger.png",
  "https://m.media-amazon.com/images/I/71MPi6NDDJL.jpg": "/static/img/products/fireboltt-phoenix.png",
  "https://m.media-amazon.com/images/I/41yoLWTVkUL.jpg": "/static/img/products/corsair-k65-rgb.png",
  "https://images.durian.in/Durian/durian/product/800x800/796011749279355.jpg": "/static/img/products/durian-king-bed-storage.png",
  "https://apisap.fabindia.com/medias/10735144-01.jpg?aio=w-768": "/static/img/products/fabindia-cushion-set.png",
  "https://nestasia.in/cdn/shop/files/matte-white-vase-set_1.png?v=1738663929&width=1200": "/static/img/products/nestasia-ceramic-vase.png",
  "https://apisap.fabindia.com/medias/20209149-01.jpg": "/static/img/products/fabindia-cotton-kurta-men.png",
  "https://assets.ajio.com/medias/sys_master/root/20241121/ks5b/673f2bcfc148fa1b30dc1660/-473Wx593H-442696267-coral-MODEL.jpg": "/static/img/products/w-anarkali-suit.png",
  "https://www.myntraglobal.com/cdn/shop/files/ecb2f6de-a3ff-4c0b-a146-638f1247540e1742975843904-HRX-by-Hrithik-Roshan-Men-Tshirts-8291742975843299-3.jpg?v=1746019541&width=1080": "/static/img/products/hrx-sport-tshirt.png",
  "https://m.media-amazon.com/images/I/514PVblwPdL._SX425_.jpg": "/static/img/products/minimalist-salicylic-facewash.png",
  "https://static.ftshp.digital/img/p/1/3/6/8/4/8/7/1368487-thickbox.jpg": "/static/img/products/nike-air-zoom-pegasus-41.png"
};
function handleImageFailure(img) {
  const local = LOCAL_IMAGE_FALLBACKS[img.getAttribute('src')];
  if (local && img.dataset.localFallback !== 'true') {
    img.dataset.localFallback = 'true';
    img.src = local;
    return;
  }
  if (img.dataset.imageUnavailable === 'true') return;
  img.dataset.imageUnavailable = 'true';
  const label = (img.alt || 'Product image').replace(/[<>&"']/g, '').slice(0, 34);
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="640" height="640" viewBox="0 0 640 640"><rect width="640" height="640" fill="#F2EEE6"/><circle cx="320" cy="260" r="112" fill="#E4DED2"/><path d="M260 260h120M320 200v120" stroke="#9A927F" stroke-width="12" stroke-linecap="round"/><text x="320" y="445" text-anchor="middle" font-family="Arial,sans-serif" font-size="25" fill="#625F55">${label}</text><text x="320" y="485" text-anchor="middle" font-family="Arial,sans-serif" font-size="17" fill="#898477">CASHON</text></svg>`;
  img.src = 'data:image/svg+xml;charset=UTF-8,' + encodeURIComponent(svg);
  img.classList.add('image-unavailable');
}
document.querySelectorAll('img').forEach(img => {
  img.addEventListener('error', function() { handleImageFailure(this); });
  if (img.complete && img.naturalWidth === 0 && img.getAttribute('src')) handleImageFailure(img);
});

// 13. Number animation for stat counters
// ══════════════════════════════════════════════════════════════
function animateCounter(el) {
  const target = parseInt(el.dataset.count || el.textContent.replace(/\D/g, '')) || 0;
  const prefix = el.dataset.prefix || '';
  const suffix = el.dataset.suffix || '';
  const duration = 1800;
  const steps = 60;
  const increment = target / steps;
  let current = 0;
  const timer = setInterval(() => {
    current = Math.min(current + increment, target);
    el.textContent = prefix + Math.floor(current).toLocaleString('en-IN') + suffix;
    if (current >= target) clearInterval(timer);
  }, duration / steps);
}

const counterObserver = new IntersectionObserver(entries => {
  entries.forEach(entry => {
    if (entry.isIntersecting && !entry.target.dataset.counted) {
      entry.target.dataset.counted = 'true';
      animateCounter(entry.target);
    }
  });
}, { threshold: 0.5 });

document.querySelectorAll('[data-count]').forEach(el => counterObserver.observe(el));

// ══════════════════════════════════════════════════════════════
// 14. Coupon code copy
// ══════════════════════════════════════════════════════════════
document.querySelectorAll('[data-copy]').forEach(el => {
  el.addEventListener('click', () => {
    const text = el.dataset.copy;
    navigator.clipboard.writeText(text).then(() => {
      showToast('success', 'Copied!', `Code "${text}" copied to clipboard`);
    }).catch(() => {
      showToast('info', `Code: ${text}`, 'Copy this code at checkout');
    });
  });
});

// ══════════════════════════════════════════════════════════════
// 15. Product image gallery (product detail)
// ══════════════════════════════════════════════════════════════
(function initGallery() {
  const mainImg  = document.getElementById('gallery-main-img');
  const thumbs   = document.querySelectorAll('[data-gallery-thumb]');
  if (!mainImg || !thumbs.length) return;

  thumbs.forEach(thumb => {
    thumb.addEventListener('click', () => {
      mainImg.style.opacity = '0';
      setTimeout(() => {
        mainImg.src = thumb.dataset.galleryThumb;
        mainImg.alt = thumb.alt;
        mainImg.style.opacity = '1';
      }, 150);
      thumbs.forEach(t => t.classList.remove('active'));
      thumb.classList.add('active');
    });
  });

  // Image zoom on click
  mainImg.addEventListener('click', () => {
    const overlay = document.createElement('div');
    overlay.style.cssText = `
      position:fixed;inset:0;z-index:9999;
      background:rgba(0,0,0,.92);display:flex;
      align-items:center;justify-content:center;cursor:zoom-out;
    `;
    const img = document.createElement('img');
    img.src = mainImg.src;
    img.style.cssText = 'max-width:90vw;max-height:90vh;object-fit:contain;border-radius:12px;';
    overlay.appendChild(img);
    overlay.addEventListener('click', () => overlay.remove());
    document.body.appendChild(overlay);
  });
})();

console.log('%cCASHON', 'color:#5A321F;font-size:2rem;font-weight:900;font-family:Outfit,sans-serif');
console.log('%cDiscover More. Shop Smarter.', 'color:#302820;font-size:.9rem');
