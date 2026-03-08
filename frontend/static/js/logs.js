/**
 * A2A Multi-Agent Dashboard - Logs Page Logic
 * Handles real-time log streaming with SSE, filtering, and auto-scroll
 */

// DOM Elements
const filterAgent = document.getElementById('filter-agent');
const filterLevel = document.getElementById('filter-level');
const searchInput = document.getElementById('search-input');
const autoScrollCheckbox = document.getElementById('auto-scroll-checkbox');
const autoScrollToggle = document.getElementById('auto-scroll-toggle');
const clearLogsBtn = document.getElementById('clear-logs');
const downloadLogsBtn = document.getElementById('download-logs');
const logContainer = document.getElementById('log-container');
const logCount = document.getElementById('log-count');
const streamStatus = document.getElementById('stream-status');

// State
let allLogs = [];
let filteredLogs = [];
let eventSource = null;
let currentFilters = {
  agent: null,
  level: null,
  search: null
};

const MAX_LOGS = 500; // Keep max 500 logs in memory

// Initialize
document.addEventListener('DOMContentLoaded', () => {
  initializePage();
});

/**
 * Initialize page
 */
async function initializePage() {
  await loadAgents();
  await loadInitialLogs();
  setupEventListeners();
  startLogStream();
}

/**
 * Setup event listeners
 */
function setupEventListeners() {
  // Filters
  filterAgent.addEventListener('change', () => {
    currentFilters.agent = filterAgent.value || null;
    applyFilters();
  });

  filterLevel.addEventListener('change', () => {
    currentFilters.level = filterLevel.value || null;
    applyFilters();
  });

  searchInput.addEventListener('input', debounce(() => {
    currentFilters.search = searchInput.value.trim().toLowerCase() || null;
    applyFilters();
  }, 300));

  // Auto-scroll
  autoScrollCheckbox.addEventListener('change', () => {
    if (autoScrollCheckbox.checked) {
      autoScrollToggle.classList.add('active');
      scrollToBottom();
    } else {
      autoScrollToggle.classList.remove('active');
    }
  });

  // Clear logs
  clearLogsBtn.addEventListener('click', () => {
    allLogs = [];
    filteredLogs = [];
    renderLogs();
    updateLogCount();
    showToast('Logs cleared', 'info');
  });

  // Download logs
  downloadLogsBtn.addEventListener('click', downloadLogs);
}

/**
 * Load agents for filter dropdown
 */
async function loadAgents() {
  try {
    const data = await apiClient.getAgents();

    if (data.agents && data.agents.length > 0) {
      const options = data.agents.map(agent => `
        <option value="${agent.agentId}">${agent.name}</option>
      `).join('');

      filterAgent.innerHTML = '<option value="">All Agents</option>' + options;
    }
  } catch (error) {
    console.error('Failed to load agents:', error);
  }
}

/**
 * Load initial logs (last 100)
 */
async function loadInitialLogs() {
  try {
    const data = await apiClient.getLogs({ limit: 100 });

    if (data.logs && data.logs.length > 0) {
      allLogs = data.logs.reverse(); // Reverse to get chronological order
      applyFilters();
    }
  } catch (error) {
    console.error('Failed to load initial logs:', error);
  }
}

/**
 * Start log stream with SSE
 */
function startLogStream() {
  try {
    eventSource = apiClient.createLogStream(
      (log) => {
        // Add new log to allLogs
        allLogs.push(log);

        // Keep only last MAX_LOGS
        if (allLogs.length > MAX_LOGS) {
          allLogs.shift();
        }

        // Apply filters to show/hide new log
        applyFilters();

        // Update status
        updateStreamStatus(true);
      },
      (error) => {
        console.error('Log stream error:', error);
        updateStreamStatus(false);

        // Attempt to reconnect after 5 seconds
        setTimeout(() => {
          if (eventSource) {
            eventSource.close();
          }
          startLogStream();
        }, 5000);
      }
    );

    updateStreamStatus(true);
  } catch (error) {
    console.error('Failed to start log stream:', error);
    updateStreamStatus(false);
  }
}

