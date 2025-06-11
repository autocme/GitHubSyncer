// GitHub Sync Server JavaScript Functions

// Global variables
let authToken = null;

// Initialize on page load
document.addEventListener('DOMContentLoaded', function() {
    // Get CSRF token from meta tag or use session auth
    const csrfToken = document.querySelector('meta[name="csrf-token"]');
    if (csrfToken) {
        authToken = csrfToken.getAttribute('content');
    }
    
    // Initialize tooltips
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
});

// Utility Functions
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

function showToast(message, type = 'info') {
    const toastContainer = document.getElementById('toast-container') || createToastContainer();
    const toastId = 'toast-' + Date.now();
    
    const toastHtml = `
        <div id="${toastId}" class="toast align-items-center text-white bg-${type} border-0" role="alert">
            <div class="d-flex">
                <div class="toast-body">
                    ${message}
                </div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
            </div>
        </div>
    `;
    
    toastContainer.insertAdjacentHTML('beforeend', toastHtml);
    const toastElement = document.getElementById(toastId);
    const toast = new bootstrap.Toast(toastElement, { autohide: true, delay: 5000 });
    toast.show();
    
    // Remove toast element after it's hidden
    toastElement.addEventListener('hidden.bs.toast', () => {
        toastElement.remove();
    });
}

function createToastContainer() {
    const container = document.createElement('div');
    container.id = 'toast-container';
    container.className = 'toast-container position-fixed bottom-0 end-0 p-3';
    container.style.zIndex = '1055';
    document.body.appendChild(container);
    return container;
}

function copyToClipboard(text) {
    if (navigator.clipboard && window.isSecureContext) {
        navigator.clipboard.writeText(text).then(() => {
            showToast('Copied to clipboard!', 'success');
        }).catch(() => {
            fallbackCopyToClipboard(text);
        });
    } else {
        fallbackCopyToClipboard(text);
    }
}

function fallbackCopyToClipboard(text) {
    const textArea = document.createElement('textarea');
    textArea.value = text;
    textArea.style.position = 'fixed';
    textArea.style.left = '-999999px';
    textArea.style.top = '-999999px';
    document.body.appendChild(textArea);
    textArea.focus();
    textArea.select();
    
    try {
        document.execCommand('copy');
        showToast('Copied to clipboard!', 'success');
    } catch (err) {
        showToast('Failed to copy to clipboard', 'danger');
    }
    
    document.body.removeChild(textArea);
}

function copyWebhookUrl() {
    const webhookUrl = document.querySelector('input[readonly]').value;
    copyToClipboard(webhookUrl);
}

function copySSHKey(keyId) {
    console.log('copySSHKey called with keyId:', keyId);
    // Find the input field for this SSH key
    const keyInput = document.querySelector(`#ssh-key-${keyId}`);
    console.log('Found input element:', keyInput);
    
    if (keyInput) {
        const fullKey = keyInput.dataset.fullKey;
        console.log('Full key length:', fullKey ? fullKey.length : 'undefined');
        if (fullKey) {
            copyToClipboard(fullKey);
        } else {
            showToast('SSH key data not found', 'danger');
        }
    } else {
        console.error('SSH key input element not found for ID:', keyId);
        showToast('Unable to find SSH key element', 'danger');
    }
}

