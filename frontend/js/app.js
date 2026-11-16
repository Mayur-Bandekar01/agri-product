/* ================= API LAYER ================= */
let authToken = null;
let currentUser = null;
let paymentIsManual = false;
let initialSetupRequired = false;
let loginInFlight = false;
let notifications = [];
let readNotificationIds = new Set();
let topbarClockTimer = null;
let deferredInstallPrompt = null;
let appIsInstalled = false;
let reportsLoaded = false;
let backgroundDataPromise = null;
const apiCache = new Map();
const apiInflight = new Map();
const API_CACHE_TTL = 5000;

function isStandaloneApp(){
  return window.matchMedia('(display-mode: standalone)').matches || window.navigator.standalone === true;
}

function isIOSSafari(){
  const ua = navigator.userAgent;
  return /iPad|iPhone|iPod/.test(ua) && /Safari/.test(ua) && !/CriOS|FxiOS|EdgiOS|OPiOS/.test(ua) && !window.MSStream;
}

function updateInstallControl(){
  const button = document.getElementById('installAppBtn');
  if (!button) return;
  const shouldShow = !appIsInstalled && !isStandaloneApp() && Boolean(deferredInstallPrompt);
  button.hidden = !shouldShow;
}

async function promptInstall(){
  if (!deferredInstallPrompt) return;
  const prompt = deferredInstallPrompt;
  deferredInstallPrompt = null;
  updateInstallControl();
  try {
    await prompt.prompt();
    const choice = await prompt.userChoice;
    if (choice?.outcome === 'dismissed') {
      try { localStorage.setItem('adinath-install-dismissed', String(Date.now())); } catch (e) { /* storage unavailable */ }
    }
  } catch (error) { /* The browser can close the prompt without a choice. */ }
}

function setupInstallBannerAutoPrompt(){
  const offerBanner = () => {
    document.removeEventListener('click', offerBanner);
    document.removeEventListener('keydown', offerBanner);
    if (!deferredInstallPrompt || appIsInstalled || isStandaloneApp()) return;
    if (sessionStorage.getItem('adinath-install-banner-offered')) return;
    try {
      const dismissedAt = Number(localStorage.getItem('adinath-install-dismissed') || 0);
      if (dismissedAt && Date.now() - dismissedAt < 3 * 24 * 60 * 60 * 1000) return;
    } catch (e) { /* storage unavailable */ }
    sessionStorage.setItem('adinath-install-banner-offered', '1');
    promptInstall();
  };
  document.addEventListener('click', offerBanner);
  document.addEventListener('keydown', offerBanner);
}

function setupPwa(){
  appIsInstalled = isStandaloneApp();
  const installButton = document.getElementById('installAppBtn');
  installButton?.addEventListener('click', promptInstall);
  setupInstallBannerAutoPrompt();
  window.addEventListener('beforeinstallprompt', event => {
    event.preventDefault();
    deferredInstallPrompt = event;
    updateInstallControl();
  });
  window.addEventListener('appinstalled', () => {
    appIsInstalled = true;
    deferredInstallPrompt = null;
    updateInstallControl();
    showToast('Adinath Agri Services has been installed.');
  });
  window.matchMedia('(display-mode: standalone)').addEventListener?.('change', event => {
    appIsInstalled = event.matches;
    updateInstallControl();
  });
  if (isIOSSafari() && !appIsInstalled && !sessionStorage.getItem('adinath-ios-install-hint')) {
    window.setTimeout(() => {
      if (!deferredInstallPrompt && !isStandaloneApp()) {
        sessionStorage.setItem('adinath-ios-install-hint', 'shown');
        showToast('To install: tap Share → Add to Home Screen.', 'success');
      }
    }, 1800);
  }
  if ('serviceWorker' in navigator) {
    window.addEventListener('load', async () => {
      try {
        const registration = await navigator.serviceWorker.register('/service-worker.js', { scope: '/' });
        const offerUpdate = worker => {
          if (!worker || !navigator.serviceWorker.controller) return;
          showToast('New version available — tap to update.', 'success', () => worker.postMessage({ type: 'SKIP_WAITING' }));
        };
        offerUpdate(registration.waiting);
        registration.addEventListener('updatefound', () => registration.installing?.addEventListener('statechange', () => {
          if (registration.installing?.state === 'installed') offerUpdate(registration.waiting);
        }));
        navigator.serviceWorker.addEventListener('controllerchange', () => window.location.reload());
      } catch (error) { console.warn('Service worker registration failed', error); }
    });
  }
}