/**
 * Apply filters to logs
 */
function applyFilters() {
  filteredLogs = allLogs.filter(log => {
    // Agent filter
    if (currentFilters.agent && log.agent_id !== currentFilters.agent) {
      return false;
    }

    // Level filter
    if (currentFilters.level && log.level !== currentFilters.level) {
      return false;
    }

    // Search filter
    if (currentFilters.search) {
      const searchLower = currentFilters.search;
      const message = (log.message || '').toLowerCase();
      const agentName = (log.agent_name || '').toLowerCase();
      const agentId = (log.agent_id || '').toLowerCase();

      if (!message.includes(searchLower) &&
          !agentName.includes(searchLower) &&
          !agentId.includes(searchLower)) {
        return false;
      }
    }

    return true;
  });

  renderLogs();
  updateLogCount();

  // Auto-scroll if enabled
  if (autoScrollCheckbox.checked) {
    scrollToBottom();
  }
}

/**
 * Render logs in container
 */
function renderLogs() {
  if (filteredLogs.length === 0) {
    logContainer.innerHTML = `
      <div class="empty-state">
        <div class="empty-state-icon">📜</div>
        <div class="empty-state-title">No logs to display</div>
        <div class="empty-state-text">
          ${allLogs.length === 0 ? 'Waiting for logs...' : 'Try adjusting your filters'}
        </div>
      </div>
    `;
    return;
  }

  // Render only last 500 logs for performance
  const logsToRender = filteredLogs.slice(-MAX_LOGS);

  logContainer.innerHTML = logsToRender.map(log => {
    const levelClass = getLogLevelClass(log.level);
    const timestamp = new Date(log.timestamp).toLocaleTimeString('en-US', {
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      fractionalSecondDigits: 3
    });

    return `
      <div class="log-entry ${levelClass}">
        <span class="log-timestamp">${timestamp}</span>
        <span class="log-level">${escapeHtml(log.level)}</span>
        <span style="color: var(--color-text-tertiary); white-space: nowrap; font-size: 11px;">
          [${escapeHtml(log.agent_name || log.agent_id)}]
        </span>
        <span class="log-message">${escapeHtml(log.message)}</span>
      </div>
    `;
  }).join('');
}

/**
 * Update log count display
 */
function updateLogCount() {
  logCount.textContent = filteredLogs.length;
}

/**
 * Update stream status indicator
 */
function updateStreamStatus(connected) {
  const indicator = streamStatus.querySelector('.health-indicator');
  const text = streamStatus.querySelector('span:last-child');

  if (connected) {
    indicator.className = 'health-indicator healthy';
    text.textContent = 'Stream Connected';
  } else {
    indicator.className = 'health-indicator offline';
    text.textContent = 'Stream Disconnected';
  }
}

/**
 * Scroll to bottom of log container
 */
function scrollToBottom() {
  requestAnimationFrame(() => {
    logContainer.scrollTop = logContainer.scrollHeight;
  });
}

/**
 * Download logs as file
 */
function downloadLogs() {
  if (filteredLogs.length === 0) {
    showToast('No logs to download', 'warning');
    return;
  }

  // Format logs as text
  const logsText = filteredLogs.map(log => {
    const timestamp = new Date(log.timestamp).toISOString();
    const agent = log.agent_name || log.agent_id;
    return `[${timestamp}] [${log.level}] [${agent}] ${log.message}`;
  }).join('\n');

  // Create and download file
  const blob = new Blob([logsText], { type: 'text/plain' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `a2a-logs-${new Date().toISOString()}.txt`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);

  showToast('Logs downloaded successfully', 'success');
}

// Clean up on page unload
window.addEventListener('beforeunload', () => {
  if (eventSource) {
    eventSource.close();
  }
});
