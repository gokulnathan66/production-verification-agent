/**
 * A2A Multi-Agent Dashboard - Utility Functions
 * Common helpers for UI and data manipulation
 */

/**
 * Show toast notification
 * @param {string} message - Message to display
 * @param {string} type - Toast type: success, error, warning, info
 * @param {number} duration - Duration in ms (default 3000)
 */
function showToast(message, type = 'info', duration = 3000) {
  // Create toast element
  const toast = document.createElement('div');
  toast.className = `toast ${type}`;
  toast.innerHTML = `
    <div style="display: flex; align-items: center; gap: 12px;">
      <span style="font-size: 20px;">
        ${type === 'success' ? '✅' : type === 'error' ? '❌' : type === 'warning' ? '⚠️' : 'ℹ️'}
      </span>
      <span>${message}</span>
    </div>
  `;

  // Add to document
  document.body.appendChild(toast);

  // Remove after duration
  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transform = 'translateX(100%)';
    setTimeout(() => toast.remove(), 300);
  }, duration);
}

/**
 * Format timestamp to relative time
 * @param {string} timestamp - ISO timestamp
 * @returns {string} Relative time string
 */
function formatRelativeTime(timestamp) {
  const date = new Date(timestamp);
  const now = new Date();
  const diff = now - date;

  const seconds = Math.floor(diff / 1000);
  const minutes = Math.floor(seconds / 60);
  const hours = Math.floor(minutes / 60);
  const days = Math.floor(hours / 24);

  if (seconds < 60) return `${seconds}s ago`;
  if (minutes < 60) return `${minutes}m ago`;
  if (hours < 24) return `${hours}h ago`;
  if (days < 7) return `${days}d ago`;

  return date.toLocaleDateString();
}

/**
 * Format timestamp to readable date/time
 * @param {string} timestamp - ISO timestamp
 * @returns {string} Formatted date/time
 */
function formatDateTime(timestamp) {
  const date = new Date(timestamp);
  return date.toLocaleString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit'
  });
}

/**
 * Format file size to human-readable string
 * @param {number} bytes - File size in bytes
 * @returns {string} Formatted size
 */
function formatFileSize(bytes) {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return `${(bytes / Math.pow(k, i)).toFixed(2)} ${sizes[i]}`;
}

/**
 * Get status badge HTML
 * @param {string} status - Status string
 * @returns {string} Badge HTML
 */
function getStatusBadge(status) {
  const statusMap = {
    completed: 'completed',
    in_progress: 'in_progress',
    error: 'error',
    pending: 'pending',
    warning: 'warning'
  };

  const badgeClass = statusMap[status] || 'pending';
  const statusText = status.replace('_', ' ').toUpperCase();

  return `
    <span class="badge badge-${badgeClass}">
      <span class="badge-dot"></span>
      ${statusText}
    </span>
  `;
}

/**
 * Get health indicator HTML
 * @param {string} health - Health status
 * @returns {string} Health indicator HTML
 */
function getHealthIndicator(health) {
  const healthMap = {
    healthy: 'healthy',
    offline: 'offline',
    degraded: 'degraded',
    unknown: 'offline'
  };

  const healthClass = healthMap[health] || 'offline';
  const healthText = health.toUpperCase();

  return `
    <div class="agent-health">
      <span class="health-indicator ${healthClass}"></span>
      <span>${healthText}</span>
    </div>
  `;
}

/**
 * Debounce function
 * @param {Function} func - Function to debounce
 * @param {number} wait - Wait time in ms
 * @returns {Function} Debounced function
 */
function debounce(func, wait) {
  let timeout;
  return function executedFunction(...args) {
    const later = () => {
      clearTimeout(timeout);
      func(...args);
    };
    clearTimeout(timeout);
    timeout = setTimeout(later, wait);
  };
}

/**
 * Truncate text with ellipsis
 * @param {string} text - Text to truncate
 * @param {number} maxLength - Maximum length
 * @returns {string} Truncated text
 */
function truncateText(text, maxLength) {
  if (text.length <= maxLength) return text;
  return text.substring(0, maxLength) + '...';
}

/**
 * Escape HTML to prevent XSS
 * @param {string} text - Text to escape
 * @returns {string} Escaped text
 */
function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

/**
 * Get log level color class
 * @param {string} level - Log level
 * @returns {string} CSS class
 */
function getLogLevelClass(level) {
  const levelMap = {
    INFO: 'info',
    WARNING: 'warning',
    ERROR: 'error',
    SUCCESS: 'success',
    DEBUG: 'info'
  };

  return levelMap[level.toUpperCase()] || 'info';
}

/**
 * Create modal element
 * @param {string} title - Modal title
 * @param {string} content - Modal content HTML
 * @param {Array} buttons - Array of button objects {text, className, onClick}
 * @returns {HTMLElement} Modal element
 */
function createModal(title, content, buttons = []) {
  const backdrop = document.createElement('div');
  backdrop.className = 'modal-backdrop';

  backdrop.innerHTML = `
    <div class="modal">
      <div class="modal-header">
        <h3 class="modal-title">${title}</h3>
        <button class="modal-close">&times;</button>
      </div>
      <div class="modal-body">
        ${content}
      </div>
      <div class="modal-footer">
        ${buttons.map(btn => `
          <button class="${btn.className || 'btn btn-secondary'}" data-action="${btn.action || ''}">
            ${btn.text}
          </button>
        `).join('')}
      </div>
    </div>
  `;

  // Close on backdrop click
  backdrop.addEventListener('click', (e) => {
    if (e.target === backdrop) {
      backdrop.remove();
    }
  });

  // Close button
  backdrop.querySelector('.modal-close').addEventListener('click', () => {
    backdrop.remove();
  });

  // Button actions
  buttons.forEach((btn, index) => {
    if (btn.onClick) {
      const buttonEl = backdrop.querySelectorAll('.modal-footer button')[index];
      buttonEl.addEventListener('click', () => {
        btn.onClick();
        if (btn.closeOnClick !== false) {
          backdrop.remove();
        }
      });
    }
  });

  return backdrop;
}

/**
 * Get current page name for navigation highlighting
 * @returns {string} Current page name
 */
function getCurrentPage() {
  const path = window.location.pathname;
  if (path === '/' || path.includes('index.html')) return 'upload';
  if (path.includes('tasks.html')) return 'tasks';
  if (path.includes('logs.html')) return 'logs';
  if (path.includes('progress.html')) return 'progress';
  return '';
}

/**
 * Copy text to clipboard
 * @param {string} text - Text to copy
 */
async function copyToClipboard(text) {
  try {
    await navigator.clipboard.writeText(text);
    showToast('Copied to clipboard!', 'success', 2000);
  } catch (error) {
    showToast('Failed to copy', 'error');
  }
}
