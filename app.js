/* ==========================================================
   IJRO INTIZOMI MONITORING DASHBOARD  |  Client Logic
   ========================================================== */

const API_BASE = window.location.origin.startsWith('http')
  ? `${window.location.origin}/api`
  : 'http://127.0.0.1:8000/api';

/* ---------- SVG Icons ---------- */
const ICONS = {
  plus: '<path d="M12 5v14M5 12h14"/>',
  sparkle: '<path d="M12 3v4M12 17v4M3 12h4M17 12h4M6.3 6.3l2.5 2.5M15.2 15.2l2.5 2.5M6.3 17.7l2.5-2.5M15.2 8.8l2.5-2.5"/>',
  arrowLeft: '<path d="M19 12H5M12 19l-7-7 7-7"/>',
  arrowRight: '<path d="M5 12h14M12 5l7 7-7 7"/>',
  arrowUpRight: '<path d="M7 17L17 7M8 7h9v9"/>',
  arrowUp: '<path d="M12 19V5M5 12l7-7 7 7"/>',
  arrowDown: '<path d="M12 5v14M19 12l-7 7-7-7"/>',
  sliders: '<path d="M4 6h10M18 6h2M4 12h4M12 12h8M4 18h12M20 18h0"/><circle cx="16" cy="6" r="2"/><circle cx="10" cy="12" r="2"/><circle cx="18" cy="18" r="2"/>',
  alert: '<circle cx="12" cy="12" r="9"/><path d="M12 8v4.5M12 16h.01"/>',
  calendar: '<rect x="3.5" y="5" width="17" height="15.5" rx="3"/><path d="M8 3v4M16 3v4M3.5 10h17"/>',
  clock: '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
  wallet: '<path d="M19 7V5.5A1.5 1.5 0 0 0 17.5 4H6a2 2 0 0 0 0 4h13a1 1 0 0 1 1 1v9a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6"/><path d="M16 14h.01"/>',
  chevronDown: '<path d="M6 9l6 6 6-6"/>',
  chevronLeft: '<path d="M15 18l-6-6 6-6"/>',
  chevronRight: '<path d="M9 18l6-6-6-6"/>',
  search: '<circle cx="11" cy="11" r="7"/><path d="M20 20l-3.5-3.5"/>',
  bell: '<path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"/><path d="M13.7 21a2 2 0 0 1-3.4 0"/>',
  settings: '<circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.7 1.7 0 0 0 .3 1.8l.1.1a2 2 0 1 1-2.8 2.8l-.1-.1a1.7 1.7 0 0 0-1.8-.3 1.7 1.7 0 0 0-1 1.5V21a2 2 0 0 1-4 0v-.1a1.7 1.7 0 0 0-1.1-1.5 1.7 1.7 0 0 0-1.8.3l-.1.1a2 2 0 1 1-2.8-2.8l.1-.1a1.7 1.7 0 0 0 .3-1.8 1.7 1.7 0 0 0-1.5-1H3a2 2 0 0 1 0-4h.1a1.7 1.7 0 0 0 1.5-1.1 1.7 1.7 0 0 0-.3-1.8l-.1-.1a2 2 0 1 1 2.8-2.8l.1.1a1.7 1.7 0 0 0 1.8.3H9a1.7 1.7 0 0 0 1-1.5V3a2 2 0 0 1 4 0v.1a1.7 1.7 0 0 0 1 1.5 1.7 1.7 0 0 0 1.8-.3l.1-.1a2 2 0 1 1 2.8 2.8l-.1.1a1.7 1.7 0 0 0-.3 1.8V9a1.7 1.7 0 0 0 1.5 1H21a2 2 0 0 1 0 4h-.1a1.7 1.7 0 0 0-1.5 1z"/>',
  file: '<path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z"/><path d="M14 3v5h5M9 13h6M9 17h6"/>',
  receipt: '<rect x="4.5" y="3.5" width="15" height="17" rx="2.5"/><path d="M14.5 9c0-.9-1-1.5-2.5-1.5S9.5 8.2 9.5 9.2s1 1.4 2.5 1.8 2.5.8 2.5 1.8-1 1.7-2.5 1.7-2.5-.6-2.5-1.5M12 6.5v1M12 14.5v1M9 18h6"/>',
  clipboard: '<rect x="8.5" y="2.5" width="7" height="4" rx="1"/><path d="M15.5 4.5H17a2 2 0 0 1 2 2V19a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6.5a2 2 0 0 1 2-2h1.5"/><path d="M9 14l2 2 4-4"/>',
  repeat: '<path d="M17 2l3 3-3 3"/><path d="M4 11V9a4 4 0 0 1 4-4h12"/><path d="M7 22l-3-3 3-3"/><path d="M20 13v2a4 4 0 0 1-4 4H4"/>',
  export: '<rect x="3.5" y="4" width="17" height="16" rx="3"/><path d="M3.5 9h17M10 14h6M13 11.5l3 2.5-3 2.5"/>',
  upload: '<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/>',
  more: '<circle cx="12" cy="5" r="1.2"/><circle cx="12" cy="12" r="1.2"/><circle cx="12" cy="19" r="1.2"/>',
  link: '<path d="M10 13a5 5 0 0 0 7.5.5l3-3a5 5 0 0 0-7-7l-1.7 1.7"/><path d="M14 11a5 5 0 0 0-7.5-.5l-3 3a5 5 0 0 0 7 7l1.7-1.7"/>',
  check: '<path d="M20 6L9 17l-5-5"/>',
  x: '<path d="M18 6L6 18M6 6l12 12"/>',
};

const icon = (name, cls = '') =>
  `<svg class="ic ${cls}" viewBox="0 0 24 24" aria-hidden="true">${ICONS[name] || ''}</svg>`;

function hydrateIcons(root = document) {
  root.querySelectorAll('i[data-i]').forEach(el => {
    el.outerHTML = icon(el.dataset.i, el.className);
  });
}

/* ---------- State ---------- */
const state = {
  token: localStorage.getItem('ijro_token') || '',
  adminUsername: localStorage.getItem('ijro_user') || '',
  currentSectionIdx: 0,
  activeTab: 'tasks',
  selectedTaskId: null,
  filters: {
    boshqarma: 'all',
    holat: 'all',
    risk: 'all',
    ustuvorlik: 'all',
    search: '',
  },
  page: 1,
  pageSize: 10,
  lastUpdatedTimestamp: '',
  tasks: [],
  riskTasks: [],
  departments: [],
  summary: null,
  kpiExcelData: null,
  kpiSelectedLeader: null,
  kpiQuarter: 'q3',
  kpiSearch: '',
};

const SECTIONS = [
  { id: 'ijro', title: 'Ijro nazorati' },
  { id: 'kpi', title: "KPI ko'rsatkichlari" },
];