// Escape API-provided text before inserting it into HTML templates.
function escapeHtml(value){
  return String(value ?? '').replace(/[&<>'"]/g, function(char) {
    const map = {
      '&': '&',
      '<': '<',
      '>': '>',
      '"': '"',
      "'": "'"
    };
    return map[char];
  });
}
function persistAuthToken(token) {
  try {
    localStorage.setItem('adinath-token', token);
  } catch (e) { console.warn('Failed to persist token', e); }
}

function loadPersistedAuth() {
  try {
    const token = localStorage.getItem('adinath-token');
    if (token) {
      authToken = token;
      return true;
    }
  } catch (e) { console.warn('Failed to load persisted token', e); }
  return false;
}

function togglePasswordVisibility(){
  const input = document.getElementById('loginPassword');
  const button = document.getElementById('passwordToggle');
  const showing = input.type === 'text';
  input.type = showing ? 'password' : 'text';
  button.classList.toggle('is-visible', !showing);
  button.setAttribute('aria-label', showing ? 'Show password' : 'Hide password');
  button.setAttribute('aria-pressed', String(!showing));
  button.title = showing ? 'Show password' : 'Hide password';
}

async function resumeSession(){
  if(!loadPersistedAuth()) return;
  try {
    currentUser = await apiFetch('/auth/me');
    applyUserIdentity(currentUser);
    document.getElementById('mainApp').style.display = '';
    document.getElementById('loginScreen').style.display = 'none';
    await bootApp();
  } catch (error) {
    authToken = null;
    try { localStorage.removeItem('adinath-token'); } catch (e) { console.warn('Failed to clear expired session', e); }
  }
}

async function apiFetch(path, opts={}){
  const {timeout = 15000, signal, ...requestOptions} = opts;
  const method = String(requestOptions.method || 'GET').toUpperCase();
  const cacheKey = method === 'GET' ? `${authToken || ''}:${path}` : '';
  if (cacheKey) {
    const cached = apiCache.get(cacheKey);
    if (cached && cached.expiresAt > Date.now()) return cached.value;
    const pending = apiInflight.get(cacheKey);
    if (pending) return pending;
  }
  const controller = new AbortController();
  const timeoutId = window.setTimeout(() => controller.abort(), timeout);
  if(signal) signal.addEventListener('abort', () => controller.abort(), {once:true});
  const headers = Object.assign({}, requestOptions.headers, authToken ? {Authorization: 'Bearer '+authToken} : {});
  if(requestOptions.body && !(requestOptions.body instanceof URLSearchParams)){
    headers['Content-Type'] = 'application/json';
    requestOptions.body = JSON.stringify(requestOptions.body);
  }
  const request = (async () => {
    let res;
    try { res = await fetch(path, Object.assign({}, requestOptions, {headers, signal:controller.signal})); }
    catch(error) {
      if(controller.signal.aborted) throw new Error('The request took too long. Please check the local service and try again.');
      throw error;
    } finally { window.clearTimeout(timeoutId); }
    if(!res.ok){
      // Read body ONCE as text, then parse for error detail
      const text = await res.text();
      const detail = text ? (() => { try { const j = JSON.parse(text); return j.detail || j; } catch(e) { return text; } })() : res.statusText;
      throw new Error(detail);
    }
    // Read body ONCE as text, parse JSON once for value
    const text = await res.text();
    const value = res.status===204 ? null : JSON.parse(text);
    if (cacheKey) apiCache.set(cacheKey, {value, expiresAt: Date.now() + API_CACHE_TTL});
    return value;
  })();
  if (cacheKey) apiInflight.set(cacheKey, request);
  try { return await request; }
  finally {
    if (cacheKey) apiInflight.delete(cacheKey);
    if (method !== 'GET') apiCache.clear();
  }
}

async function fetchWithTimeout(url, options={}, timeout=30000){
  const controller = new AbortController();
  const timer = window.setTimeout(() => controller.abort(), timeout);
  try {
    return await fetch(url, {...options, signal: controller.signal});
  } catch (error) {
    if (controller.signal.aborted) throw new Error('The export took too long. Please try again.');
    throw error;
  } finally {
    window.clearTimeout(timer);
  }
}

// ================= MODAL MANAGEMENT =================

/**
 * Open the entity modal (used for both farmer and product forms)
 * @param {string} modalId - The modal overlay element ID ('entityModal' or 'farmerModal')
 * @param {string} title - The modal title text
 * @param {Function} formBuilder - Function that returns HTML form markup
 * @param {Object} formData - Optional pre-populated farmer/product data
 */