function viewPublicKey(keyId, keyName, publicKey) {
    console.log('viewPublicKey called:', { keyId, keyName, publicKeyLength: publicKey ? publicKey.length : 'undefined' });
    
    // Create modal to display full public key
    const modalId = 'viewKeyModal';
    let modal = document.getElementById(modalId);
    
    if (!modal) {
        console.log('Creating new modal');
        const modalHtml = `
            <div class="modal fade" id="${modalId}" tabindex="-1">
                <div class="modal-dialog modal-lg">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h5 class="modal-title">
                                <i class="fas fa-eye me-2"></i>
                                SSH Public Key
                            </h5>
                            <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                        </div>
                        <div class="modal-body">
                            <h6 id="keyModalName"></h6>
                            <div class="input-group mb-3">
                                <textarea class="form-control" id="keyModalContent" rows="4" readonly></textarea>
                                <button class="btn btn-outline-secondary" type="button" onclick="copyFromModal()">
                                    <i class="fas fa-copy"></i> Copy
                                </button>
                            </div>
                            <div class="alert alert-info">
                                <i class="fas fa-info-circle me-2"></i>
                                <strong>Usage:</strong> Copy this public key and add it to your GitHub account's SSH keys.
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `;
        document.body.insertAdjacentHTML('beforeend', modalHtml);
        modal = document.getElementById(modalId);
    }
    
    // Update modal content
    const nameElement = document.getElementById('keyModalName');
    const contentElement = document.getElementById('keyModalContent');
    
    if (nameElement && contentElement) {
        nameElement.textContent = keyName;
        contentElement.value = publicKey;
        
        // Show modal
        try {
            const bsModal = new bootstrap.Modal(modal);
            bsModal.show();
            console.log('Modal shown successfully');
        } catch (error) {
            console.error('Error showing modal:', error);
            showToast('Error displaying SSH key', 'danger');
        }
    } else {
        console.error('Modal elements not found');
        showToast('Error creating modal', 'danger');
    }
}

function copyFromModal() {
    const textarea = document.getElementById('keyModalContent');
    copyToClipboard(textarea.value);
}

// API Functions
async function apiRequest(url, options = {}) {
    const defaultOptions = {
        method: 'GET',
        credentials: 'include',
        headers: {
            'Content-Type': 'application/json'
        }
    };
    
    // Only add Authorization header if we have a token
    if (authToken) {
        defaultOptions.headers['Authorization'] = `Bearer ${authToken}`;
    }
    
    const finalOptions = {
        ...defaultOptions,
        ...options,
        headers: {
            ...defaultOptions.headers,
            ...options.headers
        }
    };
    
    try {
        const response = await fetch(url, finalOptions);
        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.detail || `HTTP error! status: ${response.status}`);
        }
        
        return data;
    } catch (error) {
        console.error('API request failed:', error);
        throw error;
    }
}

// Dashboard Functions
async function syncAllRepos() {
    try {
        showToast('Syncing all repositories and restarting containers...', 'info');
        const response = await apiRequest('/api/repositories');
        const repositories = response;
        
        let successCount = 0;
        let errorCount = 0;
        let totalContainersRestarted = 0;
        
        for (const repo of repositories) {
            try {
                const syncResponse = await apiRequest(`/api/repositories/${repo.id}/sync`, { method: 'POST' });
                successCount++;
                
                if (syncResponse.containers_restarted) {
                    const restarted = syncResponse.containers_restarted.filter(c => c.success).length;
                    totalContainersRestarted += restarted;
                }
            } catch (error) {
                errorCount++;
                console.error(`Failed to sync repository ${repo.name}:`, error);
            }
        }
        
        if (errorCount === 0) {
            showToast(`Successfully synced ${successCount} repositories. ${totalContainersRestarted} containers restarted.`, 'success');
        } else {
            showToast(`Synced ${successCount} repositories, ${errorCount} failed. ${totalContainersRestarted} containers restarted.`, 'warning');
        }
        
        // Refresh page after a delay
        setTimeout(() => location.reload(), 2000);
        
    } catch (error) {
        showToast('Failed to sync repositories: ' + error.message, 'danger');
    }
}

async function discoverContainers() {
    try {
        showToast('Discovering containers...', 'info');
        const response = await apiRequest('/api/containers/discover', { method: 'POST' });
        showToast(response.message, 'success');
        
        // Refresh page after a delay
        setTimeout(() => location.reload(), 1500);
        
    } catch (error) {
        showToast('Failed to discover containers: ' + error.message, 'danger');
    }
}