/* ---------- Helpers ---------- */
const $ = s => document.querySelector(s);
const $$ = s => [...document.querySelectorAll(s)];
const esc = s => String(s || '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));

function toast(msg, type = 'info') {
  const t = document.createElement('div');
  t.className = 'toast';
  t.innerHTML = `${icon('check')} <span>${esc(msg)}</span>`;
  $('#toasts').appendChild(t);
  setTimeout(() => {
    t.classList.add('out');
    setTimeout(() => t.remove(), 300);
  }, 2800);
}

function countUp(el, to, dec = 0, dur = 1000) {
  if (!el) return;
  const from = parseFloat(el.dataset.current || 0);
  const start = performance.now();
  const step = now => {
    const p = Math.min((now - start) / dur, 1);
    const e = 1 - Math.pow(1 - p, 4);
    const v = from + (to - from) * e;
    el.textContent = v.toLocaleString('uz-UZ', { minimumFractionDigits: dec, maximumFractionDigits: dec });
    if (p < 1) requestAnimationFrame(step);
  };
  el.dataset.current = to;
  requestAnimationFrame(step);
}

/* ---------- API Client ---------- */
async function apiRequest(endpoint, options = {}) {
  const headers = {};
  if (!(options.body instanceof FormData)) {
    headers['Content-Type'] = 'application/json';
  }
  if (state.token) {
    headers['Authorization'] = `Bearer ${state.token}`;
  }
  if (options.headers) {
    Object.assign(headers, options.headers);
  }

  try {
    const res = await fetch(`${API_BASE}${endpoint}`, {
      ...options,
      headers
    });

    if (res.status === 401) {
      // Session expired or unauthenticated
      state.token = '';
      localStorage.removeItem('ijro_token');
      showLoginModal(true);
      throw new Error("Autentifikatsiya muddati tugagan");
    }

    if (!res.ok) {
      const errData = await res.json().catch(() => ({}));
      throw new Error(errData.detail || `Server xatosi: ${res.status}`);
    }

    return await res.json();
  } catch (err) {
    console.error(`API Error [${endpoint}]:`, err);
    throw err;
  }
}

/* ---------- Auth Modal ---------- */
function showLoginModal(show = true) {
  const modal = $('#loginModal');
  if (show) {
    modal.classList.add('open');
    $('#loginError').classList.add('hidden');
    $('#loginUsername').focus();
  } else {
    modal.classList.remove('open');
  }
}

$('#loginForm').addEventListener('submit', async e => {
  e.preventDefault();
  const username = $('#loginUsername').value.trim();
  const password = $('#loginPassword').value.trim();
  const errBox = $('#loginError');
  errBox.classList.add('hidden');

  try {
    const data = await apiRequest('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ username, password })
    });

    state.token = data.access_token;
    state.adminUsername = data.username;
    localStorage.setItem('ijro_token', data.access_token);
    localStorage.setItem('ijro_user', data.username);

    showLoginModal(false);
    toast("Xush kelibsiz, Administrator!");
    initDashboard();
  } catch (err) {
    errBox.textContent = err.message || "Login yoki parol noto'g'ri";
    errBox.classList.remove('hidden');
  }
});

$('#btnLogout').addEventListener('click', () => {
  if (confirm("Haqiqatan ham tizimdan chiqmoqchimisiz?")) {
    state.token = '';
    localStorage.removeItem('ijro_token');
    localStorage.removeItem('ijro_user');
    showLoginModal(true);
    toast("Tizimdan chiqildi");
  }
});

/* ---------- Settings & Separate Excel Import Modal ---------- */
async function fetchImportStatus() {
  try {
    const data = await apiRequest('/import/status');
    if (data.main_page) {
      const el = $('#statusTagMainPage');
      if (el) {
        if (data.main_page.exists) {
          el.textContent = `data/main_page/current.xlsx (${data.main_page.total_rows || 0} ta yozuv)`;
          el.className = 'file-status-tag success';
        } else {
          el.textContent = "Fayl mavjud emas";
          el.className = 'file-status-tag empty';
        }
      }
    }
    if (data.kpi) {
      const elKpi = $('#statusTagKpi');
      const elKpiBadge = $('#kpiSourceFileName');
      const label = data.kpi.exists
        ? `data/kpi/current.xlsx (${data.kpi.total_indicators || 0} ta ko'rsatkich)`
        : "Fayl mavjud emas";
      if (elKpi) {
        elKpi.textContent = label;
        elKpi.className = data.kpi.exists ? 'file-status-tag success' : 'file-status-tag empty';
      }
      if (elKpiBadge) {
        elKpiBadge.textContent = 'data/kpi/current.xlsx';
      }
    }
  } catch (err) {
    console.error("fetchImportStatus error:", err);
  }
}

async function uploadMainPageExcel(file, triggerBtnSelector = null) {
  if (!file) return;

  const validExts = ['.xlsx', '.xls'];
  const fileName = file.name.toLowerCase();
  if (!validExts.some(ext => fileName.endsWith(ext))) {
    toast("Faqat Excel (.xlsx, .xls) fayllari qabul qilinadi", 'error');
    return;
  }

  const loadingEl = $('#loadingMainPage');
  if (loadingEl) {
    loadingEl.textContent = "Ma'lumotlar yangilanmoqda...";
    loadingEl.classList.remove('hidden');
  }

  const triggerBtn = triggerBtnSelector ? $(triggerBtnSelector) : null;
  let originalBtnHtml = '';
  if (triggerBtn) {
    originalBtnHtml = triggerBtn.innerHTML;
    triggerBtn.classList.add('loading');
    triggerBtn.disabled = true;
    triggerBtn.innerHTML = `<span class="spin">${icon('repeat')}</span> <span>Yuklanmoqda...</span>`;
  }

  updateSyncBadge('syncing', "Excel tahlil qilinmoqda va hisoblanmoqda...");

  try {
    const formData = new FormData();
    formData.append('file', file);
    const res = await apiRequest('/import/main-page', {
      method: 'POST',
      body: formData
    });

    const successMsg = res.message || `${res.total_records || ''} ta topshiriq muvaffaqiyatli qabul qilindi`;
    toast(successMsg, 'success');
    updateSyncBadge('success', "Ma'lumotlar yangilandi");

    if (res.last_updated) {
      state.lastUpdatedTimestamp = res.last_updated;
      const lu = $('#lastUpdatedText');
      if (lu) lu.textContent = `So'nggi yangilanish: ${res.last_updated}`;
    }

    // Immediately recalculate & update all dashboard views based on uploaded file
    await refreshAllData(false);
    await fetchImportStatus();
  } catch (err) {
    console.error("Main page import error:", err);
    toast(err.message || "1-sahifa Excel ma'lumotlarini o'qishda xatolik yuz berdi", 'error');
    updateSyncBadge('error', "Excel ma'lumotlarini o'qishda xatolik");
    const errBox = $('#passwordError');
    if (errBox) {
      errBox.textContent = `1-sahifa xatosi: ${err.message}`;
      errBox.classList.remove('hidden');
    }
  } finally {
    if (loadingEl) loadingEl.classList.add('hidden');
    if (triggerBtn) {
      triggerBtn.classList.remove('loading');
      triggerBtn.disabled = false;
      triggerBtn.innerHTML = originalBtnHtml;
      hydrateIcons(triggerBtn);
    }
  }
}

async function uploadKpiExcel(file) {
  if (!file) return;
  const loadingEl = $('#loadingKpi');
  if (loadingEl) {
    loadingEl.textContent = "Ma'lumotlar yangilanmoqda...";
    loadingEl.classList.remove('hidden');
  }
  updateSyncBadge('syncing', "Ma'lumotlar yangilanmoqda...");

  try {
    const formData = new FormData();
    formData.append('file', file);
    await apiRequest('/import/kpi', {
      method: 'POST',
      body: formData
    });

    toast("Ma'lumotlar muvaffaqiyatli yangilandi");
    updateSyncBadge('success', "Ma'lumotlar muvaffaqiyatli yangilandi");
    state.kpiExcelData = null;
    await renderKPITable(true);
    await fetchImportStatus();
  } catch (err) {
    console.error("KPI import error:", err);
    toast("KPI Excel ma'lumotlarini o'qishda xatolik yuz berdi", 'error');
    updateSyncBadge('error', "KPI Excel ma'lumotlarini o'qishda xatolik yuz berdi");
    const errBox = $('#passwordError');
    if (errBox) {
      errBox.textContent = `KPI xatosi: ${err.message}`;
      errBox.classList.remove('hidden');
    }
  } finally {
    if (loadingEl) loadingEl.classList.add('hidden');
  }
}