function openModal(modalId, title, formBuilder, formData = null) {
  const modalOverlay = document.getElementById(modalId);
  const modalTitle = document.getElementById('entityModalTitle');
  const entityForm = document.getElementById('entityForm');

  if (!modalOverlay || !modalTitle || !entityForm) {
    console.error(`Modal elements not found for ID: ${modalId}`);
    return;
  }

  // Determine if this is a farmer form based on title or formBuilder name
  const formBuilderName = formBuilder.name || '';
  const isFarmerForm = title.toLowerCase().includes('customer') || formBuilderName.includes('Farmer');
  const farmerId = formData ? formData.id : null;

  // Set title
  modalTitle.textContent = title;

  // Build and insert form HTML
  entityForm.innerHTML = formBuilder(formData);

  // Reset form error state
  const formError = document.getElementById('entityFormError');
  if (formError) formError.textContent = '';

  // Get the submit button and reset it
  const submitBtn = entityForm.querySelector('[type="submit"]');
  if (submitBtn) {
    submitBtn.disabled = false;
    submitBtn.textContent = formData ? 'Save Changes' : (isFarmerForm ? 'Create Customer' : 'Create Product');
  }

  // Set up form submit handler
  const form = entityForm;
  form.onsubmit = async function(event) {
    event.preventDefault();

    // Show loading state
    const submit = form.querySelector('[type="submit"]');
    if (submit) {
      submit.disabled = true;
      submit.textContent = formData ? 'Saving...' : (isFarmerForm ? 'Creating...' : 'Creating...');
    }
    const formError = document.getElementById('entityFormError');
    if (formError) formError.textContent = '';

    // Build payload from form data
    const payload = Object.fromEntries(new FormData(form).entries());

    try {
      // Determine API endpoint based on form type
      const endpoint = isFarmerForm ? (farmerId ? `/farmers/${farmerId}` : '/farmers') : (farmerId ? `/products/${farmerId}` : '/products');

      // Submit via API
      const result = await apiFetch(endpoint, {
        method: farmerId ? 'PUT' : 'POST',
        body: payload
      });

      // Show success toast
      const action = isFarmerForm ? 'customer' : 'product';
      showToast(`${action.charAt(0).toUpperCase() + action.slice(1)} ${formData ? 'updated' : 'created'}`);

      // Close modal
      closeModal(modalId);

      // Reload data
      if (isFarmerForm) {
        await loadFarmers();
        renderFarmers();
      } else {
        await loadProducts();
        renderProducts();
      }
      // Reset form fields
      if (form.reset) form.reset();

    } catch (err) {
      // Display error message - keep modal open so user can correct inputs
      const formError = document.getElementById('entityFormError');
      if (formError) {
        formError.textContent = err.message || 'Could not save entry. Please try again.';
      }
      showToast(err.message || 'Operation failed', 'critical');
      console.error(`${modalId} submit error:`, err);
    } finally {
      // Re-enable submit button
      const submit = form.querySelector('[type="submit"]');
      if (submit) {
        submit.disabled = false;
        submit.textContent = formData ? 'Save Changes' : (isFarmerForm ? 'Create Customer' : 'Create Product');
      }
    }
  };

  // Show modal
  modalOverlay.classList.add('open');

  // Focus the first input field after a brief timeout
  setTimeout(() => {
    const firstInput = entityForm.querySelector('input[type="text"], input[type="number"], input[type="search"]');
    if (firstInput) {
      firstInput.focus();
      if (firstInput.select) firstInput.select();
    }
  }, 50);
}

/**
 * Close a specific modal by ID
 * @param {string} modalId - The modal overlay element ID
 */
function closeModal(modalId) {
  const overlay = document.getElementById(modalId);
  if (overlay) {
    overlay.classList.remove('open');
  }
}

/* ================= FARMER FORM ================= */

/**
 * Open the Add/Edit Customer form
 * @param {number|null} farmerId - Optional farmer ID for editing existing customer
 */
function openFarmerForm(farmerId = null) {
  const isEdit = farmerId !== null;
  const farmer = farmers.find(item => item.id === farmerId);

  // Open the entity modal with farmer form builder
  openModal(
    'entityModal',
    isEdit ? 'Edit Customer' : 'New Customer',
    buildFarmerForm,
    farmer
  );
}

/* ================= PRODUCT FORM ================= */

/**
 * Open the Add/Edit Product form
 * @param {number|null} productId - Optional product ID for editing existing product
 */
function openProductForm(productId = null) {
  const product = products.find(item => item.id === productId);
  const isEdit = product !== null;

  openModal(
    'entityModal',
    isEdit ? 'Edit Product' : 'New Product',
    buildProductForm,
    product
  );
}

/* ================= FORM SUBMISSION ================= */

/**
 * Handle farmer form submission
 * @param {Event} event - The form submit event
 * @param {number|null} farmerId - Optional farmer ID for editing
 */
