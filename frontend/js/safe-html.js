/**
 * Safe HTML Builder - Prevents XSS vulnerabilities
 * Use this instead of template literals for dynamic HTML
 */

// Re-export escapeHtml from security.js if available, otherwise define it
if (typeof window.escapeHtml === 'undefined') {
  window.escapeHtml = function(value) {
    if (value == null) return '';
    return String(value).replace(/[&<>"']/g, function(char) {
      const entities = {
        '&': '&',
        '<': '<',
        '>': '>',
        '"': '"',
        "'": "'"
      };
      return entities[char];
    });
  };
}
// escapeHtml is already available globally from security.js (loaded first)
// No local declaration needed - it's already available on window.escapeHtml

/**
 * Safely create an input field with escaped value
 */
function safeInput(attrs) {
  const {name, type = 'text', value = '', placeholder = '', required = false, id, ...rest} = attrs;
  const req = required ? ' required' : '';
  const plc = placeholder ? ` placeholder="${escapeHtml(placeholder)}"` : '';
  const val = value ? ` value="${escapeHtml(value)}"` : '';

  let extra = '';
  for (const [key, v] of Object.entries(rest)) {
    if (typeof v === 'boolean') {
      extra += v ? ` ${key}` : '';
    } else {
      extra += ` ${key}="${escapeHtml(v)}"`;
    }
  }

  const idAttr = id ? ` id="${escapeHtml(id)}"` : '';

  return `<input name="${escapeHtml(name)}" type="${type}"${val}${plc}${req}${idAttr}${extra}>`;
}

/**
 * Safely create a select dropdown with options
 */
function safeSelect(attrs, options) {
  const {name, value = '', required = false} = attrs;
  const req = required ? ' required' : '';

  const optionsHtml = options.map(opt => {
    const val = typeof opt === 'string' ? opt : opt.value;
    const label = typeof opt === 'string' ? opt : opt.label;
    const selected = val === value ? ' selected' : '';
    return `<option value="${escapeHtml(val)}"${selected}>${escapeHtml(label)}</option>`;
  }).join('');

  return `<select name="${escapeHtml(name)}"${req}>${optionsHtml}</select>`;
}

/**
 * Safely create a label with input
 */
function safeLabel(labelText, inputHtml, attrs = {}) {
  const {hidden = false, id = ''} = attrs;
  const style = hidden ? ' style="display:none;"' : '';
  const idAttr = id ? ` id="${escapeHtml(id)}"` : '';
  return `<label${style}${idAttr}>${escapeHtml(labelText)}${inputHtml}</label>`;
}

/**
 * Safe farmer form builder
 * @param {Object|null} farmer - Farmer object with nameRaw, mobileRaw, locationRaw properties, or null for a new customer
 * @returns {string} HTML form markup
 */
function buildFarmerForm(farmer = null) {
  const isEdit = Boolean(farmer);
  return `
    ${safeLabel('Name', safeInput({name: 'name', required: true, minlength: 2, maxlength: 120, value: farmer?.nameRaw || '', id: 'name'}))}
    ${safeLabel('Mobile', safeInput({name: 'mobile', required: true, minlength: 6, maxlength: 30, value: farmer?.mobileRaw || ''}))}
    ${safeLabel('Location', safeInput({name: 'location', maxlength: 160, value: farmer?.locationRaw || ''}))}
    <div class="form-error" id="entityFormError" role="alert"></div>
    <div class="form-actions">
      <button class="btn btn-secondary" type="button" onclick="closeModal('entityModal')">Cancel</button>
      <button class="btn btn-primary" type="submit">${isEdit ? 'Save Changes' : 'Create Customer'}</button>
    </div>
  `;
}

/**
 * Safe product form builder
 */