// Ijro nazorati sahifasi: to'g'ridan-to'g'ri "Import fayl" tugmasi
$('#btnImportIjroDirect')?.addEventListener('click', () => {
  $('#fileInputIjroDirect')?.click();
});

$('#fileInputIjroDirect')?.addEventListener('change', async e => {
  const file = e.target.files?.[0];
  if (file) {
    await uploadMainPageExcel(file, '#btnImportIjroDirect');
    e.target.value = '';
  }
});

// 1-sahifa Excel import triggers (Settings modal)
$('#btnSelectMainPageExcel')?.addEventListener('click', () => {
  $('#fileInputMainPage')?.click();
});

$('#fileInputMainPage')?.addEventListener('change', e => {
  const file = e.target.files?.[0];
  if (file) {
    uploadMainPageExcel(file, '#btnSelectMainPageExcel');
    e.target.value = '';
  }
});

// KPI Excel import triggers (Settings modal)
$('#btnSelectKpiExcel')?.addEventListener('click', () => {
  $('#fileInputKpi')?.click();
});

$('#fileInputKpi')?.addEventListener('change', e => {
  const file = e.target.files?.[0];
  if (file) {
    uploadKpiExcel(file);
    e.target.value = '';
  }
});

// KPI Excel import triggers (KPI page direct button)
$('#btnSelectKpiDirect')?.addEventListener('click', () => {
  $('#fileInputKpiDirect')?.click();
});

$('#fileInputKpiDirect')?.addEventListener('change', e => {
  const file = e.target.files?.[0];
  if (file) {
    uploadKpiExcel(file);
    e.target.value = '';
  }
});

$('#btnSettingsTop')?.addEventListener('click', () => {
  $('#changePasswordModal')?.classList.add('open');
  $('#passwordError')?.classList.add('hidden');
  $('#changePasswordForm')?.reset();
  fetchImportStatus();
});

$('#btnCancelPassword')?.addEventListener('click', () => {
  $('#changePasswordModal')?.classList.remove('open');
});

$('#changePasswordForm')?.addEventListener('submit', async e => {
  e.preventDefault();
  const old_password = $('#oldPassword').value;
  const new_password = $('#newPassword').value;
  const confirm_password = $('#confirmPassword').value;
  const errBox = $('#passwordError');
  errBox.classList.add('hidden');

  if (new_password !== confirm_password) {
    errBox.textContent = "Yangi parollar mos kelmadi!";
    errBox.classList.remove('hidden');
    return;
  }

  try {
    await apiRequest('/settings/change-password', {
      method: 'POST',
      body: JSON.stringify({ old_password, new_password })
    });
    $('#changePasswordModal').classList.remove('open');
    toast("Parol muvaffaqiyatli o'zgartirildi!");
  } catch (err) {
    errBox.textContent = err.message;
    errBox.classList.remove('hidden');
  }
});

/* ---------- Navigation & Indicators ---------- */
function moveIndicator() {
  const active = $('#mainNav button.active');
  const ind = $('#navIndicator');
  if (active && ind) {
    ind.style.left = active.offsetLeft + 'px';
    ind.style.width = active.offsetWidth + 'px';
  }
}

function switchSection(idx, notify = true) {
  state.currentSectionIdx = (idx + SECTIONS.length) % SECTIONS.length;
  const sec = SECTIONS[state.currentSectionIdx];
  const titleEl = $('#pageTitle');
  if (titleEl) {
    titleEl.style.opacity = '0';
    titleEl.style.transform = 'translateY(4px)';
    setTimeout(() => {
      titleEl.textContent = sec.title;
      titleEl.style.opacity = '1';
      titleEl.style.transform = 'translateY(0)';
    }, 140);
  }

  const targetNavBtn = $(`#mainNav button[data-nav="${sec.id}"]`);
  if (targetNavBtn) {
    $$('#mainNav button').forEach(x => x.classList.remove('active'));
    targetNavBtn.classList.add('active');
    moveIndicator();
  }

  const ijroStats = $('#ijroStats');
  const sectionKPI = $('#sectionKPI');
  const mainDualSection = $('#mainDualSection');
  const btnImportIjroDirect = $('#btnImportIjroDirect');

  if (sec.id === 'kpi') {
    state.activeTab = 'kpi';
    stopHeadsRotation();
    if (ijroStats) ijroStats.classList.add('hidden');
    if (mainDualSection) mainDualSection.classList.add('hidden');
    if (sectionKPI) sectionKPI.classList.remove('hidden');
    if (btnImportIjroDirect) btnImportIjroDirect.classList.add('hidden');
    renderKPITable(true);
  } else {
    state.activeTab = 'tasks';
    if (sectionKPI) sectionKPI.classList.add('hidden');
    if (ijroStats) ijroStats.classList.remove('hidden');
    if (mainDualSection) mainDualSection.classList.remove('hidden');
    if (btnImportIjroDirect) btnImportIjroDirect.classList.remove('hidden');
    renderSystemsMatrix();
    renderDepartmentHeadsRotator();
  }

  if (notify) {
    toast(`${sec.title} bo'limi tanlandi`);
  }
}

// Board internal tab switching (Topshiriqlar, Reyting, Risklar, Grafiklar)
document.addEventListener('click', e => {
  const tabBtn = e.target.closest('#boardTabs .tab');
  if (!tabBtn) return;
  const tabName = tabBtn.dataset.tab;
  if (!tabName) return;

  state.activeTab = tabName;
  $$('#boardTabs .tab').forEach(b => b.classList.toggle('active', b === tabBtn));

  const panelMap = {
    tasks: '#viewTasks',
    departments: '#viewDepartments',
    risks: '#viewRisks',
    charts: '#viewCharts'
  };

  Object.entries(panelMap).forEach(([k, sel]) => {
    const p = $(sel);
    if (p) p.classList.toggle('hidden', k !== tabName);
  });

  if (tabName === 'charts') renderCharts();
  if (tabName === 'departments') renderDepartmentsTable();
  if (tabName === 'risks') renderRisksTable();
  if (tabName === 'tasks') fetchTasks();
});

$('#mainNav').addEventListener('click', e => {
  const b = e.target.closest('button[data-nav]');
  if (!b) return;
  const idx = SECTIONS.findIndex(s => s.id === b.dataset.nav);
  if (idx !== -1) {
    switchSection(idx);
  }
});

$('#btnPrev')?.addEventListener('click', () => switchSection(state.currentSectionIdx - 1));
$('#btnNext')?.addEventListener('click', () => switchSection(state.currentSectionIdx + 1));
window.addEventListener('resize', moveIndicator);

/* ---------- Summary & KPI Cards ---------- */
function updateSyncBadge(status, msg) {
  const badge = $('#syncBadge');
  const iconSpan = $('#syncIcon');
  const textSpan = $('#syncText');
  if (!badge) return;

  badge.className = `sync-badge ${status}`;
  if (status === 'syncing') {
    if (iconSpan) iconSpan.innerHTML = `<span class="sync-spin">↻</span> `;
    if (textSpan) textSpan.textContent = msg || "Yangilanmoqda...";
  } else if (status === 'error') {
    if (iconSpan) iconSpan.innerHTML = `✕ `;
    if (textSpan) textSpan.textContent = msg || "Excel ma'lumotlarini yangilashda xatolik";
  } else {
    if (iconSpan) iconSpan.innerHTML = `✓ `;
    if (textSpan) textSpan.textContent = msg || "Ma'lumotlar yangilandi";
  }
}

