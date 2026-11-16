/**
 * Security utilities for XSS prevention and input sanitization
 */

/**
 * Escape HTML special characters to prevent XSS attacks.
 * This is the PRIMARY defense against cross-site scripting.
 * 
 * @param {*} value - Value to escape
 * @returns {string} - HTML-safe string
 */
function escapeHtml(value) {
  if (value == null) return '';
  return String(value).replace(/[&<>"']/g, function(char) {
    const entities = {
      '&': '&amp;',
      '<': '&lt;',
      '>': '&gt;',
      '"': '&quot;',
      "'": '&#39;'
    };
    return entities[char];
  });
}

/**
 * Sanitize user input for use in HTML attributes.
 * Removes potentially dangerous characters.
 */
function sanitizeAttr(value) {
  if (value == null) return '';
  // Remove quotes and angle brackets from attributes
  return String(value).replace(/["'<>]/g, '');
}

/**
 * Validate and sanitize numeric input.
 * Returns null if invalid.
 */
function sanitizeNumber(value, options = {}) {
  const { min = -Infinity, max = Infinity, allowDecimal = true } = options;
  
  if (value === '' || value == null) return null;
  
  const num = allowDecimal ? parseFloat(value) : parseInt(value, 10);
  
  if (isNaN(num) || num < min || num > max) {
    return null;
  }
  
  return num;
}

/**
 * Validate email format (basic check)
 */
function isValidEmail(email) {
  const pattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  return pattern.test(String(email));
}

/**
 * Validate phone number (allow international formats)
 */
function isValidPhone(phone) {
  const cleaned = String(phone).replace(/\D/g, '');
  return cleaned.length >= 6 && cleaned.length <= 15;
}

/**
 * Sanitize SKU (alphanumeric, dash, underscore only)
 */
function sanitizeSKU(sku) {
  return String(sku).replace(/[^A-Za-z0-9_-]/g, '').substring(0, 80);
}

/**
 * Create a safe HTML string from a template.
 * All variables are automatically escaped.
 * 
 * Usage: safeHtml`<div>${dangerousValue}</div>`
 */
function safeHtml(strings, ...values) {
  let result = strings[0];
  for (let i = 0; i < values.length; i++) {
    result += escapeHtml(values[i]) + strings[i + 1];
  }
  return result;
}

/**
 * Rate limiting helper for client-side operations
 */
class RateLimiter {
  constructor(maxAttempts = 5, windowMs = 60000) {
    this.attempts = new Map();
    this.maxAttempts = maxAttempts;
    this.windowMs = windowMs;
  }
  
  check(key) {
    const now = Date.now();
    const attempts = this.attempts.get(key) || [];
    
    // Clean old attempts
    const recentAttempts = attempts.filter(time => now - time < this.windowMs);
    
    if (recentAttempts.length >= this.maxAttempts) {
      return false;
    }
    
    recentAttempts.push(now);
    this.attempts.set(key, recentAttempts);
    return true;
  }
  
  reset(key) {
    this.attempts.delete(key);
  }
}

/**
 * Content Security Policy violation reporter
 */
function setupCSPReporting() {
  document.addEventListener('securitypolicyviolation', (event) => {
    console.error('CSP Violation:', {
      blockedURI: event.blockedURI,
      violatedDirective: event.violatedDirective,
      originalPolicy: event.originalPolicy
    });
    
    // Report to backend (optional)
    if (window.authToken) {
      fetch('/api/csp-report', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${window.authToken}`
        },
        body: JSON.stringify({
          blockedURI: event.blockedURI,
          violatedDirective: event.violatedDirective,
          timestamp: new Date().toISOString()
        })
      }).catch(() => {
        // Silent failure for CSP reporting
      });
    }
  });
}

// Initialize on load
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', setupCSPReporting);
} else {
  setupCSPReporting();
}

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
  module.exports = {
    escapeHtml,
    sanitizeAttr,
    sanitizeNumber,
    isValidEmail,
    isValidPhone,
    sanitizeSKU,
    safeHtml,
    RateLimiter
  };
}