async function saveFarmer(event, farmerId) {
  event.preventDefault();

  const form = event.currentTarget;
  const error = document.getElementById('entityFormError');
  const submit = form.querySelector('[type="submit"]');

  if (!submit) return;

  // Show loading state
  submit.disabled = true;
  submit.textContent = farmerId ? 'Updating...' : 'Saving...';
  const formError = document.getElementById('entityFormError');
  if (formError) formError.textContent = '';

  // Build payload from form data
  const payload = Object.fromEntries(new FormData(form).entries());

  try {
    // Submit via API
    const endpoint = farmerId ? `/farmers/${farmerId}` : '/farmers';
    const result = await apiFetch(endpoint, {
      method: farmerId ? 'PUT' : 'POST',
      body: payload
    });

    // Show success - result contains the newly created/updated farmer
    showToast(farmerId ? 'Customer updated' : 'Customer created');

    // Close modal
    closeModal('entityModal');

    // Reload farmers data from API
    await loadFarmers();
    renderFarmers();

    // Reset form fields
    if (form.reset) form.reset();

  } catch (err) {
    // Display error message - keep modal open so user can correct inputs
    const formError = document.getElementById('entityFormError');
    if (formError) {
      formError.textContent = err.message || 'Could not save customer. Please check inputs and try again.';
    }
    showToast(err.message || 'Failed to save customer. Please try again.', 'critical');
    // Do NOT close modal - let user fix errors
  } finally {
    // Re-enable submit button
    submit.disabled = false;
    submit.textContent = farmerId ? 'Save Changes' : 'Create Customer';
  }
}

/* ================= DATA (always loaded from the API; no client-side records) ================= */
let products = [];
let farmers = [];
let transactions = [];
let recentTransactions = [];
let outstandingRows = [];
let topProducts = [];
let salesChartData = [];
let activeSalesRange = '7d';

/* ================= LOADERS (map backend JSON -> frontend shapes) ============== */

async function loadProducts(){
  const response = await apiFetch('/products');
  if(!Array.isArray(response)) throw new Error('The products service returned an invalid response');
  products = response.map(mapProduct);
}

function mapProduct(p){
  return {
    id:p.id, name:escapeHtml(p.name), nameRaw:p.name, sku:escapeHtml(p.sku), skuRaw:p.sku,
    category:escapeHtml(p.category||''), categoryRaw:p.category||'',
    unit:escapeHtml(p.unit||''), unitRaw:p.unit||'',
    price:p.price, purchasePrice:p.purchase_price_including_gst, gstRate:p.gst_rate,
    stock:p.stock, min_stock:p.min_stock, status:p.status || 'In Stock',
    expiresOn:p.expires_on, supplier:escapeHtml(p.supplier||''),
    sellTaxMode: p.selling_price_tax_mode || 'inclusive'
  };
}

async function loadFarmers(){
  try{
    const list = await apiFetch('/farmers');
    farmers = list.map(f=>({
      id:f.id, name:escapeHtml(f.name), nameRaw:f.name, mobile:escapeHtml(f.mobile), mobileRaw:f.mobile,
      location:escapeHtml(f.location||''), locationRaw:f.location||'',
      totalPurchases:f.total_purchases, outstanding:f.outstanding,
      lastPurchase:f.last_purchase ? new Date(f.last_purchase).toLocaleDateString('en-IN',{day:'2-digit',month:'short',year:'numeric'}) : String.fromCharCode(8212)
    }));
  }catch(e){ console.warn('loadFarmers failed', e); }
}

function farmerNameById(id){ const f = farmers.find(x=>x.id===id); return f ? f.name : 'Walk-in Customer'; }

async function loadDashboard(range = activeSalesRange){
  const summaryRequest = apiFetch('/dashboard/summary');
  const recentRequest = apiFetch('/dashboard/recent-transactions?limit=6');
  const chartRequest = apiFetch('/dashboard/sales-chart?range='+encodeURIComponent(range));
  try{
    const s = await summaryRequest;
    document.getElementById('mTodaysSales').textContent = money(s.todays_sales);
    document.getElementById('mBillsToday').textContent = s.bills_today;
    document.getElementById('mOutstanding').textContent = money(s.outstanding_total);
    document.getElementById('mLowStock').textContent = s.low_stock_count + ' Items';
  }catch(e){ console.warn('loadDashboard summary failed', e); }
  try{
    const txns = await recentRequest;
    recentTransactions = txns.map(mapInvoice);
  }catch(e){ console.warn('loadDashboard transactions failed', e); }
  try{
    const chart = await chartRequest;
    salesChartData = chart.map(pt=>({label: new Date(pt.label).toLocaleDateString('en-IN',{weekday:'short'}), val: pt.total}));
    if(!salesChartData.some(d=>d.val>0)){ /* keep zeros — chart will just render flat */ }
  }catch(e){ console.warn('loadDashboard chart failed', e); }
}