async function fetchSummary() {
  try {
    const params = new URLSearchParams();
    if (state.filters.boshqarma !== 'all') params.set('boshqarma', state.filters.boshqarma);
    if (state.filters.holat !== 'all') params.set('holat', state.filters.holat);
    if (state.filters.risk !== 'all') params.set('risk', state.filters.risk);

    const data = await apiRequest(`/dashboard/summary?${params.toString()}`);
    state.summary = data;

    countUp($('#kpiJami'), data.jami_topshiriqlar);
    countUp($('#kpiBajarilgan'), data.bajarilgan);
    countUp($('#kpiJarayonda'), data.jarayonda);
    countUp($('#kpiBoshlanmagan'), data.boshlanmagan);
    countUp($('#kpiMuddatiOtgan'), data.muddati_otgan);
    countUp($('#kpiYuqoriRisk'), data.yuqori_risk);
    countUp($('#kpiFoiz'), data.umumiy_bajarilish_foizi, 1);

    $('#kpiProgressBar').style.width = `${Math.min(100, data.umumiy_bajarilish_foizi)}%`;
    $('#scoreBtn').textContent = `${Math.round(data.umumiy_bajarilish_foizi)}%`;

    if (data.is_syncing || data.sync_status === 'syncing') {
      updateSyncBadge('syncing', data.sync_message || 'Yangilanmoqda...');
    } else if (data.sync_status === 'error') {
      updateSyncBadge('error', data.sync_message || "Excel ma'lumotlarini yangilashda xatolik");
    } else {
      updateSyncBadge('success', data.sync_message || "Ma'lumotlar yangilandi");
    }

    if (data.songgi_yangilanish) {
      $('#lastUpdatedText').textContent = `So'nggi yangilanish: ${data.songgi_yangilanish}`;
      // Check if Excel updated automatically via watchdog
      if (state.lastUpdatedTimestamp && state.lastUpdatedTimestamp !== data.songgi_yangilanish) {
        toast("Excel faylidan yangi ma'lumotlar avtomatik yuklandi!");
        refreshAllData(false);
      }
      state.lastUpdatedTimestamp = data.songgi_yangilanish;
    }
  } catch (err) {
    console.error("Summary fetch error:", err);
  }
}

/* ---------- Tasks Data & Rendering ---------- */
async function fetchTasks() {
  try {
    const params = new URLSearchParams({
      page: state.page,
      page_size: state.pageSize,
      boshqarma: state.filters.boshqarma,
      holat: state.filters.holat,
      risk: state.filters.risk,
      ustuvorlik: state.filters.ustuvorlik,
      search: state.filters.search,
      sort_by: 'days_remaining',
      sort_order: 'asc'
    });

    const res = await apiRequest(`/tasks?${params.toString()}`);
    state.tasks = res.items;
    if ($('#cntTasks')) $('#cntTasks').textContent = res.total;

    if (!state.selectedTaskId && res.items.length > 0) {
      state.selectedTaskId = res.items[0].id;
    }

    renderTasksList(res);
    if (state.activeTab === 'tasks') renderFullTable(res);
  } catch (err) {
    console.error("Tasks fetch error:", err);
  }
}

function renderTasksList(res) {
  const listEl = $('#invList');
  if (!listEl) return;
  if (!res.items || res.items.length === 0) {
    listEl.innerHTML = `<li class="empty">Qidiruv yoki filtr bo'yicha topshiriqlar topilmadi</li>`;
    renderDetail(null);
    return;
  }

  listEl.innerHTML = res.items.map((t, idx) => `
    <li class="inv ${t.id === state.selectedTaskId ? 'active' : ''}" data-id="${t.id}" tabindex="0" style="animation-delay:${idx * 30}ms">
      <div class="badge-ic ${t.risk_level === 'Kritik' ? 'red' : t.risk_level === 'Yuqori' ? 'purple' : 'blue'}">
        ${icon(t.is_overdue ? 'alert' : 'clipboard', 'sm')}
      </div>
      <div>
        <div class="id"># ${esc(t.id)}</div>
        <div class="due">${esc(t.boshqarma)} • ${t.is_overdue ? '<b style="color:#f87171">Muddati o\'tgan!</b>' : `Qolgan: ${t.days_remaining} kun`}</div>
      </div>
      <span class="pill ${t.risk_level.toLowerCase()}">${esc(t.risk_level)}</span>
      <span class="amt">${t.bajarilish_foizi}%</span>
    </li>
  `).join('');

  renderPagination(res, '#paginationBar');
  renderDetail(res.items.find(t => t.id === state.selectedTaskId) || res.items[0]);
}

function renderPagination(res, containerSel) {
  const bar = $(containerSel);
  if (!bar) return;
  bar.innerHTML = `
    <button class="page-btn" ${res.page <= 1 ? 'disabled' : ''} data-p="${res.page - 1}">${icon('chevronLeft', 'xs')} Oldingi</button>
    <span class="page-info">${res.page} / ${res.total_pages} (${res.total} ta)</span>
    <button class="page-btn" ${res.page >= res.total_pages ? 'disabled' : ''} data-p="${res.page + 1}">Keyingi ${icon('chevronRight', 'xs')}</button>
  `;

  bar.querySelectorAll('button[data-p]').forEach(b => {
    b.addEventListener('click', () => {
      state.page = Number(b.dataset.p);
      fetchTasks();
    });
  });
}

function renderDetail(task) {
  const el = $('#detail');
  if (!el) return;
  if (!task) {
    el.innerHTML = `<div style="margin:auto;text-align:center;padding:60px 0;opacity:.8">${icon('search', 'lg')}<p style="margin-top:10px">Topshiriq tanlanmagan</p></div>`;
    return;
  }

  el.classList.remove('swap');
  void el.offsetWidth;
  el.classList.add('swap');

  el.innerHTML = `
    <div class="d-top">
      <div>
        <div class="d-lbl">Topshiriq kodi va holati</div>
        <div class="inv-no"># ${esc(task.id)} <span class="pill ${task.holat.toLowerCase()}">${esc(task.holat)}</span></div>
      </div>
      <div>
        <div class="d-lbl">Mas'ul boshqarma</div>
        <div class="company" style="font-size:16px">${esc(task.boshqarma)}</div>
      </div>
      <div>
        <div class="d-lbl">Ijrochi mas'ul</div>
        <div class="customer">
          <img src="assets/man1.jpg" alt="${esc(task.masul)}">
          <div><b>${esc(task.masul)}</b><small>Bosh mutaxassis</small></div>
        </div>
      </div>
    </div>

    <div class="task-description-box" style="background:rgba(255,255,255,.1);border-radius:16px;padding:16px;margin:12px 0;">
      <div class="d-lbl" style="margin-bottom:6px">Topshiriq mazmuni</div>
      <p style="font-size:14px;line-height:1.5;color:#fff">${esc(task.topshiriq)}</p>
      ${task.izoh ? `<div style="margin-top:10px;font-size:12px;color:rgba(255,255,255,.78)"><b>Izoh:</b> ${esc(task.izoh)}</div>` : ''}
    </div>

    <div class="d-items" style="grid-template-columns: repeat(4, 1fr);">
      <div class="item">
        <div class="val">${task.bajarilish_foizi}%</div>
        <div class="name">Bajarilish darajasi</div>
      </div>
      <div class="item">
        <div class="val" style="color:${task.days_remaining < 0 ? '#fca5a5' : '#fff'}">${task.days_remaining} kun</div>
        <div class="name">Qolgan muddat</div>
      </div>
      <div class="item">
        <div class="val"><span class="pill ${task.risk_level.toLowerCase()}">${esc(task.risk_level)}</span></div>
        <div class="name">Risk baholash</div>
      </div>
      <div class="item">
        <div class="val">${esc(task.ustuvorlik)}</div>
        <div class="name">Ustuvorlik</div>
      </div>
    </div>

    <div class="d-foot">
      <div><small>Berilgan sana</small><strong>${task.berilgan_sana || '—'}</strong></div>
      <div><small>Ijro muddati</small><strong>${task.muddat}</strong></div>
      <div><small>Holati</small><strong style="color:${task.is_overdue ? '#fca5a5' : '#4ade80'}">${task.is_overdue ? 'Kechikkan' : task.holat}</strong></div>
      <div class="acts">
        <button class="white-btn" onclick="alert('Topshiriq kodi: ${task.id}\\nHolati: ${task.holat}')">Batafsil ma'lumot</button>
      </div>
    </div>
  `;
}

