/**
 * A2A Multi-Agent Dashboard - Upload Page Logic
 * Handles file upload, drag-and-drop, and recent uploads display
 */

// DOM Elements
const uploadZone = document.getElementById('upload-zone');
const fileInput = document.getElementById('file-input');
const fileInfo = document.getElementById('file-info');
const fileName = document.getElementById('file-name');
const fileSize = document.getElementById('file-size');
const removeFileBtn = document.getElementById('remove-file');
const metadataForm = document.getElementById('metadata-form');
const projectNameInput = document.getElementById('project-name-input');
const tagsInput = document.getElementById('tags-input');
const descriptionInput = document.getElementById('description-input');
const uploadBtn = document.getElementById('upload-btn');
const uploadProgress = document.getElementById('upload-progress');
const progressBarFill = document.getElementById('progress-bar-fill');
const progressText = document.getElementById('progress-text');
const recentUploadsContainer = document.getElementById('recent-uploads');
const refreshListBtn = document.getElementById('refresh-list');

// State
let selectedFile = null;

// Initialize
document.addEventListener('DOMContentLoaded', () => {
  initializeUploadZone();
  loadRecentUploads();
  checkSystemHealth();
});

/**
 * Initialize upload zone with drag-and-drop
 */
function initializeUploadZone() {
  // Click to select file
  uploadZone.addEventListener('click', () => {
    if (!selectedFile) {
      fileInput.click();
    }
  });

  // File input change
  fileInput.addEventListener('change', (e) => {
    const file = e.target.files[0];
    if (file) {
      handleFileSelect(file);
    }
  });

  // Drag and drop events
  uploadZone.addEventListener('dragover', (e) => {
    e.preventDefault();
    uploadZone.classList.add('drag-over');
  });

  uploadZone.addEventListener('dragleave', () => {
    uploadZone.classList.remove('drag-over');
  });

  uploadZone.addEventListener('drop', (e) => {
    e.preventDefault();
    uploadZone.classList.remove('drag-over');

    const file = e.dataTransfer.files[0];
    if (file) {
      handleFileSelect(file);
    }
  });

  // Remove file button
  removeFileBtn.addEventListener('click', (e) => {
    e.stopPropagation();
    clearSelectedFile();
  });

  // Upload button
  uploadBtn.addEventListener('click', handleUpload);

  // Refresh list button
  refreshListBtn.addEventListener('click', loadRecentUploads);
}

/**
 * Handle file selection
 */
function handleFileSelect(file) {
  // Validate file type
  const allowedTypes = ['.py', '.js', '.java', '.go', '.rs', '.txt', '.json', '.yaml', '.yml', '.md', '.zip'];
  const fileExt = '.' + file.name.split('.').pop().toLowerCase();

  if (!allowedTypes.includes(fileExt)) {
    showToast(`File type ${fileExt} not supported. Please upload: ${allowedTypes.join(', ')}`, 'error');
    return;
  }

  // Validate file size (max 50MB)
  const maxSize = 50 * 1024 * 1024; // 50MB
  if (file.size > maxSize) {
    showToast('File size exceeds 50MB limit', 'error');
    return;
  }

  selectedFile = file;

  // Update UI
  fileName.textContent = file.name;
  fileSize.textContent = formatFileSize(file.size);

  uploadZone.classList.add('hidden');
  fileInfo.classList.remove('hidden');
  metadataForm.classList.remove('hidden');
}

/**
 * Clear selected file
 */
function clearSelectedFile() {
  selectedFile = null;
  fileInput.value = '';

  uploadZone.classList.remove('hidden');
  fileInfo.classList.add('hidden');
  metadataForm.classList.add('hidden');
  uploadProgress.classList.add('hidden');

  projectNameInput.value = '';
  tagsInput.value = '';
  descriptionInput.value = '';
}

/**
 * Handle file upload
 */