// Utility function to extract repository name from URL
function extractRepoNameFromUrl(url) {
    try {
        // Remove .git suffix if present
        let cleanUrl = url.replace(/\.git$/, '');
        
        // Extract from various URL formats
        let match;
        
        // GitHub format: https://github.com/user/repo
        match = cleanUrl.match(/github\.com[\/:]([^\/]+)\/([^\/]+)/);
        if (match) return match[2];
        
        // GitLab format: https://gitlab.com/user/repo
        match = cleanUrl.match(/gitlab\.com[\/:]([^\/]+)\/([^\/]+)/);
        if (match) return match[2];
        
        // Bitbucket format: https://bitbucket.org/user/repo
        match = cleanUrl.match(/bitbucket\.org[\/:]([^\/]+)\/([^\/]+)/);
        if (match) return match[2];
        
        // Generic Git SSH format: git@host:user/repo
        match = cleanUrl.match(/git@[^:]+:([^\/]+)\/([^\/]+)/);
        if (match) return match[2];
        
        // Generic HTTPS format: https://host/user/repo
        match = cleanUrl.match(/https?:\/\/[^\/]+\/(?:[^\/]+\/)*([^\/]+)$/);
        if (match) return match[1];
        
        // Fallback: get last part of path
        const parts = cleanUrl.split('/');
        return parts[parts.length - 1] || '';
        
    } catch (error) {
        return '';
    }
}

// Auto-fill repository name when URL changes
function onRepoUrlChange() {
    const urlInput = document.getElementById('repoUrl');
    const nameInput = document.getElementById('repoName');
    
    if (urlInput && nameInput && urlInput.value && !nameInput.value) {
        const extractedName = extractRepoNameFromUrl(urlInput.value);
        if (extractedName) {
            nameInput.value = extractedName;
        }
    }
}

// Repository Functions
async function addRepository() {
    const name = document.getElementById('repoName').value.trim();
    const url = document.getElementById('repoUrl').value.trim();
    const branch = document.getElementById('repoBranch').value.trim() || 'main';
    
    if (!url) {
        showToast('Please enter a repository URL', 'warning');
        return;
    }
    
    // Auto-generate name if not provided
    let finalName = name;
    if (!finalName) {
        finalName = extractRepoNameFromUrl(url);
        if (!finalName) {
            showToast('Please provide a repository name', 'warning');
            return;
        }
    }
    
    try {
        const response = await apiRequest('/api/repositories', {
            method: 'POST',
            body: JSON.stringify({ name: finalName, url, branch })
        });
        
        showToast('Repository added successfully', 'success');
        
        // Close modal and refresh page
        const modal = bootstrap.Modal.getInstance(document.getElementById('addRepoModal'));
        modal.hide();
        
        setTimeout(() => location.reload(), 1000);
        
    } catch (error) {
        showToast('Failed to add repository: ' + error.message, 'danger');
    }
}

async function editRepository(repoId) {
    try {
        const response = await apiRequest(`/api/repositories`);
        const repository = response.find(repo => repo.id === repoId);
        
        if (!repository) {
            showToast('Repository not found', 'danger');
            return;
        }
        
        // Populate edit form
        document.getElementById('editRepoId').value = repository.id;
        document.getElementById('editRepoName').value = repository.name;
        document.getElementById('editRepoUrl').value = repository.url;
        document.getElementById('editRepoBranch').value = repository.branch;
        document.getElementById('editRepoLocalPath').value = repository.local_path || 'Auto-detected';
        document.getElementById('editRepoActive').checked = repository.is_active;
        
        // Show modal
        const modal = new bootstrap.Modal(document.getElementById('editRepoModal'));
        modal.show();
        
    } catch (error) {
        showToast('Failed to load repository details: ' + error.message, 'danger');
    }
}

async function updateRepository() {
    const repoId = document.getElementById('editRepoId').value;
    const name = document.getElementById('editRepoName').value.trim();
    const url = document.getElementById('editRepoUrl').value.trim();
    const branch = document.getElementById('editRepoBranch').value.trim();
    const isActive = document.getElementById('editRepoActive').checked;
    
    if (!name || !url || !branch) {
        showToast('Please fill in all required fields', 'warning');
        return;
    }
    
    try {
        await apiRequest(`/api/v1/repositories/${repoId}`, {
            method: 'PUT',
            body: JSON.stringify({ name, url, branch, is_active: isActive })
        });
        
        showToast('Repository updated successfully', 'success');
        
        // Close modal and refresh page
        const modal = bootstrap.Modal.getInstance(document.getElementById('editRepoModal'));
        modal.hide();
        
        setTimeout(() => location.reload(), 1000);
        
    } catch (error) {
        showToast('Failed to update repository: ' + error.message, 'danger');
    }
}

