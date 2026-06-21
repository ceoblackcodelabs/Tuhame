/* ============================================
   TUHAME – Main JavaScript
   ============================================ */

// ─── Dark Mode ───
const darkToggleBtns = document.querySelectorAll('.dark-toggle');
const prefersDark = window.matchMedia('(prefers-color-scheme: dark)');

function setTheme(dark) {
  document.documentElement.setAttribute('data-theme', dark ? 'dark' : 'light');
  localStorage.setItem('tuhame-theme', dark ? 'dark' : 'light');
  darkToggleBtns.forEach(btn => {
    btn.innerHTML = dark ? '☀️' : '🌙';
  });
}

const savedTheme = localStorage.getItem('tuhame-theme');
if (savedTheme) {
  setTheme(savedTheme === 'dark');
} else {
  setTheme(prefersDark.matches);
}

darkToggleBtns.forEach(btn => {
  btn.addEventListener('click', () => {
    const isDark = document.documentElement.getAttribute('data-theme') === 'dark';
    setTheme(!isDark);
  });
});

// ─── Navbar scroll ───
const navbar = document.querySelector('.navbar');
if (navbar) {
  function updateNavbar() {
    if (window.scrollY > 60) {
      navbar.classList.add('scrolled');
      navbar.classList.remove('transparent');
    } else {
      navbar.classList.remove('scrolled');
      navbar.classList.add('transparent');
    }
  }
  window.addEventListener('scroll', updateNavbar, { passive: true });
  updateNavbar();
}

// ─── Mobile Menu ───
const hamburger = document.querySelector('.hamburger');
const mobileMenu = document.querySelector('.mobile-menu');

if (hamburger && mobileMenu) {
  hamburger.addEventListener('click', () => {
    hamburger.classList.toggle('open');
    mobileMenu.classList.toggle('open');
    document.body.style.overflow = mobileMenu.classList.contains('open') ? 'hidden' : '';
  });

  mobileMenu.querySelectorAll('a').forEach(link => {
    link.addEventListener('click', () => {
      hamburger.classList.remove('open');
      mobileMenu.classList.remove('open');
      document.body.style.overflow = '';
    });
  });
}

// ─── Hero Carousel ───
const heroSlides = document.querySelectorAll('.hero-slide');
const heroDots = document.querySelectorAll('.hero-dot');
let currentSlide = 0;
let heroTimer;

function goToSlide(n) {
  heroSlides[currentSlide]?.classList.remove('active');
  heroDots[currentSlide]?.classList.remove('active');
  currentSlide = (n + heroSlides.length) % heroSlides.length;
  heroSlides[currentSlide]?.classList.add('active');
  heroDots[currentSlide]?.classList.add('active');
}

function startCarousel() {
  if (heroSlides.length < 2) return;
  heroTimer = setInterval(() => goToSlide(currentSlide + 1), 5000);
}

heroDots.forEach((dot, i) => {
  dot.addEventListener('click', () => {
    clearInterval(heroTimer);
    goToSlide(i);
    startCarousel();
  });
});

if (heroSlides.length > 0) {
  goToSlide(0);
  startCarousel();
}

// ─── Scroll Animations ───
const fadeEls = document.querySelectorAll('.fade-up');

if ('IntersectionObserver' in window) {
  const fadeObserver = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        entry.target.classList.add('visible');
        fadeObserver.unobserve(entry.target);
      }
    });
  }, { threshold: 0.1, rootMargin: '0px 0px -40px 0px' });

  fadeEls.forEach(el => fadeObserver.observe(el));
}

// ─── Save / Wishlist ───
const savedProps = new Set(JSON.parse(localStorage.getItem('tuhame-saved') || '[]'));

function updateSaveBtns() {
  document.querySelectorAll('.property-save').forEach(btn => {
    const id = btn.dataset.id;
    if (id && savedProps.has(id)) btn.classList.add('saved');
  });
}

document.addEventListener('click', e => {
  const saveBtn = e.target.closest('.property-save');
  if (!saveBtn) return;
  const id = saveBtn.dataset.id;
  if (!id) return;

  if (savedProps.has(id)) {
    savedProps.delete(id);
    saveBtn.classList.remove('saved');
    saveBtn.textContent = '🤍';
    showToast('Removed from saved', '🗑️');
  } else {
    savedProps.add(id);
    saveBtn.classList.add('saved');
    saveBtn.textContent = '❤️';
    showToast('Saved to wishlist!', '❤️');
  }
  localStorage.setItem('tuhame-saved', JSON.stringify([...savedProps]));
});

updateSaveBtns();

// ─── Toast Notifications ───
function showToast(message, icon = '✅', duration = 3000) {
  let container = document.querySelector('.toast-container');
  if (!container) {
    container = document.createElement('div');
    container.className = 'toast-container';
    document.body.appendChild(container);
  }

  const toast = document.createElement('div');
  toast.className = 'toast';
  toast.innerHTML = `<span class="toast-icon">${icon}</span><span>${message}</span>`;
  container.appendChild(toast);

  requestAnimationFrame(() => {
    requestAnimationFrame(() => toast.classList.add('show'));
  });

  setTimeout(() => {
    toast.classList.remove('show');
    setTimeout(() => toast.remove(), 400);
  }, duration);
}

