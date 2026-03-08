/**
 * A2A Multi-Agent Dashboard - API Client
 * Handles all communication with the backend
 */

class A2AApiClient {
  constructor(baseUrl = '') {
    this.baseUrl = baseUrl;
  }

  /**
   * Generic request handler with error handling
   */
  async request(endpoint, options = {}) {
    try {
      const response = await fetch(`${this.baseUrl}${endpoint}`, {
        ...options,
        headers: {
          'Content-Type': 'application/json',
          ...options.headers,
        },
      });

      if (!response.ok) {
        const error = await response.json().catch(() => ({}));
        throw new Error(error.detail || `HTTP ${response.status}: ${response.statusText}`);
      }

      return await response.json();
    } catch (error) {
      console.error(`API Error [${endpoint}]:`, error);
      throw error;
    }
  }

  /**
   * Upload artifact to S3
   * @param {FormData} formData - Form data with file and metadata
   * @returns {Promise<Object>} Upload result
   */
  async uploadArtifact(formData) {
    try {
      const response = await fetch(`${this.baseUrl}/api/artifacts/upload`, {
        method: 'POST',
        body: formData,
        // Don't set Content-Type header - browser will set it with boundary for FormData
      });

      if (!response.ok) {
        const error = await response.json().catch(() => ({}));
        throw new Error(error.detail || 'Upload failed');
      }

      return await response.json();
    } catch (error) {
      console.error('Upload Error:', error);
      throw error;
    }
  }

  /**
   * Get list of artifacts
   * @param {Object} params - Query parameters
   * @returns {Promise<Object>} Artifacts list
   */
  async getArtifacts(params = {}) {
    const queryString = new URLSearchParams(params).toString();
    return this.request(`/api/artifacts${queryString ? `?${queryString}` : ''}`);
  }

  /**
   * Get task history with optional filters
   * @param {Object} filters - Filter parameters
   * @returns {Promise<Object>} Task history
   */
  async getTaskHistory(filters = {}) {
    const queryString = new URLSearchParams(
      Object.entries(filters).filter(([_, v]) => v != null)
    ).toString();
    return this.request(`/api/tasks/history${queryString ? `?${queryString}` : ''}`);
  }

  /**
   * Get details for a specific task
   * @param {string} taskId - Task ID
   * @returns {Promise<Object>} Task details
   */
  async getTaskDetails(taskId) {
    return this.request(`/api/tasks/${taskId}/details`);
  }

  /**
   * Get logs with optional filters
   * @param {Object} filters - Filter parameters
   * @returns {Promise<Object>} Logs
   */
  async getLogs(filters = {}) {
    const queryString = new URLSearchParams(
      Object.entries(filters).filter(([_, v]) => v != null)
    ).toString();
    return this.request(`/api/logs${queryString ? `?${queryString}` : ''}`);
  }

  /**
   * Execute a task on an agent
   * @param {Object} request - Task request
   * @returns {Promise<Object>} Execution result
   */
  async executeTask(request) {
    return this.request('/execute', {
      method: 'POST',
      body: JSON.stringify(request),
    });
  }

  /**
   * Get list of all agents
   * @returns {Promise<Object>} Agents list
   */
  async getAgents() {
    return this.request('/agents');
  }

  /**
   * Discover a new agent
   * @param {string} url - Agent URL
   * @returns {Promise<Object>} Discovery result
   */
  async discoverAgent(url) {
    return this.request('/discover', {
      method: 'POST',
      body: JSON.stringify({ url }),
    });
  }

  /**
   * Check system health
   * @returns {Promise<Object>} Health status
   */
  async getHealth() {
    return this.request('/health');
  }

  /**
   * Create SSE connection for log streaming
   * @param {Function} onMessage - Callback for new log entries
   * @param {Function} onError - Error callback
   * @returns {EventSource} EventSource instance
   */
  createLogStream(onMessage, onError) {
    const eventSource = new EventSource(`${this.baseUrl}/api/logs/stream`);

    eventSource.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        onMessage(data);
      } catch (error) {
        console.error('Error parsing log stream data:', error);
      }
    };

    eventSource.onerror = (error) => {
      console.error('Log stream error:', error);
      if (onError) onError(error);
    };

    return eventSource;
  }

  /**
   * Create SSE connection for progress streaming
   * @param {Function} onMessage - Callback for progress updates
   * @param {Function} onError - Error callback
   * @returns {EventSource} EventSource instance
   */
  createProgressStream(onMessage, onError) {
    const eventSource = new EventSource(`${this.baseUrl}/api/progress/stream`);

    eventSource.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        onMessage(data);
      } catch (error) {
        console.error('Error parsing progress stream data:', error);
      }
    };

    eventSource.onerror = (error) => {
      console.error('Progress stream error:', error);
      if (onError) onError(error);
    };

    return eventSource;
  }
}

// Export singleton instance
const apiClient = new A2AApiClient();