function buildProductForm(product = null) {
  const standardGstRates = [0, 5, 12, 18, 28];
  const hasCustomGst = product?.gstSelectionType === 'custom' ||
    (product?.gstRate != null && !standardGstRates.includes(Number(product.gstRate)));

  const gstOptions = standardGstRates.map(rate => ({
    value: String(rate),
    label: `${rate}%`
  }));
  gstOptions.unshift({value: '', label: 'Select GST'});
  gstOptions.push({value: 'custom', label: 'Custom GST'});

  const selectedGst = hasCustomGst ? 'custom' : (product?.gstRate != null ? String(product.gstRate) : '');

  return `
    ${safeLabel('Name', safeInput({name: 'name', required: true, maxlength: 160, value: product?.nameRaw || ''}))}
    ${safeLabel('SKU', safeInput({name: 'sku', required: true, maxlength: 80, value: product?.skuRaw || ''}))}
    ${safeLabel('Product Type', safeSelect(
      {name: 'category', required: true},
      [
        {value: 'Fertilizer', label: 'Fertilizer'},
        {value: 'Pesticides', label: 'Pesticides'}
      ]
    ).replace('value="Fertilizer"', `value="Fertilizer"${product?.categoryRaw === 'Fertilizer' || !product ? ' selected' : ''}`)
     .replace('value="Pesticides"', `value="Pesticides"${product?.categoryRaw === 'Pesticides' ? ' selected' : ''}`))}
    ${safeLabel('Unit', safeInput({name: 'unit', required: true, maxlength: 40, value: product?.unitRaw || ''}))}
    ${safeLabel('Purchase price (incl. GST)', safeInput({name: 'purchase_price_including_gst', type: 'number', min: 0, step: 0.01, value: product?.purchasePrice || ''}))}
    ${safeLabel('Selling price', safeInput({name: 'selling_price', type: 'number', min: 0, step: 0.01, value: product?.price || '', placeholder: 'Not Verified'}))}
    ${safeLabel('GST rate (%)', safeSelect(
      {name: 'gst_rate'},
      gstOptions
    ).replace(`value="${selectedGst}"`, `value="${selectedGst}" selected`).replace('name="gst_rate"', 'name="gst_rate" id="productGstRate"'))}
    ${safeLabel('Custom GST (%)', safeInput({
      name: 'custom_gst_rate',
      id: 'customGstRate',
      type: 'number',
      min: 0,
      max: 100,
      step: 0.01,
      value: hasCustomGst ? product.gstRate : '',
      required: hasCustomGst
    }), {hidden: !hasCustomGst, id: 'customGstRateLabel'})}
    ${safeLabel('Selling price tax mode', `<select name="selling_price_tax_mode">
      <option value="inclusive"${product?.sellingPriceTaxMode === 'inclusive' ? ' selected' : ''}>Tax inclusive</option>
      <option value="exclusive"${!product || product.sellingPriceTaxMode !== 'inclusive' ? ' selected' : ''}>Tax exclusive</option>
    </select>`)}
    ${safeLabel('Pack size', safeInput({name: 'pack_size', maxlength: 80, value: product?.packSize || ''}))}
    ${safeLabel('Current stock', safeInput({name: 'stock', type: 'number', min: 0, step: 0.01, required: true, value: product?.stock || 0}))}
    ${safeLabel('Low-stock threshold', safeInput({name: 'min_stock', type: 'number', min: 0, step: 0.01, required: true, value: product?.min_stock || 10}))}
    ${safeLabel('Expiry date <small>(optional)</small>', safeInput({name: 'expires_on', type: 'date', value: product?.expiresOn || ''}))}
    ${safeLabel('Supplier <small>(optional)</small>', safeInput({name: 'supplier', maxlength: 160, value: product?.supplierRaw || ''}))}
    <div class="form-error" id="entityFormError" role="alert"></div>
    <div class="form-actions">
      <button class="btn btn-secondary" type="button" onclick="closeModal('entityModal')">Cancel</button>
      <button class="btn btn-primary" type="submit">${product ? 'Save Changes' : 'Create Product'}</button>
    </div>
  `;
}

/**
 * Safe notification item builder
 */
function buildNotificationItem(item, isRead) {
  const notificationIcon = {
    low_stock: '▣',
    expiry: '◷',
    payment: '₹',
    sale: '↗',
    system: '•'
  }[item.type] || '•';

  const dateStr = new Date(item.created_at).toLocaleString('en-IN', {
    day: 'numeric',
    month: 'short',
    hour: '2-digit',
    minute: '2-digit'
  });

  const unreadDot = isRead ? '' : '<i class="notification-unread" aria-label="Unread"></i>';

  return `
    <button class="notification-item ${escapeHtml(item.severity)} ${isRead ? 'is-read' : ''}"
            type="button"
            onclick="openNotification('${escapeHtml(item.id)}')">
      <span class="notification-icon">${notificationIcon}</span>
      <span class="notification-copy">
        <strong>${escapeHtml(item.title)}</strong>
        <span>${escapeHtml(item.message)}</span>
        <time>${escapeHtml(dateStr)}</time>
      </span>
      ${unreadDot}
    </button>
  `;
}

/**
 * Safe product form builder (duplicate for compatibility)
 */