// ─── Filter Chips ───
document.querySelectorAll('.filter-chip').forEach(chip => {
  chip.addEventListener('click', function () {
    const group = this.closest('.filter-chips');
    if (group) group.querySelectorAll('.filter-chip').forEach(c => c.classList.remove('active'));
    this.classList.toggle('active');
  });
});

document.querySelectorAll('.map-filter-chip').forEach(chip => {
  chip.addEventListener('click', function () {
    this.classList.toggle('active');
  });
});

// ─── View Toggle (Grid/List) ───
const viewToggles = document.querySelectorAll('.view-toggle');
const propertiesGrid = document.querySelector('.properties-grid');

viewToggles.forEach(btn => {
  btn.addEventListener('click', function () {
    viewToggles.forEach(b => b.classList.remove('active'));
    this.classList.add('active');
    if (propertiesGrid) {
      const isGrid = this.dataset.view === 'grid';
      propertiesGrid.style.gridTemplateColumns = isGrid
        ? 'repeat(auto-fill, minmax(300px, 1fr))'
        : '1fr';
    }
  });
});

// ─── Price Range Slider ───
const priceSlider = document.querySelector('#price-slider');
const priceDisplay = document.querySelector('#price-display');

if (priceSlider && priceDisplay) {
  priceSlider.addEventListener('input', function () {
    priceDisplay.textContent = `KES ${Number(this.value).toLocaleString()}`;
  });
}

// ─── Map Listing Sync ───
const mapCards = document.querySelectorAll('.map-listing-card');

mapCards.forEach(card => {
  card.addEventListener('click', function () {
    mapCards.forEach(c => c.classList.remove('active'));
    this.classList.add('active');
    showToast(`Viewing: ${this.dataset.name || 'Property'}`, '📍');
  });
});

// ─── Profile Nav Tabs ───
const profileNavItems = document.querySelectorAll('.profile-nav-item');
const profileSections = document.querySelectorAll('.profile-section');

profileNavItems.forEach(item => {
  item.addEventListener('click', function () {
    const target = this.dataset.section;
    profileNavItems.forEach(i => i.classList.remove('active'));
    this.classList.add('active');
    profileSections.forEach(s => {
      s.style.display = s.id === target ? 'block' : 'none';
    });
  });
});

// ─── QR Code Generator ───
function generateQR(canvas, text) {
  if (!canvas) return;
  const ctx = canvas.getContext('2d');
  const size = canvas.width;
  // Simple visual QR pattern (decorative)
  ctx.fillStyle = '#fff';
  ctx.fillRect(0, 0, size, size);
  ctx.fillStyle = '#0F172A';

  const modules = 21;
  const cellSize = size / modules;

  // Generate pseudo-random pattern based on text
  const hash = text.split('').reduce((a, c) => (a << 5) - a + c.charCodeAt(0), 0);
  const rng = (seed) => {
    seed = ((seed + 0x6D2B79F5) + ((seed << 14) - (seed >> 2))) | 0;
    return (seed >>> 0) / 4294967296;
  };

  for (let row = 0; row < modules; row++) {
    for (let col = 0; col < modules; col++) {
      // Finder patterns (corners)
      if (
        (row < 7 && col < 7) ||
        (row < 7 && col >= modules - 7) ||
        (row >= modules - 7 && col < 7)
      ) {
        const inFinder = (r, c) => r >= 1 && r <= 5 && c >= 1 && c <= 5
          ? r >= 2 && r <= 4 && c >= 2 && c <= 4
          : true;
        const localRow = row < 7 ? row : row - (modules - 7);
        const localCol = col < 7 ? col : col - (modules - 7);
        if (row >= modules - 7 && col >= modules - 7) continue;
        ctx.fillStyle = inFinder(localRow, localCol) ? '#0F172A' : '#fff';
        ctx.fillRect(col * cellSize, row * cellSize, cellSize, cellSize);
      } else {
        if (rng(hash + row * modules + col) > 0.5) {
          ctx.fillRect(col * cellSize, row * cellSize, cellSize, cellSize);
        }
      }
    }
  }
}

const qrCanvas = document.querySelector('#qr-canvas');
if (qrCanvas) {
  generateQR(qrCanvas, 'TUHAME-HOUSE-001-TENANT-456');
}

// ─── Mortgage Calculator ───
const mortgageForm = document.querySelector('#mortgage-calc');
if (mortgageForm) {
  mortgageForm.addEventListener('input', calcMortgage);

  function calcMortgage() {
    const price = parseFloat(document.querySelector('#loan-amount')?.value || 0);
    const rate = parseFloat(document.querySelector('#interest-rate')?.value || 0) / 100 / 12;
    const months = parseInt(document.querySelector('#loan-term')?.value || 0) * 12;
    const result = document.querySelector('#mortgage-result');

    if (!price || !rate || !months || !result) return;

    const monthly = (price * rate * Math.pow(1 + rate, months)) / (Math.pow(1 + rate, months) - 1);
    result.textContent = isFinite(monthly)
      ? `KES ${Math.round(monthly).toLocaleString()} / month`
      : '—';
  }
}