async function deleteRepository(repoId, repoName) {
    if (!confirm(`Are you sure you want to delete repository "${repoName}"?`)) {
        return;
    }
    
    try {
        await apiRequest(`/api/repositories/${repoId}`, { method: 'DELETE' });
        showToast('Repository deleted successfully', 'success');
        
        setTimeout(() => location.reload(), 1000);
        
    } catch (error) {
        showToast('Failed to delete repository: ' + error.message, 'danger');
    }
}

async function syncRepository(repoId) {
    try {
        showToast('Syncing repository and restarting containers...', 'info');
        const response = await apiRequest(`/api/repositories/${repoId}/sync`, { method: 'POST' });
        
        if (response.success) {
            const containersRestarted = response.containers_restarted || [];
            const successCount = containersRestarted.filter(c => c.success).length;
            
            if (successCount > 0) {
                showToast(`Repository synced successfully. ${successCount} containers restarted.`, 'success');
            } else {
                showToast('Repository synced successfully. No containers found to restart.', 'success');
            }
        } else {
            showToast('Repository sync failed: ' + response.message, 'danger');
        }
        
        setTimeout(() => location.reload(), 2000);
        
    } catch (error) {
        showToast('Failed to sync repository: ' + error.message, 'danger');
    }
}

// Container Functions
async function restartContainer(containerId) {
    try {
        showToast('Restarting container...', 'info');
        const response = await apiRequest(`/api/containers/${containerId}/restart`, { method: 'POST' });
        showToast('Container restarted successfully', 'success');
        
        setTimeout(() => location.reload(), 2000);
        
    } catch (error) {
        showToast('Failed to restart container: ' + error.message, 'danger');
    }
}

async function viewContainerDetails(containerId) {
    try {
        // This would require an additional API endpoint to get container details
        showToast('Container details feature coming soon', 'info');
        
    } catch (error) {
        showToast('Failed to load container details: ' + error.message, 'danger');
    }
}

// Settings Functions
async function createApiKey() {
    const name = document.getElementById('apiKeyName').value.trim();
    
    if (!name) {
        showToast('Please enter a key name', 'warning');
        return;
    }
    
    try {
        const response = await apiRequest('/api/api-keys', {
            method: 'POST',
            body: JSON.stringify({ name })
        });
        
        // Show the generated API key
        document.getElementById('generatedApiKey').value = response.api_key;
        
        // Close add modal and show display modal
        const addModal = bootstrap.Modal.getInstance(document.getElementById('addApiKeyModal'));
        addModal.hide();
        
        const displayModal = new bootstrap.Modal(document.getElementById('apiKeyDisplayModal'));
        displayModal.show();
        
        // Clear form
        document.getElementById('addApiKeyForm').reset();
        
        showToast('API key created successfully', 'success');
        
    } catch (error) {
        showToast('Failed to create API key: ' + error.message, 'danger');
    }
}

async function revokeApiKey(keyId, keyName) {
    if (!confirm(`Are you sure you want to revoke API key "${keyName}"?`)) {
        return;
    }
    
    try {
        await apiRequest(`/api/api-keys/${keyId}`, { method: 'DELETE' });
        showToast('API key revoked successfully', 'success');
        
        setTimeout(() => location.reload(), 1000);
        
    } catch (error) {
        showToast('Failed to revoke API key: ' + error.message, 'danger');
    }
}