$('#invList')?.addEventListener('click', e => {
  const li = e.target.closest('.inv');
  if (!li) return;
  state.selectedTaskId = li.dataset.id;
  $$('.inv').forEach(x => x.classList.toggle('active', x === li));
  const t = state.tasks.find(x => x.id === state.selectedTaskId);
  renderDetail(t);
});

/* ---------- Full Table View ---------- */
async function renderFullTable() {
  const tbody = $('#allTasksBody');
  if (!tbody) return;

  const res = await apiRequest(`/tasks?page=${state.page}&page_size=${state.pageSize}&boshqarma=${state.filters.boshqarma}&holat=${state.filters.holat}&risk=${state.filters.risk}&search=${state.filters.search}`);
  state.tasks = res.items;

  tbody.innerHTML = res.items.map(t => `
    <tr>
      <td><b># ${esc(t.id)}</b></td>
      <td>${esc(t.boshqarma)}</td>
      <td style="max-width:280px">${esc(t.topshiriq)}</td>
      <td>${esc(t.masul)}</td>
      <td>${t.berilgan_sana || '—'}</td>
      <td>${t.muddat}</td>
      <td><span class="pill ${t.holat.toLowerCase()}">${esc(t.holat)}</span></td>
      <td><b>${t.bajarilish_foizi}%</b></td>
      <td style="color:${t.days_remaining < 0 ? '#f87171' : '#cbd5e1'};font-weight:600">${t.days_remaining} kun</td>
      <td><span class="pill ${t.risk_level.toLowerCase()}">${esc(t.risk_level)}</span></td>
      <td>${esc(t.ustuvorlik)}</td>
    </tr>
  `).join('');

  renderPagination(res, '#tablePaginationBar');
}

/* ---------- High Risk View ---------- */
async function renderRisksTable() {
  const tbody = $('#riskTableBody');
  if (!tbody) return;

  const data = await apiRequest('/risks');
  state.riskTasks = data.all_risks;
  if ($('#cntRisks')) $('#cntRisks').textContent = (data.critical.length + data.high.length);

  tbody.innerHTML = data.all_risks.map(t => `
    <tr style="${t.risk_level === 'Kritik' ? 'background:rgba(220,38,38,.08)' : ''}">
      <td><b># ${esc(t.id)}</b></td>
      <td>${esc(t.boshqarma)}</td>
      <td style="max-width:300px">${esc(t.topshiriq)}</td>
      <td>${esc(t.masul)}</td>
      <td>${t.muddat}</td>
      <td style="color:${t.days_remaining < 0 ? '#f87171' : '#fb923c'};font-weight:700">${t.days_remaining} kun</td>
      <td><b>${t.bajarilish_foizi}%</b></td>
      <td><span class="pill ${t.risk_level.toLowerCase()}">${esc(t.risk_level)}</span></td>
      <td>${esc(t.ustuvorlik)}</td>
    </tr>
  `).join('');
}

/* ---------- Department Ranking View ---------- */
async function renderDepartmentsTable() {
  const tbody = $('#deptTableBody');
  if (!tbody) return;

  const depts = await apiRequest('/departments');
  state.departments = depts;

  // Also fill filter dropdown if present
  const select = $('#fBoshqarma');
  if (select && select.children.length <= 1) {
    depts.forEach(d => {
      const opt = document.createElement('option');
      opt.value = d.boshqarma;
      opt.textContent = d.boshqarma;
      select.appendChild(opt);
    });
  }

  tbody.innerHTML = depts.map(d => `
    <tr>
      <td><b style="font-size:16px;color:#a855f7">#${d.rank}</b></td>
      <td><b>${esc(d.boshqarma)}</b></td>
      <td>${d.jami}</td>
      <td style="color:#4ade80">${d.bajarilgan}</td>
      <td style="color:#60a5fa">${d.jarayonda}</td>
      <td style="color:#f87171;font-weight:600">${d.muddati_otgan}</td>
      <td style="color:#fb923c">${d.yuqori_risk}</td>
      <td>
        <div style="display:flex;align-items:center;gap:8px">
          <span><b>${d.bajarilish_foizi}%</b></span>
          <div style="flex:1;height:6px;background:rgba(255,255,255,.1);border-radius:99px;overflow:hidden">
            <div style="width:${d.bajarilish_foizi}%;height:100%;background:#3b82f6"></div>
          </div>
        </div>
      </td>
      <td><span class="pill purple" style="font-weight:700">${d.score} ball</span></td>
    </tr>
  `).join('');
}

/* ---------- Charts View ---------- */
async function renderCharts() {
  if (!$('#chartHolatBox') && !$('#chartRiskBox') && !$('#chartDeptFoizBox') && !$('#chartDeptOverdueBox')) return;
  const charts = await apiRequest('/dashboard/charts');

  // 1. Holat box
  if ($('#chartHolatBox')) {
    $('#chartHolatBox').innerHTML = charts.holat_stats.map(item => `
      <div class="chart-bar-row">
        <div class="chart-bar-label">${item.name}</div>
        <div class="chart-bar-track">
          <div class="chart-bar-prog" style="width:${item.value * 5}%;background:${item.color || '#3b82f6'}"></div>
        </div>
        <div class="chart-bar-val">${item.value} ta</div>
      </div>
    `).join('');
  }

  // 2. Risk box
  if ($('#chartRiskBox')) {
    $('#chartRiskBox').innerHTML = charts.risk_stats.map(item => `
      <div class="chart-bar-row">
        <div class="chart-bar-label">${item.name} xavf</div>
        <div class="chart-bar-track">
          <div class="chart-bar-prog" style="width:${item.value * 6}%;background:${item.color || '#eab308'}"></div>
        </div>
        <div class="chart-bar-val">${item.value} ta</div>
      </div>
    `).join('');
  }

  // 3. Dept foiz box
  if ($('#chartDeptFoizBox')) {
    $('#chartDeptFoizBox').innerHTML = charts.boshqarma_foizlari.map(item => `
      <div class="chart-bar-row">
        <div class="chart-bar-label">${esc(item.boshqarma)}</div>
        <div class="chart-bar-track">
          <div class="chart-bar-prog" style="width:${item.foiz}%;background:linear-gradient(90deg, #10b981 0%, #3b82f6 100%)"></div>
        </div>
        <div class="chart-bar-val">${item.foiz}%</div>
      </div>
    `).join('');
  }

  // 4. Dept overdue box
  if ($('#chartDeptOverdueBox')) {
    $('#chartDeptOverdueBox').innerHTML = charts.muddati_otgan_boshqarmalar.map(item => `
      <div class="chart-bar-row">
        <div class="chart-bar-label">${esc(item.boshqarma)}</div>
        <div class="chart-bar-track">
          <div class="chart-bar-prog" style="width:${item.overdue * 15}%;background:#ef4444"></div>
        </div>
        <div class="chart-bar-val">${item.overdue} ta</div>
      </div>
    `).join('');
  }
}

