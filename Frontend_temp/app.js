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
const verifyBtn = document.getElementById('verifyBtn');
const backBtn = document.getElementById('backBtn');
const channelInput = document.getElementById('channelInput');
const startDownloadBtn = document.getElementById('startDownloadBtn');
const newDownloadBtn = document.getElementById('newDownloadBtn');

// Sections
const accountSection = document.getElementById('accountSection');
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
    startDownloadBtn.addEventListener('click', startDownload);
    newDownloadBtn.addEventListener('click', () => {
        downloadSection.style.display = 'block';
        progressSection.style.display = 'none';
        summarySection.style.display = 'none';
        channelInput.value = '';
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
    if (!code) {
        showError('Please enter the verification code');
        return;
    }

    try {
        verifyBtn.disabled = true;
        verifyBtn.textContent = 'Verifying...';

        const response = await fetch(`${API_URL}/login/verify`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                phone: currentPhone,
                code: code
            })
        });

        const data = await response.json();

        if (response.ok && data.success) {
            document.getElementById('successMsg').textContent =
                `Welcome, ${data.user.first_name}!`;
            showStep('successStep');
        } else if (data.requires_password) {
            showError('2FA password required (not yet supported)');
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
async function startDownload() {
    const channel = channelInput.value.trim();
    const downloadType = document.querySelector('input[name="downloadType"]:checked').value;

    if (!channel) {
        alert('Please enter a channel name or link');
        return;
    }

    try {
        startDownloadBtn.disabled = true;
        startDownloadBtn.textContent = 'Starting...';

        const response = await fetch(`${API_URL}/download`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                phone: currentPhone,
                channel: channel,
                download_type: downloadType
            })
        });

        const data = await response.json();

        if (response.ok) {
            currentJobId = data.job_id;
            downloadSection.style.display = 'none';
            progressSection.style.display = 'block';
            summarySection.style.display = 'none';
            pollDownloadStatus();
        } else {
            alert(data.detail || 'Failed to start download');
        }
    } catch (error) {
        alert('Error: ' + error.message);
    } finally {
        startDownloadBtn.disabled = false;
        startDownloadBtn.textContent = 'Start Download';
    }
}

async function pollDownloadStatus() {
    if (!currentJobId) return;

    try {
        const response = await fetch(`${API_URL}/download/status/${currentJobId}`);
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
}