async function createGitKey() {
    const name = document.getElementById('gitKeyName').value.trim();
    
    if (!name) {
        showToast('Please enter a key name', 'warning');
        return;
    }
    
    try {
        showToast('Generating SSH key...', 'info');
        const response = await apiRequest('/api/git-keys', {
            method: 'POST',
            body: JSON.stringify({ name })
        });
        
        showToast('SSH key generated successfully', 'success');
        
        // Close modal and refresh page
        const modal = bootstrap.Modal.getInstance(document.getElementById('addGitKeyModal'));
        modal.hide();
        
        // Clear form
        document.getElementById('addGitKeyForm').reset();
        
        setTimeout(() => location.reload(), 1000);
        
    } catch (error) {
        showToast('Failed to generate SSH key: ' + error.message, 'danger');
    }
}

async function deleteGitKey(keyId, keyName) {
    if (!confirm(`Are you sure you want to delete SSH key "${keyName}"?`)) {
        return;
    }
    
    try {
        await apiRequest(`/api/git-keys/${keyId}`, { method: 'DELETE' });
        showToast('SSH key deleted successfully', 'success');
        
        setTimeout(() => location.reload(), 1000);
        
    } catch (error) {
        showToast('Failed to delete SSH key: ' + error.message, 'danger');
    }
}

function viewPublicKey(keyId, keyName, publicKey) {
    document.getElementById('keyName').textContent = keyName;
    document.getElementById('publicKeyContent').value = publicKey;
    
    const modal = new bootstrap.Modal(document.getElementById('publicKeyModal'));
    modal.show();
}

// Log Functions
function filterLogs() {
    const operationFilter = document.getElementById('operationFilter').value.toLowerCase();
    const statusFilter = document.getElementById('statusFilter').value.toLowerCase();
    const searchFilter = document.getElementById('searchFilter').value.toLowerCase();
    
    const tableRows = document.querySelectorAll('#logsTable tbody tr');
    
    tableRows.forEach(row => {
        const operation = row.cells[1].textContent.toLowerCase();
        const status = row.cells[2].textContent.toLowerCase();
        const message = row.cells[3].textContent.toLowerCase();
        
        const operationMatch = !operationFilter || operation.includes(operationFilter);
        const statusMatch = !statusFilter || status.includes(statusFilter);
        const searchMatch = !searchFilter || message.includes(searchFilter);
        
        if (operationMatch && statusMatch && searchMatch) {
            row.style.display = '';
        } else {
            row.style.display = 'none';
        }
    });
}

function clearFilters() {
    document.getElementById('operationFilter').value = '';
    document.getElementById('statusFilter').value = '';
    document.getElementById('searchFilter').value = '';
    filterLogs();
}

function refreshLogs() {
    location.reload();
}

async function clearLogs() {
    if (!confirm('Are you sure you want to clear all logs? This action cannot be undone.')) {
        return;
    }
    
    try {
        showToast('Clearing logs...', 'info');
        
        const response = await apiRequest('/api/v1/logs', {
            method: 'DELETE'
        });
        
        showToast(`Successfully cleared ${response.deleted_count} logs`, 'success');
        
        // Refresh the page to show the empty logs table
        setTimeout(() => location.reload(), 1000);
        
    } catch (error) {
        showToast('Failed to clear logs: ' + error.message, 'danger');
    }
}