async function handleUpload() {
  if (!selectedFile) {
    showToast('Please select a file first', 'error');
    return;
  }

  // Validate project name
  const projectName = projectNameInput.value.trim();
  if (!projectName) {
    showToast('Please enter a project name', 'error');
    projectNameInput.focus();
    return;
  }

  // Prepare form data
  const formData = new FormData();
  formData.append('file', selectedFile);
  formData.append('project_name', projectName);

  if (tagsInput.value.trim()) {
    formData.append('tags', tagsInput.value.trim());
  }

  if (descriptionInput.value.trim()) {
    formData.append('description', descriptionInput.value.trim());
  }

  // Show progress
  uploadBtn.disabled = true;
  uploadBtn.innerHTML = '<span class="loading"></span><span>Uploading...</span>';
  uploadProgress.classList.remove('hidden');
  progressBarFill.style.width = '0%';
  progressText.textContent = 'Uploading to S3...';

  // Simulate progress (since we can't track real upload progress with fetch)
  let progress = 0;
  const progressInterval = setInterval(() => {
    progress += 5;
    if (progress >= 90) {
      clearInterval(progressInterval);
    }
    progressBarFill.style.width = `${progress}%`;
  }, 100);

  try {
    // Upload to API
    const result = await apiClient.uploadArtifact(formData);

    // Complete progress
    clearInterval(progressInterval);
    progressBarFill.style.width = '100%';
    progressText.textContent = 'Upload complete!';

    // Show success
    showToast(`File uploaded successfully: ${result.filename}`, 'success');

    // Wait a bit for user to see success
    setTimeout(() => {
      clearSelectedFile();
      loadRecentUploads();
    }, 1500);

  } catch (error) {
    clearInterval(progressInterval);
    showToast(`Upload failed: ${error.message}`, 'error');

    uploadBtn.disabled = false;
    uploadBtn.innerHTML = '<span>🚀</span><span>Upload to S3</span>';
    uploadProgress.classList.add('hidden');
  }
}

/**
 * Load recent uploads
 */
async function loadRecentUploads() {
  refreshListBtn.innerHTML = '<span class="loading"></span>';
  refreshListBtn.disabled = true;

  try {
    const data = await apiClient.getArtifacts({ limit: 10 });

    if (data.artifacts && data.artifacts.length > 0) {
      renderRecentUploads(data.artifacts);
    } else {
      recentUploadsContainer.innerHTML = `
        <div class="empty-state">
          <div class="empty-state-icon">📦</div>
          <div class="empty-state-title">No artifacts yet</div>
          <div class="empty-state-text">Upload your first artifact to get started</div>
        </div>
      `;
    }
  } catch (error) {
    showToast(`Failed to load recent uploads: ${error.message}`, 'error');
  } finally {
    refreshListBtn.innerHTML = '🔄 Refresh';
    refreshListBtn.disabled = false;
  }
}

/**
 * Render recent uploads list
 */
function renderRecentUploads(artifacts) {
  recentUploadsContainer.innerHTML = artifacts.map(artifact => `
    <div class="file-item mb-sm">
      <div class="file-info">
        <div class="file-icon">📄</div>
        <div class="file-details">
          <div class="file-name">${escapeHtml(artifact.filename)}</div>
          <div class="file-meta">
            ${formatFileSize(artifact.size)} • ${formatRelativeTime(artifact.uploaded_at)}
          </div>
          ${artifact.tags ? `<div class="file-meta" style="margin-top: 4px;">🏷️ ${escapeHtml(artifact.tags)}</div>` : ''}
        </div>
      </div>
      <div style="display: flex; gap: 8px;">
        <button class="btn btn-ghost btn-sm" onclick="copyArtifactUrl('${escapeHtml(artifact.presigned_url)}')">
          📋 Copy URL
        </button>
        <a href="${escapeHtml(artifact.presigned_url)}" target="_blank" class="btn btn-secondary btn-sm">
          👁️ View
        </a>
      </div>
    </div>
  `).join('');
  
  // Populate verification dropdown
  populateVerificationDropdown(artifacts);
}