function mapInvoice(invoice){
  return {id:invoice.id, inv:escapeHtml(invoice.invoice_no), farmer:escapeHtml(invoice.farmer_name || 'Walk-in Customer'), items:'—', amount:invoice.grand_total, method:String(invoice.payment_method).toUpperCase(), status:invoice.status};
}

async function loadInvoices(){
  try { transactions = (await apiFetch('/invoices')).map(mapInvoice); }
  catch(e) { console.warn('loadInvoices failed', e); }
}

async function loadOutstanding(){
  const summaryRequest = apiFetch('/outstanding/summary');
  const rowsRequest = apiFetch('/outstanding');
  try{
    const s = await summaryRequest;
    document.getElementById('oTotalOutstanding').textContent = money(s.total_outstanding);
    document.getElementById('oDueToday').textContent = money(s.due_today);
    document.getElementById('oOverdue').textContent = money(s.overdue);
    document.getElementById('oCustomersWithDues').textContent = s.customers_with_dues;
  }catch(e){ console.warn('loadOutstanding summary failed', e); }
  try{
    const rows = await rowsRequest;
    outstandingRows = rows.map(r=>({
      id: r.id, farmer: r.farmer_name || 'Walk-in Customer', inv: r.invoice_no,
      date: new Date(r.date).toLocaleDateString('en-IN',{day:'2-digit',month:'short',year:'numeric'}),
      total: r.grand_total, paid: r.amount_paid, balance: r.balance_due,
      status: r.status
    })).map(r=>({...r, farmer:escapeHtml(r.farmer), inv:escapeHtml(r.inv)}));
  }catch(e){ console.warn('loadOutstanding rows failed', e); }
}

function loadReadNotifications(){
  try { readNotificationIds = new Set(JSON.parse(localStorage.getItem('adinath-read-notifications') || '[]')); }
  catch(e) { readNotificationIds = new Set(); }
}
function persistReadNotifications(){ localStorage.setItem('adinath-read-notifications', JSON.stringify([...readNotificationIds])); }
async function loadNotifications(){
  try { notifications = await apiFetch('/notifications'); renderNotifications(); }
  catch(e) { console.warn('loadNotifications failed', e); }
}
function notificationIcon(type){ return ({low_stock:'▣', expiry:'◷', payment:'₹', sale:'↗', system:'•'})[type] || '•'; }
function renderNotifications(){
  const unread = notifications.filter(item => !readNotificationIds.has(item.id));
  const badge = document.getElementById('notificationBadge');
  badge.hidden = unread.length === 0;
  const count = document.getElementById('notificationCount');
  count.textContent = unread.length ? `${unread.length} new notification${unread.length === 1 ? '' : 's'}` : "You're all caught up";
  document.getElementById('notificationList').innerHTML = notifications.length ? notifications.map(item => `
    <button class="notification-item ${escapeHtml(item.severity)} ${readNotificationIds.has(item.id) ? 'is-read' : ''}" type="button" onclick="openNotification('${escapeHtml(item.id)}')">
      <span class="notification-icon">${notificationIcon(item.type)}</span><span class="notification-copy"><strong>${escapeHtml(item.title)}</strong><span>${escapeHtml(item.message)}</span><time>${new Date(item.created_at).toLocaleString('en-IN',{day:'numeric',month:'short',hour:'2-digit',minute:'2-digit'})}</time></span>
      ${readNotificationIds.has(item.id) ? '' : '<i class="notification-unread" aria-label="Unread"></i>'}
    </button>`).join('') : '<div class="notification-empty">No notifications right now.</div>';
}
function toggleNotifications(){
  const center = document.getElementById('notificationCenter');
  const opening = center.hidden;
  center.hidden = !opening;
  document.getElementById('notificationTrigger').setAttribute('aria-expanded', String(opening));
  if(opening) loadNotifications();
}
function closeNotifications(restoreFocus=false){
  const center = document.getElementById('notificationCenter');
  if(!center || center.hidden) return;
  center.hidden = true;
  document.getElementById('notificationTrigger').setAttribute('aria-expanded', 'false');
  if(restoreFocus) document.getElementById('notificationTrigger').focus();
}
document.addEventListener('pointerdown', event=>{
  const wrap = document.querySelector('.notification-wrap');
  const center = document.getElementById('notificationCenter');
  if(center && !center.hidden && wrap && !wrap.contains(event.target)) closeNotifications();
});
document.addEventListener('keydown', event=>{
  if(event.key === 'Escape') closeNotifications(true);
});
function openNotification(id){
  const notification = notifications.find(item => item.id === id);
  if(!notification) return;
  readNotificationIds.add(id); persistReadNotifications(); renderNotifications();
  closeNotifications();
  if(notification.action_view) goTo(notification.action_view);
}
function markAllNotificationsRead(){
  notifications.forEach(item => readNotificationIds.add(item.id)); persistReadNotifications(); renderNotifications();
}
function announcePriorityNotification(){
  const urgent = notifications.find(item => !readNotificationIds.has(item.id) && (item.severity === 'critical' || item.severity === 'warning'));
  if(!urgent || sessionStorage.getItem(`adinath-announced-${urgent.id}`)) return;
  sessionStorage.setItem(`adinath-announced-${urgent.id}`, '1');
  showToast(`${urgent.title} — open details`, urgent.severity, () => openNotification(urgent.id));
}