async function viewLogDetails(logId) {
    try {
        const response = await apiRequest(`/api/logs`);
        const log = response.logs.find(l => l.id === logId);
        
        if (!log) {
            showToast('Log entry not found', 'danger');
            return;
        }
        
        // Parse details if it's a JSON string
        let details = null;
        try {
            details = typeof log.details === 'string' ? JSON.parse(log.details) : log.details;
        } catch (e) {
            details = log.details;
        }
        
        // Format log details content
        let content = `
            <div class="mb-3">
                <h6><i class="fas fa-clock me-2"></i>Timestamp</h6>
                <p class="text-muted">${new Date(log.created_at).toLocaleString()}</p>
            </div>
            
            <div class="mb-3">
                <h6><i class="fas fa-tag me-2"></i>Operation</h6>
                <span class="badge bg-secondary">${log.operation_type}</span>
            </div>
            
            <div class="mb-3">
                <h6><i class="fas fa-info-circle me-2"></i>Status</h6>
                <span class="badge ${log.status === 'success' ? 'bg-success' : log.status === 'error' ? 'bg-danger' : 'bg-warning'}">${log.status}</span>
            </div>
            
            <div class="mb-3">
                <h6><i class="fas fa-comment me-2"></i>Message</h6>
                <p>${log.message}</p>
            </div>
        `;
        
        // Add repository information if available
        if (log.repository) {
            content += `
                <div class="mb-3">
                    <h6><i class="fas fa-code-branch me-2"></i>Repository</h6>
                    <p>${log.repository.name}</p>
                </div>
            `;
        }
        
        // Add container information if available
        if (log.container_id) {
            content += `
                <div class="mb-3">
                    <h6><i class="fas fa-cube me-2"></i>Container</h6>
                    <p><code>${log.container_id}</code></p>
                </div>
            `;
        }
        
        // Add detailed error information if available
        if (details) {
            content += `
                <div class="mb-3">
                    <h6><i class="fas fa-exclamation-triangle me-2"></i>Detailed Information</h6>
                    <div class="card">
                        <div class="card-body">
            `;
            
            if (typeof details === 'object') {
                // Display structured error details
                Object.entries(details).forEach(([key, value]) => {
                    const formattedKey = key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
                    let formattedValue = value;
                    
                    if (typeof value === 'object') {
                        formattedValue = `<pre><code>${JSON.stringify(value, null, 2)}</code></pre>`;
                    } else if (key === 'timestamp') {
                        formattedValue = new Date(value).toLocaleString();
                    }
                    
                    content += `
                        <div class="mb-2">
                            <strong>${formattedKey}:</strong>
                            <div class="ms-3">${formattedValue}</div>
                        </div>
                    `;
                });
            } else {
                content += `<pre><code>${details}</code></pre>`;
            }
            
            content += `
                        </div>
                    </div>
                </div>
            `;
        }
        
        // Update modal content
        document.getElementById('logDetailsContent').innerHTML = content;
        
        // Show modal
        const modal = new bootstrap.Modal(document.getElementById('logDetailsModal'));
        modal.show();
        
    } catch (error) {
        showToast('Failed to load log details: ' + error.message, 'danger');
    }
}

// Pagination is now handled through URL parameters and server-side rendering

// Change Password Function
document.addEventListener('DOMContentLoaded', function() {
    const changePasswordForm = document.getElementById('changePasswordForm');
    if (changePasswordForm) {
        changePasswordForm.addEventListener('submit', async function(e) {
            e.preventDefault();
            
            const currentPassword = document.getElementById('current_password').value;
            const newPassword = document.getElementById('new_password').value;
            const confirmPassword = document.getElementById('confirm_password').value;
            
            if (newPassword !== confirmPassword) {
                showToast('New passwords do not match', 'warning');
                return;
            }
            
            if (newPassword.length < 6) {
                showToast('Password must be at least 6 characters long', 'warning');
                return;
            }
            
            try {
                showToast('This feature is not yet implemented', 'info');
                // TODO: Implement change password API endpoint
                
            } catch (error) {
                showToast('Failed to change password: ' + error.message, 'danger');
            }
        });
    }
});

// Auto-refresh functionality for dashboard
if (window.location.pathname === '/dashboard') {
    // Refresh dashboard every 30 seconds
    setInterval(() => {
        // Only refresh if user is still on the page and no modals are open
        if (document.visibilityState === 'visible' && !document.querySelector('.modal.show')) {
            location.reload();
        }
    }, 30000);
}

// Handle form submissions with Enter key
document.addEventListener('keydown', function(e) {
    if (e.key === 'Enter' && e.target.tagName === 'INPUT') {
        const form = e.target.closest('form');
        if (form) {
            const submitButton = form.querySelector('button[type="submit"], .btn-primary');
            if (submitButton && !submitButton.disabled) {
                e.preventDefault();
                submitButton.click();
            }
        }
    }
});

// Initialize JSON filter for containers template
window.fromJson = function(jsonString) {
    try {
        return JSON.parse(jsonString || '{}');
    } catch (e) {
        return {};
    }
};