/* ==========================================================
   DUAL SPLIT DASHBOARD: SYSTEMS MATRIX & DEPARTMENT HEADS
   ========================================================== */

let systemsMatrixCategories = [];

async function renderSystemsMatrix() {
  const tbody = $('#systemsMatrixBody');
  if (!tbody) return;

  try {
    const data = await apiRequest('/dashboard/systems-breakdown');
    
    // Update summary counts
    const cntIjro = $('#cntIjroTotal');
    const cntEdo = $('#cntEdoTotal');
    if (cntIjro) cntIjro.textContent = data.ijro_gov.jami;
    if (cntEdo) cntEdo.textContent = data.edo_ijro.jami;

    // Combine 5 Ijro.gov.uz categories + 4 Edo.ijro uz categories
    const cats = [
      ...data.ijro_gov.kategoriyalar,
      ...data.edo_ijro.kategoriyalar
    ];
    systemsMatrixCategories = cats;

    tbody.innerHTML = `
      <!-- 1. Jami topshiriqlar -->
      <tr class="matrix-row row-total">
        <td class="row-lbl-cell"><b>Jami topshiriqlar</b></td>
        ${cats.map((c, i) => `
          <td class="cell-val highlight-total ${i === 4 ? 'col-divide-right' : ''}" data-cat-idx="${i}" title="${esc(c.nomi)} (Jami: ${c.jami})">
            ${c.jami}
          </td>
        `).join('')}
      </tr>

      <!-- 2. Bajarilgan -->
      <tr class="matrix-row row-done">
        <td class="row-lbl-cell"><span style="color:#4ade80">●</span> Bajarilgan</td>
        ${cats.map((c, i) => `
          <td class="cell-val c-green ${i === 4 ? 'col-divide-right' : ''}" data-cat-idx="${i}" title="${esc(c.nomi)} (Bajarilgan: ${c.bajarildi})">
            ${c.bajarildi}
          </td>
        `).join('')}
      </tr>

      <!-- 3. Jarayonda -->
      <tr class="matrix-row row-process">
        <td class="row-lbl-cell"><span style="color:#60a5fa">●</span> Jarayonda</td>
        ${cats.map((c, i) => `
          <td class="cell-val c-blue ${i === 4 ? 'col-divide-right' : ''}" data-cat-idx="${i}" title="${esc(c.nomi)} (Jarayonda: ${c.jarayonda})">
            ${c.jarayonda}
          </td>
        `).join('')}
      </tr>

      <!-- 4. Kechikkan (muddati o'tgan) -->
      <tr class="matrix-row row-overdue">
        <td class="row-lbl-cell"><span style="color:#f87171">●</span> Kechikkan</td>
        ${cats.map((c, i) => `
          <td class="cell-val ${c.kechikkan > 0 ? 'c-red' : 'c-gray'} ${i === 4 ? 'col-divide-right' : ''}" data-cat-idx="${i}" title="${esc(c.nomi)} (Kechikkan: ${c.kechikkan})">
            ${c.kechikkan}
          </td>
        `).join('')}
      </tr>

      <!-- 5. Bajarilish foizi -->
      <tr class="matrix-row row-pct">
        <td class="row-lbl-cell">Bajarilish foizi</td>
        ${cats.map((c, i) => `
          <td class="cell-val ${i === 4 ? 'col-divide-right' : ''}" data-cat-idx="${i}" title="${esc(c.nomi)} (Ijro: ${c.foiz}%)">
            <div class="matrix-pct-wrap">
              <span class="matrix-pct">${Math.round(c.foiz)}%</span>
              <div class="matrix-pct-bar">
                <div class="matrix-pct-fill" style="width:${Math.min(100, c.foiz)}%"></div>
              </div>
            </div>
          </td>
        `).join('')}
      </tr>
    `;

    // Click handler for category drilldown tasks
    tbody.querySelectorAll('td[data-cat-idx]').forEach(td => {
      td.addEventListener('click', () => {
        const idx = parseInt(td.dataset.catIdx);
        const selectedCat = systemsMatrixCategories[idx];
        if (selectedCat) {
          showCategoryDrilldown(selectedCat);
        }
      });
    });

  } catch (err) {
    console.error("renderSystemsMatrix error:", err);
  }
}