/**
 * Populate verification artifact dropdown
 */
function populateVerificationDropdown(artifacts) {
  const select = document.getElementById('verify-artifact-select');
  if (!select) return;
  
  select.innerHTML = '<option value="">-- Select an uploaded artifact --</option>';
  
  artifacts.forEach(artifact => {
    const option = document.createElement('option');
    option.value = artifact.s3_key;
    option.textContent = `${artifact.filename} (${formatFileSize(artifact.size)})`;
    option.dataset.filename = artifact.filename;
    select.appendChild(option);
  });
}

/**
 * Copy artifact URL to clipboard
 */
function copyArtifactUrl(url) {
  copyToClipboard(url);
}

/**
 * Trigger production verification
 */
async function triggerVerification() {
  const select = document.getElementById('verify-artifact-select');
  const projectNameInput = document.getElementById('verify-project-name');
  const verifyBtn = document.getElementById('verify-btn');
  const statusDiv = document.getElementById('verify-status');
  
  const s3Key = select.value;
  const projectName = projectNameInput.value.trim();
  
  if (!s3Key) {
    showNotification('Please select an artifact', 'error');
    return;
  }
  
  if (!projectName) {
    showNotification('Please enter a project name', 'error');
    return;
  }
  
  verifyBtn.disabled = true;
  verifyBtn.innerHTML = '<span class="loading"></span><span>Triggering...</span>';
  statusDiv.style.display = 'none';
  
  try {
    const formData = new FormData();
    formData.append('s3_key', s3Key);
    formData.append('project_name', projectName);
    
    const response = await fetch('/api/verify/trigger', {
      method: 'POST',
      body: formData
    });
    
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }
    
    const result = await response.json();
    
    statusDiv.style.display = 'block';
    statusDiv.className = 'alert alert-success';
    statusDiv.innerHTML = `
      <strong>✅ Verification Triggered!</strong><br>
      Task ID: ${result.task_id}<br>
      <a href="/progress.html?task_id=${result.task_id}" class="btn btn-primary btn-sm" style="margin-top: 8px;">
        View Progress →
      </a>
    `;
    
    showNotification('Verification workflow started', 'success');
    
    // Redirect after 2 seconds
    setTimeout(() => {
      window.location.href = `/progress.html?task_id=${result.task_id}`;
    }, 2000);
    
  } catch (error) {
    statusDiv.style.display = 'block';
    statusDiv.className = 'alert alert-error';
    statusDiv.innerHTML = `<strong>❌ Failed:</strong> ${error.message}`;
    showNotification('Verification trigger failed', 'error');
  } finally {
    verifyBtn.disabled = false;
    verifyBtn.innerHTML = '<span>✅</span><span>Verify Production Code</span>';
  }
}

// Initialize verification button
document.addEventListener('DOMContentLoaded', () => {
  const verifyBtn = document.getElementById('verify-btn');
  if (verifyBtn) {
    verifyBtn.addEventListener('click', triggerVerification);
  }
});

/**
 * Check system health and update status indicator
 */
async function checkSystemHealth() {
  try {
    const health = await apiClient.getHealth();
    const statusEl = document.getElementById('system-status');
    const indicator = document.querySelector('.nav-status .health-indicator');

    if (health.status === 'healthy') {
      statusEl.textContent = 'System Online';
      indicator.className = 'health-indicator healthy';
    } else {
      statusEl.textContent = 'System Degraded';
      indicator.className = 'health-indicator degraded';
    }
  } catch (error) {
    const statusEl = document.getElementById('system-status');
    const indicator = document.querySelector('.nav-status .health-indicator');
    statusEl.textContent = 'System Offline';
    indicator.className = 'health-indicator offline';
  }

  // Check again in 30 seconds
  setTimeout(checkSystemHealth, 30000);
}
