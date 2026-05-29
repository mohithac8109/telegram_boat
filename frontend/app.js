/**
 * Telegram Media Manager - Frontend Application
 */

const API_URL = '/api';
let currentPhone = null;
let currentJobId = null;
let statusCheckInterval = null;

// DOM Elements
const accountSelect = document.getElementById('accountSelect');
const loginBtn = document.getElementById('loginBtn');
const loginModal = document.getElementById('loginModal');
const closeModal = document.querySelector('.close');
const phoneInput = document.getElementById('phoneInput');
const sendOtpBtn = document.getElementById('sendOtpBtn');
const codeInput = document.getElementById('codeInput');
const passwordInput = document.getElementById('passwordInput');
const passwordGroup = document.getElementById('passwordGroup');
const verifyBtn = document.getElementById('verifyBtn');
const backBtn = document.getElementById('backBtn');
const channelInput = document.getElementById('channelInput');
const startDownloadBtn = document.getElementById('startDownloadBtn');
const scanChannelBtn = document.getElementById('scanChannelBtn');
const downloadZipBtn = document.getElementById('downloadZipBtn');
const downloadSelectedBtn = document.getElementById('downloadSelectedBtn');
const downloadAllBtn = document.getElementById('downloadAllBtn');
const newDownloadBtn = document.getElementById('newDownloadBtn');
const selectAllCheckbox = document.getElementById('selectAllCheckbox');

// Sections
const accountSection = document.getElementById('accountSection');
const selectionSection = document.getElementById('selectionSection');
const selectionList = document.getElementById('selectionList');
const selectionInfo = document.getElementById('selectionInfo');

let selectionItems = [];
let currentChannel = null;
let currentDownloadType = '5';
const downloadSection = document.getElementById('downloadSection');
const progressSection = document.getElementById('progressSection');
const summarySection = document.getElementById('summarySection');

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    loadAccounts();
    attachEventListeners();
});

function attachEventListeners() {
    loginBtn.addEventListener('click', openLoginModal);
    closeModal.addEventListener('click', closeLoginModal);
    window.addEventListener('click', (e) => {
        if (e.target === loginModal) closeLoginModal();
    });

    sendOtpBtn.addEventListener('click', sendOtp);
    verifyBtn.addEventListener('click', verifyCode);
    backBtn.addEventListener('click', backToPhone);
    accountSelect.addEventListener('change', selectAccount);
    scanChannelBtn.addEventListener('click', scanChannel);
    if (downloadZipBtn) downloadZipBtn.addEventListener('click', downloadZipAfter);
    downloadSelectedBtn.addEventListener('click', downloadSelected);
    downloadAllBtn.addEventListener('click', downloadAll);
    if (selectAllCheckbox) selectAllCheckbox.addEventListener('change', toggleSelectAll);
    newDownloadBtn.addEventListener('click', () => {
        downloadSection.style.display = 'block';
        selectionSection.style.display = 'none';
        progressSection.style.display = 'none';
        summarySection.style.display = 'none';
        channelInput.value = '';
        selectionItems = [];
        currentChannel = null;
        if (selectAllCheckbox) {
            selectAllCheckbox.checked = false;
        }
    });
}

// Account Management
async function loadAccounts() {
    try {
        const response = await fetch(`${API_URL}/accounts`);
        const data = await response.json();

        accountSelect.innerHTML = '<option value="">-- Select Account --</option>';
        data.accounts.forEach(phone => {
            const option = document.createElement('option');
            option.value = phone;
            option.textContent = phone;
            accountSelect.appendChild(option);
        });
    } catch (error) {
        console.error('Error loading accounts:', error);
    }
}

function selectAccount() {
    currentPhone = accountSelect.value;
    if (currentPhone) {
        downloadSection.style.display = 'block';
        loadHistory();
    } else {
        downloadSection.style.display = 'none';
    }
}

// Login Functions
function openLoginModal() {
    loginModal.classList.remove('hidden');
    showStep('phoneStep');
    resetForm();
}

function closeLoginModal() {
    loginModal.classList.add('hidden');
}

function showStep(stepId) {
    document.querySelectorAll('.step').forEach(s => s.classList.add('hidden'));
    document.getElementById(stepId).classList.remove('hidden');
}