// ─── Move Cost Calculator ───
const moveCostForm = document.querySelector('#move-calc');
if (moveCostForm) {
  moveCostForm.addEventListener('input', calcMoveCost);

  function calcMoveCost() {
    const distance = parseFloat(document.querySelector('#move-distance')?.value || 0);
    const rooms = parseInt(document.querySelector('#move-rooms')?.value || 1);
    const result = document.querySelector('#move-cost-result');
    if (!result) return;

    const base = 3000;
    const perKm = 150;
    const perRoom = 800;
    const total = base + (distance * perKm) + (rooms * perRoom);
    result.textContent = `Estimated: KES ${Math.round(total).toLocaleString()}`;
  }
}

// ─── Search Live Filter ───
const searchInput = document.querySelector('.live-search');
const propertyCards = document.querySelectorAll('.property-card[data-name]');

if (searchInput && propertyCards.length) {
  searchInput.addEventListener('input', function () {
    const query = this.value.toLowerCase();
    propertyCards.forEach(card => {
      const name = card.dataset.name?.toLowerCase() || '';
      const loc = card.dataset.location?.toLowerCase() || '';
      card.style.display = (name.includes(query) || loc.includes(query)) ? '' : 'none';
    });
  });
}

// ─── Photo Gallery Lightbox ───
const galleryImgs = document.querySelectorAll('.gallery-img');

galleryImgs.forEach(img => {
  img.addEventListener('click', function () {
    const overlay = document.createElement('div');
    overlay.style.cssText = `
      position:fixed;inset:0;background:rgba(0,0,0,0.95);
      z-index:9999;display:flex;align-items:center;justify-content:center;
      cursor:pointer;animation:fadeIn 0.2s ease;
    `;

    const bigImg = document.createElement('img');
    bigImg.src = this.src;
    bigImg.style.cssText = 'max-width:90vw;max-height:90vh;border-radius:12px;object-fit:contain;';

    const closeBtn = document.createElement('button');
    closeBtn.innerHTML = '✕';
    closeBtn.style.cssText = `
      position:absolute;top:1.5rem;right:1.5rem;
      background:rgba(255,255,255,0.15);border:none;color:#fff;
      font-size:1.5rem;width:44px;height:44px;border-radius:50%;cursor:pointer;
      display:flex;align-items:center;justify-content:center;
    `;

    overlay.appendChild(bigImg);
    overlay.appendChild(closeBtn);
    document.body.appendChild(overlay);
    document.body.style.overflow = 'hidden';

    const close = () => {
      overlay.remove();
      document.body.style.overflow = '';
    };

    overlay.addEventListener('click', e => { if (e.target === overlay || e.target === closeBtn) close(); });
    document.addEventListener('keydown', e => { if (e.key === 'Escape') close(); }, { once: true });
  });
});

// ─── Auth Form ───
const loginForm = document.querySelector('#login-form');
if (loginForm) {
  loginForm.addEventListener('submit', function (e) {
    e.preventDefault();
    showToast('Signing you in…', '🔐');
    setTimeout(() => {
      window.location.href = 'profile.html';
    }, 1500);
  });
}

const registerForm = document.querySelector('#register-form');
if (registerForm) {
  registerForm.addEventListener('submit', function (e) {
    e.preventDefault();
    const pw = document.querySelector('#reg-password')?.value;
    const pw2 = document.querySelector('#reg-confirm-password')?.value;
    if (pw !== pw2) {
      showToast('Passwords do not match', '❌');
      return;
    }
    showToast('Creating your account…', '🎉');
    setTimeout(() => {
      window.location.href = 'profile.html';
    }, 1500);
  });
}

// ─── Number Counter Animation ───
function animateCounter(el) {
  const target = parseInt(el.dataset.target);
  const duration = 2000;
  const start = performance.now();

  function update(now) {
    const progress = Math.min((now - start) / duration, 1);
    const eased = 1 - Math.pow(1 - progress, 3);
    el.textContent = Math.round(eased * target).toLocaleString() + (el.dataset.suffix || '');
    if (progress < 1) requestAnimationFrame(update);
  }
  requestAnimationFrame(update);
}

const counters = document.querySelectorAll('[data-target]');
if (counters.length && 'IntersectionObserver' in window) {
  const counterObserver = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        animateCounter(entry.target);
        counterObserver.unobserve(entry.target);
      }
    });
  }, { threshold: 0.5 });

  counters.forEach(c => counterObserver.observe(c));
}

// ─── Move Score Bars Animation ───
const scoreBars = document.querySelectorAll('.score-bar-fill');
if (scoreBars.length && 'IntersectionObserver' in window) {
  const barObserver = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        entry.target.style.width = entry.target.dataset.width || '0%';
        barObserver.unobserve(entry.target);
      }
    });
  }, { threshold: 0.5 });

  scoreBars.forEach(bar => {
    bar.style.width = '0%';
    barObserver.observe(bar);
  });
}

console.log('🏠 TuHame loaded. Find. Move. Settle.');