/* ================= NAVIGATION ================= */
const titles = {dashboard:"Dashboard", billing:"Billing", products:"Products", inventory:"Inventory", farmers:"Farmers", sales:"Sales", purchases:"Purchases", outstanding:"Outstanding Payments", reports:"Settings"};
let viewHistory = ['dashboard'];

function updateBackButton(){
  const button = document.getElementById('appBackBtn');
  button.disabled = viewHistory.length < 2;
  button.title = button.disabled ? 'No previous section' : `Back to ${titles[viewHistory[viewHistory.length - 2]]}`;
}

function goTo(view, recordHistory = true){
  if(view === 'reports') {
    buildReportsDashboard();
    if (reportsLoaded && selectedReport) {
      renderSelectedReport(selectedReport);
      document.getElementById('reportContent').hidden = false;
      document.getElementById('reportLoading').hidden = true;
    } else {
      loadReports().catch(error => console.warn('Deferred report load failed', error));
    }
  }
  const currentView = viewHistory[viewHistory.length - 1];
  if(recordHistory && view !== currentView) viewHistory.push(view);
  document.querySelectorAll('.view').forEach(v=>v.classList.remove('active'));
  document.getElementById('view-'+view).classList.add('active');
  document.querySelectorAll('.nav-item').forEach(n=>n.classList.toggle('active', n.dataset.view===view));
  document.getElementById('pageTitle').textContent = titles[view];
  document.getElementById('mainApp').classList.remove('sidebar-open');
  document.body.classList.remove('nav-open');
  if(view === 'dashboard') playDashboardEntrance();
  updateBackButton();
  document.querySelector('.content').scrollTo({top:0, behavior: window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth'});
}
function goBack(){
  if(viewHistory.length < 2) return;
  viewHistory.pop();
  goTo(viewHistory[viewHistory.length - 1], false);
}
updateBackButton();
document.querySelectorAll('.nav-item, .mobile-nav-item').forEach(item=>{
  item.addEventListener('click', ()=> goTo(item.dataset.view));
});

/* ================= DASHBOARD RENDER ================= */
function renderDashboard(){
  const maxVal = Math.max(...salesChartData.map(d=>d.val), 1);
  document.getElementById('salesChart').innerHTML = salesChartData.length ? salesChartData.map(d=>`
    <div class="chart-bar-col">
      <div class="chart-bar" style="height:${(d.val/maxVal*100)}%" tabindex="0" aria-label="${d.label}: ${money(d.val)}"><span class="chart-bar-value">${money(d.val)}</span></div>
      <div class="chart-bar-label">${d.label}</div>
    </div>`).join('') : '<div class="empty-state"><h3>No sales data yet</h3><p>Sales will appear after you create invoices.</p></div>';

  const low = products.filter(p=>p.status!=='In Stock').slice(0,5);
  document.getElementById('stockAlertList').innerHTML = low.length ? low.map(p=>`
    <div class="alert-row">
      <div class="alert-dot" style="background:${p.status==='Out of Stock' ? 'var(--danger)':'var(--earth)'}"></div>
      <div><div class="alert-name">${p.name}</div><div class="alert-sub">${p.category} · ${p.sku}</div></div>
      <div class="alert-qty">${p.stock} left</div>
    </div>`).join('') : '<div class="empty-state"><h3>No stock alerts</h3><p>Products with low stock will appear here.</p></div>';

  document.getElementById('recentTxnTable').innerHTML = `
    <thead><tr><th>Invoice</th><th>Farmer</th><th>Products</th><th>Amount</th><th>Payment</th><th>Status</th></tr></thead>
    <tbody>${recentTransactions.length ? recentTransactions.map(t=>`
      <tr><td class="cell-strong">${t.inv}</td><td>${t.farmer}</td><td class="cell-muted">${t.items}</td>
      <td class="cell-num">${money(t.amount)}</td><td>${t.method}</td><td>${statusBadge(t.status)}</td></tr>`).join('') : '<tr><td colspan="6" class="cell-muted">No invoices yet. Create an invoice to see transactions here.</td></tr>'}
    </tbody>`;
}

/* ================= HELPERS ================= */
function statusBadge(status){
  const map = {
    paid:['badge-paid','Paid'], partial:['badge-partial','Partial'], credit:['badge-credit','Credit'],
    'In Stock':['badge-in','In Stock'], 'Low Stock':['badge-low','Low Stock'], 'Out of Stock':['badge-out','Out of Stock'],
    Normal:['badge-in','Normal'], 'Expiring Soon':['badge-partial','Expiring Soon'], Expired:['badge-out','Expired'],
    overdue:['badge-credit','Overdue'], 'due-today':['badge-partial','Due Today']
  };
  const m = map[status] || ['badge-in', status];
  return `<span class="badge ${m[0]}">${m[1]}</span>`;
}

/* ================= MONEY FORMATTER ================= */
function money(val){
  const n = Number(val) || 0;
  return n.toLocaleString('en-IN', {style:'currency', currency:'INR', minimumFractionDigits:0, maximumFractionDigits:0});
}

/* ================= LOGIN HANDLING ================= */

async function handleLogin(){
  const btn = document.getElementById('loginBtn');
  const errEl = document.getElementById('loginError');
  const username = document.getElementById('loginUsername').value.trim();
  const password = document.getElementById('loginPassword').value;
  const remember = document.getElementById('rememberSession').checked;

  if(!username || !password){
    errEl.textContent = 'Please enter username and password.';
    return;
  }

  btn.disabled = true;
  btn.querySelector('span').textContent = 'Signing in...';
  errEl.textContent = '';

  try {
    const res = await apiFetch('/auth/login', {
      method: 'POST',
      body: {username, password}
    });

    authToken = res.access_token;
    if (remember) {
      persistAuthToken(authToken);
    } else {
      try { localStorage.removeItem('adinath-token'); } catch(e) {}
    }

    currentUser = await apiFetch('/auth/me');
    applyUserIdentity(currentUser);
    document.getElementById('mainApp').style.display = '';
    document.getElementById('loginScreen').style.display = 'none';
    document.getElementById('loginPassword').value = '';
    await bootApp();
  } catch (e) {
    errEl.textContent = e.message || 'Login failed. Please check your credentials.';
  } finally {
    btn.disabled = false;
    btn.querySelector('span').textContent = 'Log In';
  }
}

function applyUserIdentity(user){
  if(!user) return;
  const nameEl = document.getElementById('currentUserName');
  const roleEl = document.getElementById('currentUserRole');
  if(nameEl) nameEl.textContent = user.name || user.username;
  if(roleEl) roleEl.textContent = user.role || 'User';
}

async function bootApp(){
  // Load initial data for dashboard
  await Promise.all([
    loadProducts(),
    loadFarmers(),
    loadDashboard(),
    loadNotifications()
  ]);

  renderDashboard();
  renderFarmers();
  renderProducts();
  renderInvoices();
  renderOutstanding();
  announcePriorityNotification();

  // Start topbar clock
  startTopbarClock();
}

function startTopbarClock(){
  const clockEl = document.getElementById('topbarClock');
  if(!clockEl) return;
  const update = () => {
    clockEl.textContent = new Date().toLocaleTimeString('en-IN', {hour:'2-digit', minute:'2-digit', second:'2-digit'});
  };
  update();
  if(topbarClockTimer) clearInterval(topbarClockTimer);
  topbarClockTimer = setInterval(update, 1000);
}

/* ================= RENDERERS ================= */

function renderFarmers(){
  const container = document.getElementById('farmerList');
  if(!container) return;
  container.innerHTML = farmers.length ? farmers.map(f=> `
    <tr>
      <td class="cell-strong">${f.name}</td>
      <td>${f.mobile}</td>
      <td class="cell-muted">${f.location || '-'}</td>
      <td class="cell-num">${money(f.totalPurchases || 0)}</td>
      <td class="cell-num ${f.outstanding ? 'text-danger' : ''}">${money(f.outstanding || 0)}</td>
      <td class="cell-num">${f.lastPurchase || '-'}</td>
    </tr>
  `).join('') : '<tr><td colspan="6" class="cell-muted">No customers yet. Click "New Customer" to add.</td></tr>';
}

function renderProducts(){
  const container = document.getElementById('productList');
  if(!container) return;
  container.innerHTML = products.length ? products.map(p=> `
    <tr>
      <td class="cell-strong">${p.name}</td>
      <td class="cell-muted">${p.category} · ${p.sku}</td>
      <td class="cell-num">${p.stock} / ${p.min_stock}</td>
      <td class="cell-num">${money(p.price || 0)}</td>
    </tr>
  `).join('') : '<tr><td colspan="4" class="cell-muted">No products yet. Add products to get started.</td></tr>';
}

function renderInvoices(){
  const container = document.getElementById('invoiceList');
  if(!container) return;
  container.innerHTML = transactions.length ? transactions.map(t=> `
    <tr>
      <td class="cell-strong">${t.inv}</td>
      <td class="cell-muted">${t.farmer}</td>
      <td class="cell-num">${money(t.amount)}</td>
      <td class="cell-num">${t.method}</td>
      <td>${statusBadge(t.status)}</td>
    </tr>
  `).join('') : '<tr><td colspan="5" class="cell-muted">No invoices yet.</td></tr>';
}

function renderOutstanding(){
  const container = document.getElementById('outstandingTable');
  if(!container) return;
  container.innerHTML = outstandingRows.length ? outstandingRows.map(r=> `
    <tr>
      <td class="cell-strong">${r.farmer}</td>
      <td class="cell-muted">${r.inv}</td>
      <td class="cell-num">${money(r.total)}</td>
      <td class="cell-num">${money(r.paid)}</td>
      <td class="cell-num text-danger">${money(r.balance)}</td>
      <td>${statusBadge(r.status)}</td>
    </tr>
  `).join('') : '<tr><td colspan="6" class="cell-muted">No outstanding records.</td></tr>';
}

/* ================= TOAST/NOTIFICATION ================= */
let toastTimer = null;

function showToast(message, severity = 'success', onClick){
  // Try to use a toast container if it exists
  const toastContainer = document.getElementById('toastContainer');
  if(toastContainer){
    const toast = document.createElement('div');
    toast.className = `toast toast-${severity}`;
    toast.innerHTML = `<span>${escapeHtml(message)}</span>`;
    if(typeof onClick === 'function'){
      toast.addEventListener('click', onClick);
      toast.style.cursor = 'pointer';
    }
    toastContainer.appendChild(toast);
    setTimeout(() => {
      toast.remove();
    }, 4000);
    return;
  }

  // Fallback to alert for basic notification
  if(severity === 'critical'){
    alert(message);
  }
}

/* ================= REPORTS ================= */
let selectedReport = null;

async function loadReports(){
  try {
    const list = await apiFetch('/reports');
    reportsLoaded = true;
    document.getElementById('reportList').innerHTML = list.map(r=> `
      <button class="report-item" type="button" onclick="selectReport('${r.id}')">
        <span class="report-title">${escapeHtml(r.title)}</span>
        <span class="report-type">${r.type}</span>
      </button>
    `).join('') || '<div class="empty-state">No reports available.</div>';
  } catch(e){ console.warn('loadReports failed', e); }
}

function selectReport(id){
  const report = /* fetch from list */ null;
  selectedReport = {id, title: 'Report', type: 'sales'};
  buildReportsDashboard();
  renderSelectedReport(selectedReport);
}

function buildReportsDashboard(){
  // Create the dashboard UI for reports
  document.getElementById('reportTabs').innerHTML = `
    <button class="report-tab active" data-tab="sales">Sales</button>
    <button class="report-tab" data-tab="inventory">Inventory</button>
    <button class="report-tab" data-tab="customers">Customers</button>
  `;
  document.querySelectorAll('.report-tab').forEach(tab=> {
    tab.addEventListener('click', e=> {
      document.querySelectorAll('.report-tab').forEach(t=> t.classList.remove('active'));
      tab.classList.add('active');
    });
  });
}

function renderSelectedReport(report){
  document.getElementById('reportContent').hidden = false;
  document.getElementById('reportLoading').hidden = true;
  document.getElementById('selectedReportTitle').textContent = report.title;
  document.getElementById('reportContent').innerHTML = `
    <div class="report-generator">
      <button class="btn btn-primary" onclick="generateReport('${report.id}')">Generate Report</button>
      <button class="btn btn-secondary" onclick="downloadReport('${report.id}')">Download</button>
    </div>
  `;
}

async function generateReport(reportId){
  try {
    const blob = await apiFetch('/reports/' + reportId + '/generate');
    showToast('Report generated successfully', 'success');
  } catch(e){
    showToast('Failed to generate report: ' + (e.message || 'Unknown error'), 'critical');
  }
}

async function downloadReport(reportId){
  try {
    const blob = await apiFetch('/reports/' + reportId + '/download');
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = reportId + '.xlsx';
    document.body.appendChild(a);
    a.click();
    URL.revokeObjectURL(url);
    document.body.removeChild(a);
    showToast('Report downloaded', 'success');
  } catch(e){
    showToast('Download failed: ' + (e.message || 'Unknown error'), 'critical');
  }
}