function resetForm() {
    phoneInput.value = '';
    codeInput.value = '';
    passwordInput.value = '';
    passwordGroup.classList.add('hidden');
    document.getElementById('errorMsg').classList.add('hidden');
    document.getElementById('errorMsg').textContent = '';
}

async function sendOtp() {
    const phone = phoneInput.value.trim();
    if (!phone) {
        showError('Please enter a phone number');
        return;
    }

    try {
        sendOtpBtn.disabled = true;
        sendOtpBtn.textContent = 'Sending...';

        const response = await fetch(`${API_URL}/login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ phone })
        });

        const data = await response.json();

        if (response.ok) {
            currentPhone = phone;
            showStep('otpStep');
        } else {
            showError(data.detail || 'Failed to send OTP');
        }
    } catch (error) {
        showError('Network error: ' + error.message);
    } finally {
        sendOtpBtn.disabled = false;
        sendOtpBtn.textContent = 'Send OTP';
    }
}

async function verifyCode() {
    const code = codeInput.value.trim();
    const password = passwordInput.value.trim();

    if (!code) {
        showError('Please enter the verification code');
        return;
    }

    try {
        verifyBtn.disabled = true;
        verifyBtn.textContent = 'Verifying...';

        const payload = {
            phone: currentPhone,
            code: code,
        };

        if (password) {
            payload.password = password;
        }

        const response = await fetch(`${API_URL}/login/verify`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        const data = await response.json();

        if (response.ok && data.success) {
            document.getElementById('successMsg').textContent =
                `Welcome, ${data.user.first_name}!`;
            showStep('successStep');
        } else if (data.requires_password) {
            passwordGroup.classList.remove('hidden');
            showError('This account requires a 2FA password. Please enter it and verify again.');
        } else {
            showError(data.detail || 'Verification failed');
        }
    } catch (error) {
        showError('Network error: ' + error.message);
    } finally {
        verifyBtn.disabled = false;
        verifyBtn.textContent = 'Verify';
    }
}

function backToPhone() {
    showStep('phoneStep');
}

document.getElementById('closeLoginBtn').addEventListener('click', () => {
    closeLoginModal();
    loadAccounts();
});

function showError(message) {
    const errorDiv = document.getElementById('errorMsg');
    errorDiv.textContent = message;
    errorDiv.classList.remove('hidden');
}

// Download Functions
async function startDownload(messageIds = null) {
    const channel = channelInput.value.trim();
    const downloadType = document.querySelector('input[name="downloadType"]:checked').value;

    if (!channel) {
        alert('Please enter a channel name or link');
        return;
    }

    try {
        if (startDownloadBtn) {
            startDownloadBtn.disabled = true;
            startDownloadBtn.textContent = 'Starting...';
        }
        downloadSelectedBtn.disabled = true;
        downloadAllBtn.disabled = true;
        if (downloadZipBtn) downloadZipBtn.disabled = true;

        const payload = {
            phone: currentPhone,
            channel: channel,
            download_type: downloadType,
        };
        if (Array.isArray(messageIds)) {
            payload.message_ids = messageIds;
        }

        const response = await fetch(`${API_URL}/download`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        const data = await response.json();

        if (response.ok) {
            currentJobId = data.job_id;
            downloadSection.style.display = 'none';
            selectionSection.style.display = 'none';
            progressSection.style.display = 'block';
            summarySection.style.display = 'none';
            pollDownloadStatus();
        } else {
            alert(data.detail || 'Failed to start download');
        }
    } catch (error) {
        alert('Error: ' + error.message);
    } finally {
        if (startDownloadBtn) {
            startDownloadBtn.disabled = false;
            startDownloadBtn.textContent = 'Start Download';
        }
        downloadSelectedBtn.disabled = false;
        downloadAllBtn.disabled = false;
        if (downloadZipBtn) downloadZipBtn.disabled = false;
    }
}

async function scanChannel() {
    const channel = channelInput.value.trim();
    const downloadType = document.querySelector('input[name="downloadType"]:checked').value;

    if (!channel) {
        alert('Please enter a channel name or link');
        return;
    }

    if (!currentPhone) {
        alert('Please select an account first');
        return;
    }

    scanChannelBtn.disabled = true;
    scanChannelBtn.textContent = 'Scanning...';
    currentChannel = channel;
    currentDownloadType = downloadType;
    downloadSection.style.display = 'none';
    selectionSection.style.display = 'block';
    selectionInfo.textContent = 'Scanning channel. This may take a moment...';
    selectionList.innerHTML = '';
    selectionItems = [];
    if (selectAllCheckbox) {
        selectAllCheckbox.checked = false;
    }

    try {
        const response = await fetch(`${API_URL}/channel/media?phone=${encodeURIComponent(currentPhone)}&channel=${encodeURIComponent(channel)}&download_type=${encodeURIComponent(downloadType)}`);
        const data = await response.json();

        if (response.ok && data.success) {
            selectionItems = data.items;
            if (selectionItems.length === 0) {
                selectionInfo.textContent = 'No matching media found in this channel.';
                if (selectAllCheckbox) {
                    selectAllCheckbox.checked = false;
                }
                return;
            }
            renderSelectionList(selectionItems);
            selectionInfo.textContent = `Found ${selectionItems.length} items. Select files to download or download all.`;
        } else {
            selectionInfo.textContent = data.detail || 'Failed to scan channel.';
            downloadSection.style.display = 'block';
            selectionSection.style.display = 'none';
        }
    } catch (error) {
        selectionInfo.textContent = 'Error scanning channel: ' + error.message;
        downloadSection.style.display = 'block';
        selectionSection.style.display = 'none';
    } finally {
        scanChannelBtn.disabled = false;
        scanChannelBtn.textContent = 'Scan Channel';
    }
}

function renderSelectionList(items) {
    if (!items.length) {
        selectionList.innerHTML = '<p>No media items found.</p>';
        return;
    }

    const typeLabel = (type) => {
        switch (type) {
            case 'video': return '🎥 Video';
            case 'photo': return '📷 Photo';
            case 'document': return '📄 Document';
            case 'audio': return '🎵 Audio';
            default: return type ? type.toUpperCase() : 'FILE';
        }
    };

    selectionList.innerHTML = items.map(item => `
        <label class="selection-item">
            <input type="checkbox" class="selection-checkbox" value="${item.id}" checked>
            <div class="selection-details">
                <span class="selection-title">${typeLabel(item.type)} #${item.id}</span>
                <span class="selection-meta">${item.date || 'Unknown date'} · ${formatBytes(item.size)}${item.caption ? ' · ' + escapeHtml(item.caption) : ''}</span>
            </div>
        </label>
    `).join('');

    if (selectAllCheckbox) {
        selectAllCheckbox.checked = true;
    }
}

function toggleSelectAll() {
    const checked = Boolean(selectAllCheckbox && selectAllCheckbox.checked);
    document.querySelectorAll('.selection-checkbox').forEach(checkbox => {
        checkbox.checked = checked;
    });
}

function downloadSelected() {
    const checked = Array.from(document.querySelectorAll('.selection-checkbox:checked'));
    if (!checked.length) {
        alert('Please select at least one item to download.');
        return;
    }

    const ids = checked.map(input => Number(input.value));
    startDownload(ids);
}

function downloadAll() {
    if (!selectionItems.length) {
        alert('No scanned items to download. Please scan the channel first.');
        return;
    }

    const allIds = selectionItems.map(item => item.id);
    startDownload(allIds);
}

function formatBytes(bytes) {
    if (bytes === 0) return '0 B';
    const units = ['B', 'KB', 'MB', 'GB', 'TB'];
    const index = Math.floor(Math.log(bytes) / Math.log(1024));
    return `${(bytes / Math.pow(1024, index)).toFixed(2)} ${units[index]}`;
}

function escapeHtml(text) {
    return text
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
}

function triggerZipDownload(channel, buttonElement) {
    const normalizedChannel = (channel || '').trim();

    if (!normalizedChannel) {
        alert('Please enter a channel name or link');
        return;
    }

    if (!currentPhone) {
        alert('Please select an account first');
        return;
    }

    if (buttonElement) {
        buttonElement.disabled = true;
        buttonElement.textContent = 'Preparing ZIP...';
    }

    const zipUrl = `${API_URL}/download/zip?phone=${encodeURIComponent(currentPhone)}&channel=${encodeURIComponent(normalizedChannel)}`;
    window.location.href = zipUrl;

    setTimeout(() => {
        if (buttonElement) {
            buttonElement.disabled = false;
            buttonElement.textContent = 'Download ZIP';
        }
    }, 1000);
}

function downloadZip() {
    triggerZipDownload(channelInput.value, downloadZipBtn);
}

function downloadZipAfter() {
    triggerZipDownload(currentChannel || channelInput.value, downloadZipBtn);
}

async function loadHistory() {
    if (!currentPhone) return;

    try {
        const response = await fetch(`/api/history/${encodeURIComponent(currentPhone)}`);
        const data = await response.json();
        const container = document.getElementById('historyList');
        container.innerHTML = '';

        if (!data || !data.channels || data.channels.length === 0) {
            container.innerHTML = '<p class="hint">No downloads found for this account.</p>';
            return;
        }

        data.channels.forEach(channel => {
            container.innerHTML += `
                <div class="history-card">
                    <h4>${channel.name}</h4>
                    <p>${channel.files} files</p>
                    <p>${channel.size_mb} MB</p>
                </div>
            `;
        });
    } catch (error) {
        console.error('Failed to load history', error);
    }
}

async function pollDownloadStatus() {
    if (!currentJobId) return;

    try {
        const response = await fetch(`${API_URL}/download/status/${currentJobId}`);
        
        // Handle old job IDs (404)
        if (response.status === 404) {
            localStorage.removeItem("currentJobId");
            currentJobId = null;
            console.log("Job ID not found - clearing from storage");
            return;
        }

        const data = await response.json();

        if (data.status === 'scanning') {
            document.getElementById('statusMsg').textContent = 'Scanning channel...';
        } else if (data.status === 'downloading') {
            updateProgress(data.progress);
        } else if (data.status === 'completed') {
            completeDownload(data.stats);
            return;
        } else if (data.status === 'failed') {
            alert('Download failed: ' + (data.error || 'Unknown error'));
            progressSection.style.display = 'none';
            downloadSection.style.display = 'block';
            return;
        }

        statusCheckInterval = setTimeout(pollDownloadStatus, 1000);
    } catch (error) {
        console.error('Error polling status:', error);
        statusCheckInterval = setTimeout(pollDownloadStatus, 2000);
    }
}

function updateProgress(progress) {
    if (!progress) return;

    document.getElementById('progressPercent').textContent =
        progress.percent.toFixed(1) + '%';
    document.getElementById('progressFill').style.width =
        progress.percent + '%';

    document.getElementById('speedStat').textContent =
        progress.speed_mbps.toFixed(2) + ' MB/s';
    document.getElementById('etaStat').textContent = progress.eta;
    document.getElementById('sizeStat').textContent =
        progress.current_mb.toFixed(2) + ' / ' + progress.total_mb.toFixed(2) + ' MB';

    document.getElementById('statusMsg').textContent = 'Downloading...';
    const currentItemMsg = document.getElementById('currentItemMsg');
    if (currentItemMsg) {
        const parts = [];
        if (progress.current_item_label) parts.push(progress.current_item_label);
        if (progress.current_item_caption) parts.push(progress.current_item_caption);
        if (progress.item_index && progress.total_items) {
            parts.push(`Item ${progress.item_index} of ${progress.total_items}`);
        }
        currentItemMsg.textContent = parts.length ? parts.join(' · ') : 'Downloading current file...';
    }
}

function completeDownload(stats) {
    if (statusCheckInterval) clearTimeout(statusCheckInterval);

    progressSection.style.display = 'none';
    summarySection.style.display = 'block';

    document.getElementById('totalFiles').textContent = stats.downloaded_count;
    document.getElementById('videoCount').textContent = stats.video_count;
    document.getElementById('photoCount').textContent = stats.photo_count;
    document.getElementById('docCount').textContent = stats.document_count;
    document.getElementById('audioCount').textContent = stats.audio_count;
    document.getElementById('totalSize').textContent = stats.total_size_gb.toFixed(2) + ' GB';
    document.getElementById('timeTaken').textContent = stats.elapsed_time;
    document.getElementById('avgSpeed').textContent = stats.avg_speed_mbps.toFixed(2) + ' MB/s';

    document.getElementById('downloadPath').innerHTML =
        `<strong>Saved To:</strong> ${stats.channel_folder}`;

    if (downloadZipBtn) {
        downloadZipBtn.disabled = false;
        downloadZipBtn.textContent = 'Download ZIP';
        downloadZipBtn.style.display = 'block';
    }

    const currentItemMsg = document.getElementById('currentItemMsg');
    if (currentItemMsg) {
        currentItemMsg.textContent = 'Download completed.';
    }

    // refresh history for the selected account
    loadHistory();
}