function buildProductForm2(product = null) {
  const standardGstRates = [0, 5, 12, 18, 28];
  const hasCustomGst = product?.gstSelectionType === 'custom' ||
    (product?.gstRate != null && !standardGstRates.includes(Number(product.gstRate)));

  const gstOptions = standardGstRates.map(rate => ({
    value: String(rate),
    label: `${rate}%`
  }));
  gstOptions.unshift({value: '', label: 'Select GST'});
  gstOptions.push({value: 'custom', label: 'Custom GST'});

  const selectedGst = hasCustomGst ? 'custom' : (product?.gstRate != null ? String(product.gstRate) : '');

  return `
    ${safeLabel('Name', safeInput({name: 'name', required: true, maxlength: 160, value: product?.nameRaw || ''}))}
    ${safeLabel('SKU', safeInput({name: 'sku', required: true, maxlength: 80, value: product?.skuRaw || ''}))}
    ${safeLabel('Product Type', safeSelect(
      {name: 'category', required: true},
      [
        {value: 'Fertilizer', label: 'Fertilizer'},
        {value: 'Pesticides', label: 'Pesticides'}
      ]
    ).replace('value="Fertilizer"', `value="Fertilizer"${product?.categoryRaw === 'Fertilizer' || !product ? ' selected' : ''}`)
     .replace('value="Pesticides"', `value="Pesticides"${product?.categoryRaw === 'Pesticides' ? ' selected' : ''}`))}
    ${safeLabel('Unit', safeInput({name: 'unit', required: true, maxlength: 40, value: product?.unitRaw || ''}))}
    ${safeLabel('Purchase price (incl. GST)', safeInput({name: 'purchase_price_including_gst', type: 'number', min: 0, step: 0.01, value: product?.purchasePrice || ''}))}
    ${safeLabel('Selling price', safeInput({name: 'selling_price', type: 'number', min: 0, step: 0.01, value: product?.price || '', placeholder: 'Not Verified'}))}
    ${safeLabel('GST rate (%)', safeSelect(
      {name: 'gst_rate'},
      gstOptions
    ).replace(`value="${selectedGst}"`, `value="${selectedGst}" selected`).replace('name="gst_rate"', 'name="gst_rate" id="productGstRate"'))}
    ${safeLabel('Custom GST (%)', safeInput({
      name: 'custom_gst_rate',
      id: 'customGstRate',
      type: 'number',
      min: 0,
      max: 100,
      step: 0.01,
      value: hasCustomGst ? product.gstRate : '',
      required: hasCustomGst
    }), {hidden: !hasCustomGst, id: 'customGstRateLabel'})}
    ${safeLabel('Selling price tax mode', `<select name="selling_price_tax_mode">
      <option value="inclusive"${product?.sellingPriceTaxMode === 'inclusive' ? ' selected' : ''}>Tax inclusive</option>
      <option value="exclusive"${!product || product.sellingPriceTaxMode !== 'inclusive' ? ' selected' : ''}>Tax exclusive</option>
    </select>`)}
    ${safeLabel('Pack size', safeInput({name: 'pack_size', maxlength: 80, value: product?.packSize || ''}))}
    ${safeLabel('Current stock', safeInput({name: 'stock', type: 'number', min: 0, step: 0.01, required: true, value: product?.stock || 0}))}
    ${safeLabel('Low-stock threshold', safeInput({name: 'min_stock', type: 'number', min: 0, step: 0.01, required: true, value: product?.min_stock || 10}))}
    ${safeLabel('Expiry date <small>(optional)</small>', safeInput({name: 'expires_on', type: 'date', value: product?.expiresOn || ''}))}
    ${safeLabel('Supplier <small>(optional)</small>', safeInput({name: 'supplier', maxlength: 160, value: product?.supplierRaw || ''}))}
    <div class="form-error" id="entityFormError" role="alert"></div>
    <div class="form-actions">
      <button class="btn btn-secondary" type="button" onclick="closeModal('entityModal')">Cancel</button>
      <button class="btn btn-primary" type="submit">${product ? 'Save Changes' : 'Create Product'}</button>
    </div>
  `;
}

/**
 * Safe notification item builder
 */
function buildNotificationItem2(item, isRead) {
  const notificationIcon = {
    low_stock: '▣',
    expiry: '◷',
    payment: '₹',
    sale: '↗',
    system: '•'
  }[item.type] || '•';

  const dateStr = new Date(item.created_at).toLocaleString('en-IN', {
    day: 'numeric',
    month: 'short',
    hour: '2-digit',
    minute: '2-digit'
  });

  const unreadDot = isRead ? '' : '<i class="notification-unread" aria-label="Unread"></i>';

  return `
    <button class="notification-item ${escapeHtml(item.severity)} ${isRead ? 'is-read' : ''}"
            type="button"
            onclick="openNotification('${escapeHtml(item.id)}')">
      <span class="notification-icon">${notificationIcon}</span>
      <span class="notification-copy">
        <strong>${escapeHtml(item.title)}</strong>
        <span>${escapeHtml(item.message)}</span>
        <time>${escapeHtml(dateStr)}</time>
      </span>
      ${unreadDot}
    </button>
  `;
}

/**
 * Make functions globally available
 */
window.safeInput = safeInput;
window.safeSelect = safeSelect;
window.safeLabel = safeLabel;
window.buildProductForm = buildProductForm;
window.buildFarmerForm = buildFarmerForm;
window.buildNotificationItem = buildNotificationItem;
window.escapeHtmlSafe = escapeHtml;