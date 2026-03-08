/**
 * A2A Multi-Agent Dashboard - Tasks Page Logic
 * Handles task list display, filtering, and details modal
 */

// DOM Elements
const filterAgent = document.getElementById('filter-agent');
const filterStatus = document.getElementById('filter-status');
const refreshBtn = document.getElementById('refresh-tasks');
const autoRefreshCheckbox = document.getElementById('auto-refresh-checkbox');
const tasksTbody = document.getElementById('tasks-tbody');

// State
let currentFilters = {
  agent_id: null,
  status: null
};
let autoRefreshInterval = null;
let allTasks = [];

// Initialize
document.addEventListener('DOMContentLoaded', () => {
  initializePage();
});

/**
 * Initialize page
 */
async function initializePage() {
  await loadAgents();
  await loadTasks();
  setupEventListeners();
  startAutoRefresh();
}

/**
 * Setup event listeners
 */
function setupEventListeners() {
  // Filter changes
  filterAgent.addEventListener('change', () => {
    currentFilters.agent_id = filterAgent.value || null;
    loadTasks();
  });

  filterStatus.addEventListener('change', () => {
    currentFilters.status = filterStatus.value || null;
    loadTasks();
  });

  // Refresh button
  refreshBtn.addEventListener('click', loadTasks);

  // Auto-refresh toggle
  autoRefreshCheckbox.addEventListener('change', () => {
    if (autoRefreshCheckbox.checked) {
      startAutoRefresh();
    } else {
      stopAutoRefresh();
    }
  });
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
 * Load tasks with current filters
 */
async function loadTasks() {
  refreshBtn.innerHTML = '<span class="loading"></span>';
  refreshBtn.disabled = true;

  try {
    const data = await apiClient.getTaskHistory({
      ...currentFilters,
      limit: 100
    });

    allTasks = data.tasks || [];

    if (allTasks.length > 0) {
      renderTasks(allTasks);
    } else {
      showEmptyState();
    }
  } catch (error) {
    showToast(`Failed to load tasks: ${error.message}`, 'error');
    showErrorState(error.message);
  } finally {
    refreshBtn.innerHTML = '🔄 Refresh';
    refreshBtn.disabled = false;
  }
}

/**
 * Render tasks table
 */
function renderTasks(tasks) {
  tasksTbody.innerHTML = tasks.map(task => {
    const duration = calculateDuration(task.created_at, task.completed_at);

    return `
      <tr onclick="showTaskDetails('${task.id}')" style="cursor: pointer;">
        <td>
          <code class="task-id">${escapeHtml(task.id).substring(0, 12)}...</code>
        </td>
        <td>
          <div style="display: flex; flex-direction: column; gap: 4px;">
            <span style="font-weight: 500;">${escapeHtml(task.agent_name || task.agent_id)}</span>
            <code style="font-size: 10px; opacity: 0.6;">${escapeHtml(task.agent_id)}</code>
          </div>
        </td>
        <td>
          <div style="max-width: 400px;">
            ${escapeHtml(truncateText(task.request, 100))}
          </div>
        </td>
        <td>
          ${getStatusBadge(task.status)}
        </td>
        <td>
          <div style="display: flex; flex-direction: column; gap: 4px;">
            <span class="task-timestamp">${formatRelativeTime(task.created_at)}</span>
            <span style="font-size: 10px; opacity: 0.6;">${formatDateTime(task.created_at)}</span>
          </div>
        </td>
        <td>
          <span class="font-mono text-sm">${duration}</span>
        </td>
      </tr>
    `;
  }).join('');
}

/**
 * Calculate task duration
 */
function calculateDuration(startTime, endTime) {
  if (!endTime) return '-';

  const start = new Date(startTime);
  const end = new Date(endTime);
  const diff = end - start;

  const seconds = Math.floor(diff / 1000);
  const minutes = Math.floor(seconds / 60);
  const hours = Math.floor(minutes / 60);

  if (hours > 0) return `${hours}h ${minutes % 60}m`;
  if (minutes > 0) return `${minutes}m ${seconds % 60}s`;
  return `${seconds}s`;
}

/**
 * Show empty state
 */
function showEmptyState() {
  tasksTbody.innerHTML = `
    <tr>
      <td colspan="6">
        <div class="empty-state">
          <div class="empty-state-icon">📋</div>
          <div class="empty-state-title">No tasks found</div>
          <div class="empty-state-text">Try adjusting your filters or execute a new task</div>
        </div>
      </td>
    </tr>
  `;
}

/**
 * Show error state
 */
function showErrorState(message) {
  tasksTbody.innerHTML = `
    <tr>
      <td colspan="6">
        <div class="empty-state">
          <div class="empty-state-icon">❌</div>
          <div class="empty-state-title">Error loading tasks</div>
          <div class="empty-state-text">${escapeHtml(message)}</div>
        </div>
      </td>
    </tr>
  `;
}

/**
 * Show task details in modal
 */
async function showTaskDetails(taskId) {
  try {
    const data = await apiClient.getTaskDetails(taskId);
    const task = data.task;

    if (!task) {
      showToast('Task not found', 'error');
      return;
    }

    // Format task result/error
    let resultHtml = '';
    if (task.result) {
      try {
        const resultObj = typeof task.result === 'string' ? JSON.parse(task.result) : task.result;
        resultHtml = `<pre>${JSON.stringify(resultObj, null, 2)}</pre>`;
      } catch {
        resultHtml = `<pre>${escapeHtml(task.result)}</pre>`;
      }
    }

    let errorHtml = '';
    if (task.error) {
      errorHtml = `
        <div style="background: rgba(239, 68, 68, 0.1); border: 1px solid var(--color-error); border-radius: 8px; padding: 12px; margin-top: 16px;">
          <strong style="color: var(--color-error);">Error:</strong>
          <pre style="margin-top: 8px; background: transparent; border: none; padding: 0;">${escapeHtml(task.error)}</pre>
        </div>
      `;
    }

    // Create modal content
    const content = `
      <div style="display: flex; flex-direction: column; gap: 16px;">
        <!-- Basic Info -->
        <div>
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
            <span style="font-size: 12px; color: var(--color-text-tertiary);">TASK ID</span>
            ${getStatusBadge(task.status)}
          </div>
          <code style="font-size: 14px; padding: 8px 12px; display: block; background: var(--color-bg-elevated); border-radius: 6px;">${escapeHtml(task.id)}</code>
        </div>

        <!-- Agent Info -->
        <div>
          <div style="font-size: 12px; color: var(--color-text-tertiary); margin-bottom: 8px;">AGENT</div>
          <div style="display: flex; flex-direction: column; gap: 4px;">
            <span style="font-weight: 500;">${escapeHtml(task.agent_name || task.agent_id)}</span>
            <code style="font-size: 12px; opacity: 0.6;">${escapeHtml(task.agent_id)}</code>
          </div>
        </div>

        <!-- Request -->
        <div>
          <div style="font-size: 12px; color: var(--color-text-tertiary); margin-bottom: 8px;">REQUEST</div>
          <div style="background: var(--color-bg-elevated); padding: 12px; border-radius: 8px; border: 1px solid var(--color-border-primary);">
            ${escapeHtml(task.request)}
          </div>
        </div>

        <!-- Timestamps -->
        <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 16px;">
          <div>
            <div style="font-size: 12px; color: var(--color-text-tertiary); margin-bottom: 8px;">CREATED</div>
            <div style="font-family: var(--font-mono); font-size: 13px;">${formatDateTime(task.created_at)}</div>
          </div>
          ${task.completed_at ? `
          <div>
            <div style="font-size: 12px; color: var(--color-text-tertiary); margin-bottom: 8px;">COMPLETED</div>
            <div style="font-family: var(--font-mono); font-size: 13px;">${formatDateTime(task.completed_at)}</div>
          </div>
          ` : ''}
        </div>

        <!-- Result -->
        ${task.result ? `
        <div>
          <div style="font-size: 12px; color: var(--color-text-tertiary); margin-bottom: 8px;">RESULT</div>
          <div style="max-height: 300px; overflow-y: auto;">
            ${resultHtml}
          </div>
        </div>
        ` : ''}

        <!-- Error -->
        ${errorHtml}

        <!-- Artifacts -->
        ${task.artifacts && task.artifacts.length > 0 ? `
        <div>
          <div style="font-size: 12px; color: var(--color-text-tertiary); margin-bottom: 8px;">ARTIFACTS</div>
          <div style="display: flex; flex-direction: column; gap: 8px;">
            ${task.artifacts.map(artifact => `
              <div style="background: var(--color-bg-elevated); padding: 8px 12px; border-radius: 6px; font-family: var(--font-mono); font-size: 12px;">
                ${escapeHtml(artifact)}
              </div>
            `).join('')}
          </div>
        </div>
        ` : ''}
      </div>
    `;

    const modal = createModal(
      `Task Details`,
      content,
      [
        {
          text: 'Close',
          className: 'btn btn-secondary',
          onClick: () => {}
        }
      ]
    );

    document.body.appendChild(modal);
  } catch (error) {
    showToast(`Failed to load task details: ${error.message}`, 'error');
  }
}

/**
 * Start auto-refresh
 */
function startAutoRefresh() {
  stopAutoRefresh(); // Clear any existing interval
  autoRefreshInterval = setInterval(() => {
    if (autoRefreshCheckbox.checked) {
      loadTasks();
    }
  }, 5000); // Refresh every 5 seconds
}

/**
 * Stop auto-refresh
 */
function stopAutoRefresh() {
  if (autoRefreshInterval) {
    clearInterval(autoRefreshInterval);
    autoRefreshInterval = null;
  }
}

// Clean up on page unload
window.addEventListener('beforeunload', () => {
  stopAutoRefresh();
});