function showCategoryDrilldown(category) {
  const panel = $('#systemTasksDrilldown');
  const title = $('#drilldownTitle');
  const subtitle = $('#drilldownSubtitle');
  const tbody = $('#drilldownTableBody');
  if (!panel || !tbody) return;

  title.textContent = `${category.nomi} (${category.jami} ta topshiriq)`;
  subtitle.textContent = `Bajarilgan: ${category.bajarildi} ta • Jarayonda: ${category.jarayonda} ta • Kechikkan: ${category.kechikkan} ta • Ijro: ${category.foiz}%`;

  const tasks = category.tasks || [];
  if (tasks.length === 0) {
    tbody.innerHTML = `<tr><td colspan="7" style="text-align:center;padding:20px;color:#94a3b8">Bu kategoriya bo'yicha topshiriqlar mavjud emas</td></tr>`;
  } else {
    tbody.innerHTML = tasks.map(t => `
      <tr>
        <td><b style="color:#a855f7"># ${esc(t.id)}</b></td>
        <td style="max-width:240px;line-height:1.4">${esc(t.topshiriq)}</td>
        <td><span class="head-dept-pill" style="margin:0">${esc(t.boshqarma)}</span></td>
        <td>${esc(t.masul)}</td>
        <td style="color:${t.is_overdue ? '#f87171' : '#cbd5e1'};font-weight:600">${t.muddat}</td>
        <td><span class="pill ${t.holat.toLowerCase()}">${esc(t.holat)}</span></td>
        <td><b style="color:#34d399">${t.bajarilish_foizi}%</b></td>
      </tr>
    `).join('');
  }

  panel.classList.remove('hidden');
  panel.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

// Close drilldown button listener
document.addEventListener('click', e => {
  if (e.target.closest('#btnCloseDrilldown')) {
    $('#systemTasksDrilldown')?.classList.add('hidden');
  }
});

/* ==========================================================
   HEADS ROTATOR SHOWCASE (HAR 5 SEKUNDDA ALMASHIB TURISHI)
   ========================================================== */

let headsRotationProgressTimer = null;
let currentHeadIndex = 0;
let isRotationPaused = false;
const ROTATION_DURATION_MS = 5000;
let elapsedMs = 0;

async function renderDepartmentHeadsRotator() {
  const spotlightWrap = $('#headSpotlightWrap');
  if (!spotlightWrap) return;

  try {
    const depts = await apiRequest('/departments');
    state.departments = depts;

    if (!depts || depts.length === 0) return;

    if (currentHeadIndex >= depts.length) {
      currentHeadIndex = 0;
    }

    // Render active spotlight card
    renderHeadSpotlight(currentHeadIndex);

    // Start auto-rotation every 5 seconds
    startHeadsRotation();

  } catch (err) {
    console.error("renderDepartmentHeadsRotator error:", err);
  }
}

function renderHeadSpotlight(index) {
  const depts = state.departments;
  if (!depts || depts.length === 0) return;

  const spotlightWrap = $('#headSpotlightWrap');
  if (!spotlightWrap) return;

  const d = depts[index];
  if (!d) return;

  spotlightWrap.innerHTML = `
    <div class="spotlight-card centered-style" data-dept="${esc(d.boshqarma)}">
      <!-- O'rtada kattaroq rasm va shaxs ma'lumotlari -->
      <div class="spotlight-center-header">
        <div class="spotlight-avatar-box">
          <img src="${d.rasm || 'assets/man1.jpg'}" alt="${esc(d.boshliq)}" class="spotlight-avatar-large" onerror="this.src='assets/man1.jpg'">
          <span class="spotlight-rank-badge-large">#${d.rank}</span>
        </div>
        <div class="spotlight-person-details">
          <div class="spotlight-name-large">${esc(d.boshliq)}</div>
          <div class="spotlight-meta-row">
            <span class="spotlight-role-text">${esc(d.lavozim)}</span>
            <span class="meta-dot">•</span>
            <span class="spotlight-dept-tag">${esc(d.boshqarma)}</span>
          </div>
          <div class="spotlight-score-row">
            <span class="spotlight-score-tag"><b>${d.score}</b> ball</span>
          </div>
        </div>
      </div>

      <!-- Rasm tagidan topshiriqlar umumiy ijrosi va ko'rsatkichlari -->
      <div class="spotlight-execution-box">
        <div class="spotlight-prog-row">
          <div class="spotlight-prog-label">
            <span>Topshiriqlar umumiy ijrosi</span>
            <span class="spotlight-prog-pct">${d.bajarilish_foizi}%</span>
          </div>
          <div class="spotlight-prog-track">
            <div class="spotlight-prog-fill" style="width: ${Math.min(100, d.bajarilish_foizi)}%"></div>
          </div>
        </div>

        <div class="spotlight-pills-grid">
          <div class="s-pill">
            <span class="s-pill-title">Jami</span>
            <span class="s-pill-val purple">${d.jami}&nbsp;ta</span>
          </div>
          <div class="s-pill">
            <span class="s-pill-title">Bajarildi</span>
            <span class="s-pill-val green">${d.bajarilgan}&nbsp;ta</span>
          </div>
          <div class="s-pill">
            <span class="s-pill-title">Jarayonda</span>
            <span class="s-pill-val blue">${d.jarayonda}&nbsp;ta</span>
          </div>
          <div class="s-pill">
            <span class="s-pill-title">Kechikkan</span>
            <span class="s-pill-val ${d.muddati_otgan > 0 ? 'red' : 'gray'}">${d.muddati_otgan}&nbsp;ta</span>
          </div>
        </div>
      </div>
    </div>
  `;
}

function startHeadsRotation() {
  stopHeadsRotation();
  elapsedMs = 0;

  headsRotationProgressTimer = setInterval(() => {
    elapsedMs += 100;
    const progress = Math.min(100, (elapsedMs / ROTATION_DURATION_MS) * 100);
    const fill = $('#rotatorProgressFill');
    if (fill) fill.style.width = `${progress}%`;

    if (elapsedMs >= ROTATION_DURATION_MS) {
      elapsedMs = 0;
      nextHead();
    }
  }, 100);
}

function stopHeadsRotation() {
  if (headsRotationProgressTimer) {
    clearInterval(headsRotationProgressTimer);
    headsRotationProgressTimer = null;
  }
}

function nextHead() {
  if (!state.departments || state.departments.length === 0) return;
  currentHeadIndex = (currentHeadIndex + 1) % state.departments.length;
  elapsedMs = 0;
  renderHeadSpotlight(currentHeadIndex);
}

/* ---------- Global Refresh & Sync ---------- */
async function refreshAllData(showNotification = true) {
  try {
    state.kpiExcelData = null;
    await fetchSummary();
    await renderSystemsMatrix();
    await renderDepartmentHeadsRotator();

    // Re-render based on active tab so the UI immediately reflects updated Excel data
    if (state.activeTab === 'charts') {
      await renderCharts();
    } else if (state.activeTab === 'departments') {
      await renderDepartmentsTable();
    } else if (state.activeTab === 'risks') {
      await renderRisksTable();
    } else if (state.activeTab === 'kpi') {
      await renderKPITable(true);
    } else {
      await fetchTasks();
    }

    if (showNotification) toast("Ma'lumotlar muvaffaqiyatli yangilandi");
  } catch (err) {
    console.error("Refresh error:", err);
  }
}

/* ---------- KPI Evaluation & Excel Integration ---------- */
async function fetchKPIExcelData(force = false) {
  if (state.kpiExcelData && !force) return state.kpiExcelData;
  try {
    const data = await apiRequest('/kpi/excel-data');
    state.kpiExcelData = data;
    return data;
  } catch (err) {
    console.error("Error fetching KPI Excel data:", err);
    return null;
  }
}

async function renderKPITable(force = false) {
  const data = await fetchKPIExcelData(force);
  if (!data || !data.summary) return;

  const s = data.summary;
  const leaders = data.leaders || [];
  const orgStats = data.org_stats || [];

  const fmtPct = val => {
    if (val === null || val === undefined) return '0%';
    const s = String(val).replace(',', '.');
    return s.endsWith('%') ? s : s + '%';
  };

  const fmtScore = v => {
    if (v === null || v === undefined) return '0%';
    const n = Number(String(v).replace(',', '.'));
    if (isNaN(n)) return String(v);
    return (n % 1 === 0 ? n.toFixed(0) : n.toFixed(2).replace(/\.?0+$/, '')) + '%';
  };

  // Update Summary Metric Cards (2-rasmdagi ko'rsatkichlar)
  if ($('#kpiQ3Score')) $('#kpiQ3Score').textContent = fmtPct(s.q3_bajarilishi);
  if ($('#kpiCumScore')) $('#kpiCumScore').textContent = fmtPct(s.q3_cumulative_9oy);
  if ($('#kpiCumBreakdown')) $('#kpiCumBreakdown').textContent = `I: ${fmtPct(s.q1_bajarilishi)} | II: ${fmtPct(s.q2_bajarilishi)} | III: ${fmtPct(s.q3_bajarilishi)}`;
  if ($('#kpiTotalInd')) $('#kpiTotalInd').textContent = `${s.jami_indikatorlar} ta`;
  if ($('#kpiTotalSub')) $('#kpiTotalSub').textContent = `${s.bajarilgan_indikatorlar || 32} tasi 100%+ bajarilgan`;
  if ($('#kpiIjroGovScore')) $('#kpiIjroGovScore').textContent = fmtPct(s.ijro_intizomi_koeffitsienti);

  // Render Leader Cards (4 ta boshqaruv rahbari)
  const leadersGrid = $('#kpiLeadersGrid');
  if (leadersGrid) {
    const initialsMap = {
      1: "BJ",
      2: "OA",
      3: "AD",
      4: "FE"
    };

    leadersGrid.innerHTML = leaders.map(l => {
      const isActive = state.kpiSelectedLeader === l.id;
      const initials = initialsMap[l.id] || "KPI";
      const qScore = l.quarter_scores ? (l.quarter_scores[state.kpiQuarter] ?? l.average_score) : l.average_score;
      const cumScore = l.quarter_scores ? (l.quarter_scores.cumulative ?? l.average_score) : l.average_score;
      return `
        <div class="kpi-leader-card ${isActive ? 'active' : ''}" data-leader-id="${l.id}">
          <div class="kpi-leader-top">
            <div class="kpi-leader-avatar">${initials}</div>
            <span class="kpi-leader-score">${fmtScore(qScore)}</span>
          </div>
          <div class="kpi-leader-role">${esc(l.role)}</div>
          <div class="kpi-leader-name">${esc(l.fio)}</div>
          <div class="kpi-leader-stats">
            <span>Indikatorlar: <b>${l.indicators.length} ta</b></span>
            <span style="color:#60a5fa">9 oylik: <b>${fmtScore(cumScore)}</b></span>
          </div>
        </div>
      `;
    }).join('');
  }
}


// Manual refresh button: "Ma'lumotlarni yangilash" (Requirements 15, 16, 20, 21)
$('#btnManualRefresh')?.addEventListener('click', async () => {
  const btn = $('#btnManualRefresh');
  if (btn) {
    btn.style.opacity = '0.7';
    btn.classList.add('loading');
  }
  updateSyncBadge('syncing', "Ma'lumotlar yangilanmoqda...");
  try {
    const res = await apiRequest('/data/refresh-all', { method: 'POST' });
    if (res.success) {
      toast("Ma'lumotlar muvaffaqiyatli yangilandi", 'success');
      updateSyncBadge('success', "Ma'lumotlar muvaffaqiyatli yangilandi");
    } else {
      if (res.main_page && !res.main_page.success) {
        toast("1-sahifa Excel ma'lumotlarini o'qishda xatolik yuz berdi", 'error');
        updateSyncBadge('error', "1-sahifa Excel ma'lumotlarini o'qishda xatolik yuz berdi");
      } else if (res.kpi && !res.kpi.success) {
        toast("KPI Excel ma'lumotlarini o'qishda xatolik yuz berdi", 'error');
        updateSyncBadge('error', "KPI Excel ma'lumotlarini o'qishda xatolik yuz berdi");
      }
    }

    if (res.last_updated) {
      state.lastUpdatedTimestamp = res.last_updated;
      const lu = $('#lastUpdatedText');
      if (lu) lu.textContent = `So'nggi yangilanish: ${res.last_updated}`;
    }

    await refreshAllData(false);
    if (state.activeTab === 'kpi') {
      await renderKPITable(true);
    }
    await fetchImportStatus();
  } catch (err) {
    console.error("Refresh error:", err);
    updateSyncBadge('error', "Ma'lumotlarni yangilashda xatolik yuz berdi");
    toast(err.message || "Ma'lumotlarni yangilashda xatolik yuz berdi", 'error');
  } finally {
    if (btn) {
      btn.style.opacity = '1';
      btn.classList.remove('loading');
    }
  }
});

$('#btnSyncData')?.addEventListener('click', () => $('#btnManualRefresh')?.click());
$('#btnRefreshBoard')?.addEventListener('click', () => refreshAllData(true));

// Excel Export
function downloadExcel() {
  const params = new URLSearchParams();
  if (state.token) params.set('token', state.token);
  if (state.filters.boshqarma !== 'all') params.set('boshqarma', state.filters.boshqarma);
  if (state.filters.holat !== 'all') params.set('holat', state.filters.holat);
  if (state.filters.risk !== 'all') params.set('risk', state.filters.risk);

  const url = `${API_BASE}/export/excel?${params.toString()}`;
  window.open(url, '_blank');
  toast("Excel hisoboti yuklab olinmoqda...");
}

$('#btnDownloadExcel')?.addEventListener('click', downloadExcel);
$('#btnExportTop')?.addEventListener('click', downloadExcel);
$('#btnQuickExport')?.addEventListener('click', downloadExcel);

/* ---------- Filters Handler ---------- */
$('#btnToggleFilters')?.addEventListener('click', () => {
  $('#filters')?.classList.toggle('collapsed');
});

$('#fBoshqarma')?.addEventListener('change', e => {
  state.filters.boshqarma = e.target.value;
  state.page = 1;
  updateFilterCount();
  refreshAllData(false);
});

$('#fHolat')?.addEventListener('change', e => {
  state.filters.holat = e.target.value;
  state.page = 1;
  updateFilterCount();
  refreshAllData(false);
});

$('#fRisk')?.addEventListener('change', e => {
  state.filters.risk = e.target.value;
  state.page = 1;
  updateFilterCount();
  refreshAllData(false);
});

$('#fUstuvorlik')?.addEventListener('change', e => {
  state.filters.ustuvorlik = e.target.value;
  state.page = 1;
  updateFilterCount();
  refreshAllData(false);
});

let searchTimeout = null;
$('#fSearch')?.addEventListener('input', e => {
  clearTimeout(searchTimeout);
  searchTimeout = setTimeout(() => {
    state.filters.search = e.target.value;
    state.page = 1;
    updateFilterCount();
    fetchTasks();
  }, 300);
});

$('#btnClearFilters')?.addEventListener('click', () => {
  if ($('#fBoshqarma')) $('#fBoshqarma').value = 'all';
  if ($('#fHolat')) $('#fHolat').value = 'all';
  if ($('#fRisk')) $('#fRisk').value = 'all';
  if ($('#fUstuvorlik')) $('#fUstuvorlik').value = 'all';
  if ($('#fSearch')) $('#fSearch').value = '';
  state.filters = { boshqarma: 'all', holat: 'all', risk: 'all', ustuvorlik: 'all', search: '' };
  state.page = 1;
  updateFilterCount();
  refreshAllData(false);
});

function updateFilterCount() {
  let count = 0;
  if (state.filters.boshqarma !== 'all') count++;
  if (state.filters.holat !== 'all') count++;
  if (state.filters.risk !== 'all') count++;
  if (state.filters.ustuvorlik !== 'all') count++;
  if (state.filters.search) count++;
  const el = $('#filterCount');
  if (el) el.textContent = count;
}

/* ---------- Automatic Polling (Watchdog sync detector) ---------- */
function startLivePolling() {
  // Poll exactly every 3 seconds (Requirement 4)
  setInterval(async () => {
    if (!state.token) return;
    try {
      const params = new URLSearchParams();
      if (state.filters.boshqarma !== 'all') params.set('boshqarma', state.filters.boshqarma);
      const res = await apiRequest(`/dashboard/summary?${params.toString()}`);

      if (res.is_syncing || res.sync_status === 'syncing') {
        updateSyncBadge('syncing', res.sync_message || 'Yangilanmoqda...');
      } else if (res.sync_status === 'error') {
        updateSyncBadge('error', res.sync_message || "Excel ma'lumotlarini yangilashda xatolik");
      } else {
        updateSyncBadge('success', res.sync_message || "Ma'lumotlar yangilandi");
      }

      if (state.lastUpdatedTimestamp && res.songgi_yangilanish && state.lastUpdatedTimestamp !== res.songgi_yangilanish) {
        toast("Excel yangilandi! Ma'lumotlar qayta hisoblandi");
        refreshAllData(false);
      }
      if (res.songgi_yangilanish) {
        state.lastUpdatedTimestamp = res.songgi_yangilanish;
        $('#lastUpdatedText').textContent = `So'nggi yangilanish: ${res.songgi_yangilanish}`;
      }
    } catch (e) {
      // Silent error during background poll
    }
  }, 3000);
}

/* ---------- Initialization ---------- */
async function initDashboard() {
  hydrateIcons();
  switchSection(state.currentSectionIdx, false);
  try {
    await fetchImportStatus();
    await refreshAllData(false);
    startLivePolling();
  } catch (err) {
    console.error("Dashboard init error:", err);
  }
}

window.addEventListener('DOMContentLoaded', () => {
  hydrateIcons();
  moveIndicator();
  initDashboard();
});
