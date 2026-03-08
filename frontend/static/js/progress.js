/**
 * A2A Multi-Agent Dashboard - Progress Page Logic
 * Handles real-time agent status updates with SSE
 */

// DOM Elements
const streamStatus = document.getElementById('stream-status');
const lastUpdate = document.getElementById('last-update');
const statTotal = document.getElementById('stat-total');
const statActive = document.getElementById('stat-active');
const statCompleted = document.getElementById('stat-completed');
const statErrors = document.getElementById('stat-errors');
const agentCount = document.getElementById('agent-count');
const agentGrid = document.getElementById('agent-grid');

// State
let eventSource = null;
let currentData = null;

// Initialize
document.addEventListener('DOMContentLoaded', () => {
  initializePage();
});

/**
 * Initialize page
 */
function initializePage() {
  startProgressStream();
}

/**
 * Start progress stream with SSE
 */
function startProgressStream() {
  try {
    eventSource = apiClient.createProgressStream(
      (data) => {
        currentData = data;
        updateUI(data);
        updateStreamStatus(true);
        updateLastUpdate();
      },
      (error) => {
        console.error('Progress stream error:', error);
        updateStreamStatus(false);

        // Attempt to reconnect after 5 seconds
        setTimeout(() => {
          if (eventSource) {
            eventSource.close();
          }
          startProgressStream();
        }, 5000);
      }
    );

    updateStreamStatus(true);
  } catch (error) {
    console.error('Failed to start progress stream:', error);
    updateStreamStatus(false);
  }
}

/**
 * Update UI with new data
 */
function updateUI(data) {
  if (!data) return;

  // Update global stats
  if (data.global) {
    statTotal.textContent = data.global.total_tasks || 0;
    statActive.textContent = data.global.active_tasks || 0;
    statCompleted.textContent = data.global.completed_tasks || 0;
    statErrors.textContent = data.global.error_tasks || 0;

    // Add animation to values
    animateValue(statTotal);
    animateValue(statActive);
    animateValue(statCompleted);
    animateValue(statErrors);
  }

  // Update agents
  if (data.agents && data.agents.length > 0) {
    agentCount.textContent = data.agents.length;
    renderAgents(data.agents);
  } else {
    renderEmptyState();
  }
}

/**
 * Render agent cards
 */
function renderAgents(agents) {
  agentGrid.innerHTML = agents.map(agent => {
    const healthClass = agent.health === 'healthy' ? 'healthy' :
                       agent.health === 'offline' ? 'offline' : 'degraded';

    return `
      <div class="agent-card">
        <div class="agent-card-header">
          <div class="agent-name">${escapeHtml(agent.name || agent.agent_id)}</div>
          <div class="agent-health">
            <span class="health-indicator ${healthClass}"></span>
            <span>${agent.health.toUpperCase()}</span>
          </div>
        </div>

        <div style="font-family: var(--font-mono); font-size: var(--font-size-xs); color: var(--color-text-tertiary); margin-bottom: var(--space-md);">
          ${escapeHtml(agent.agent_id)}
        </div>

        <div class="agent-stats">
          <div class="agent-stat">
            <div class="agent-stat-value">${agent.active_tasks || 0}</div>
            <div class="agent-stat-label">Active</div>
          </div>

          <div class="agent-stat">
            <div class="agent-stat-value" style="color: var(--color-success);">
              ${agent.completed_tasks || 0}
            </div>
            <div class="agent-stat-label">Completed</div>
          </div>

          <div class="agent-stat">
            <div class="agent-stat-value" style="color: var(--color-text-tertiary);">
              ${agent.total_tasks || 0}
            </div>
            <div class="agent-stat-label">Total</div>
          </div>
        </div>

        ${agent.health !== 'healthy' ? `
          <div style="margin-top: var(--space-md); padding: var(--space-sm); background: rgba(239, 68, 68, 0.1); border-radius: var(--radius-sm); border: 1px solid var(--color-error); font-size: var(--font-size-xs); text-align: center; color: var(--color-error);">
            ⚠️ ${agent.health === 'offline' ? 'Agent Offline' : 'Health Degraded'}
          </div>
        ` : ''}
      </div>
    `;
  }).join('');
}

/**
 * Render empty state
 */
function renderEmptyState() {
  agentCount.textContent = '0';
  agentGrid.innerHTML = `
    <div class="empty-state" style="grid-column: 1 / -1;">
      <div class="empty-state-icon">🤖</div>
      <div class="empty-state-title">No agents discovered</div>
      <div class="empty-state-text">Use the /discover endpoint to add agents</div>
    </div>
  `;
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
 * Update last update timestamp
 */
function updateLastUpdate() {
  const now = new Date();
  lastUpdate.textContent = now.toLocaleTimeString('en-US', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit'
  });
}

/**
 * Animate value change
 */
function animateValue(element) {
  element.style.transform = 'scale(1.1)';
  element.style.transition = 'transform 0.2s ease';

  setTimeout(() => {
    element.style.transform = 'scale(1)';
  }, 200);
}

/**
 * Calculate completion percentage
 */
function calculateCompletionRate(completed, total) {
  if (total === 0) return 0;
  return Math.round((completed / total) * 100);
}

/**
 * Format uptime
 */
function formatUptime(seconds) {
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);

  if (hours > 0) return `${hours}h ${minutes}m`;
  if (minutes > 0) return `${minutes}m`;
  return `${seconds}s`;
}

// Clean up on page unload
window.addEventListener('beforeunload', () => {
  if (eventSource) {
    eventSource.close();
  }
});
