// Shared Two-Factor Authentication helper injected into every dashboard.
// Automatically renders a 2FA button inside the top navbar (or as a floating
// button if no navbar is found) and provides the modal needed to enable or
// disable 2FA using the backend /api/two-factor endpoints.

(function () {
    const API_BASE = window.TWO_FACTOR_API_BASE || '/api/v1';
    const selectors = {
        button: 'twoFactorBtn',
        modal: 'twoFactorModal',
        step1: 'twoFactorStep1',
        step2: 'twoFactorStep2',
        step3: 'twoFactorStep3',
        loading: 'twoFactorLoading',
        qr: 'twoFactorQR',
        codeInput: 'twoFactorCode',
        backupCodes: 'twoFactorBackupCodes'
    };

    function authHeaders() {
        const token = localStorage.getItem('access_token');
        return token
            ? { 'Authorization': `Bearer ${token}` }
            : {};
    }

    async function request(path, options = {}) {
        const response = await fetch(`${API_BASE}${path}`, {
            method: 'GET',
            ...options,
            headers: {
                'Content-Type': 'application/json',
                ...authHeaders(),
                ...(options.headers || {})
            }
        });
        const data = await response.json().catch(() => ({}));
        return { response, data };
    }

    async function checkStatus() {
        try {
            const { response, data } = await request('/two-factor/status');
            if (response.ok) {
                return data;
            }
        } catch (error) {
            console.warn('2FA status check failed', error);
        }
        return { enabled: false };
    }

    async function startSetup() {
        return request('/two-factor/setup', { method: 'POST' });
    }

    async function enableTwoFactor(token) {
        return request('/two-factor/enable', {
            method: 'POST',
            body: JSON.stringify({ token })
        });
    }

    async function disableTwoFactor(payload) {
        return request('/two-factor/disable', {
            method: 'POST',
            body: JSON.stringify(payload)
        });
    }

    function ensureStyles() {
        if (document.getElementById('twoFactorStyles')) return;
        const style = document.createElement('style');
        style.id = 'twoFactorStyles';
        style.textContent = `
            .twofa-btn {
                background: rgba(255,255,255,0.2);
                color: #fff;
                border: 1px solid rgba(255,255,255,0.7);
                padding: 8px 16px;
                border-radius: 5px;
                cursor: pointer;
                font-size: 14px;
                margin-left: 10px;
            }
            .twofa-btn.twofa-enabled {
                background: rgba(76, 175, 80, 0.3);
                border-color: #4caf50;
            }
            #${selectors.modal} {
                display: none;
                position: fixed;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                background: rgba(0,0,0,0.5);
                z-index: 10000;
                align-items: center;
                justify-content: center;
            }
            #${selectors.modal}.visible {
                display: flex;
            }
            #${selectors.modal} .tf-container {
                background: #fff;
                padding: 30px;
                border-radius: 12px;
                max-width: 520px;
                width: 90%;
                max-height: 80vh;
                overflow-y: auto;
            }
            #${selectors.modal} button {
                width: 100%;
                padding: 12px;
                margin-top: 10px;
                border: none;
                border-radius: 6px;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: #fff;
                cursor: pointer;
            }
            @keyframes spin {
                from { transform: rotate(0deg); }
                to { transform: rotate(360deg); }
            }
        `;
        document.head.appendChild(style);
    }

    function ensureModal() {
        if (document.getElementById(selectors.modal)) return;
        const wrapper = document.createElement('div');
        wrapper.id = selectors.modal;
        wrapper.innerHTML = `
            <div class="tf-container">
                <div id="${selectors.step1}">
                    <h3>Two-Factor Authentication</h3>
                    <p style="margin: 15px 0;">Secure your account with a second factor.</p>
                    <button id="twoFactorStartBtn">Enable 2FA</button>
                    <button id="twoFactorCancelBtn" style="background:#ccc;color:#333;">Cancel</button>
                </div>
                <div id="${selectors.loading}" style="display:none;text-align:center;padding:40px;">
                    <div style="border:4px solid #f3f3f3;border-top:4px solid #667eea;border-radius:50%;width:40px;height:40px;animation:spin 1s linear infinite;margin:0 auto;"></div>
                    <p style="margin-top:15px;">Processing...</p>
                </div>
                <div id="${selectors.step2}" style="display:none;">
                    <div id="${selectors.qr}" style="text-align:center;"></div>
                    <label>Enter 6-digit code from your authenticator app:</label>
                    <input type="text" id="${selectors.codeInput}" maxlength="6" pattern="[0-9]{6}" style="width:100%;padding:12px;font-size:18px;text-align:center;letter-spacing:5px;margin:10px 0;">
                    <button id="twoFactorVerifyBtn">Verify & Enable</button>
                </div>
                <div id="${selectors.step3}" style="display:none;">
                    <div id="${selectors.backupCodes}"></div>
                    <button id="twoFactorCloseBtn">Close</button>
                </div>
            </div>
        `;
        wrapper.addEventListener('click', (e) => {
            if (e.target === wrapper) {
                hideModal();
            }
        });
        document.body.appendChild(wrapper);

        document.getElementById('twoFactorStartBtn').addEventListener('click', handleEnable2FA);
        document.getElementById('twoFactorCancelBtn').addEventListener('click', hideModal);
        document.getElementById('twoFactorVerifyBtn').addEventListener('click', handleVerify2FA);
        document.getElementById('twoFactorCloseBtn').addEventListener('click', hideModal);
    }

    function ensureButton() {
        if (document.getElementById(selectors.button)) return;
        const btn = document.createElement('button');
        btn.id = selectors.button;
        btn.className = 'twofa-btn';
        btn.textContent = '🔓 2FA: OFF';
        btn.type = 'button';
        btn.addEventListener('click', openTwoFactorManagement);

        const navbarActions = document.querySelector('.navbar .navbar-actions');
        const navbar = document.querySelector('.navbar');
        if (navbarActions) {
            navbarActions.appendChild(btn);
        } else if (navbar) {
            navbar.appendChild(btn);
        } else {
            btn.style.position = 'fixed';
            btn.style.bottom = '20px';
            btn.style.right = '20px';
            document.body.appendChild(btn);
        }
    }

    function ensureUI() {
        ensureStyles();
        ensureButton();
        ensureModal();
    }

    function showStep(step) {
        ['step1', 'step2', 'step3', 'loading'].forEach((name) => {
            const el = document.getElementById(selectors[name]);
            if (!el) return;
            el.style.display = (name === step) ? 'block' : 'none';
        });
    }

    function showModal() {
        ensureUI();
        const modal = document.getElementById(selectors.modal);
        modal.classList.add('visible');
    }

    function hideModal() {
        const modal = document.getElementById(selectors.modal);
        if (modal) {
            modal.classList.remove('visible');
        }
        showStep('step1');
        const codeInput = document.getElementById(selectors.codeInput);
        if (codeInput) codeInput.value = '';
    }

    async function initButton() {
        const btn = document.getElementById(selectors.button);
        if (!btn) return;
        btn.disabled = true;
        btn.textContent = 'Checking 2FA…';
        const status = await checkStatus();
        if (status.enabled) {
            btn.textContent = '🔒 2FA: ON';
            btn.classList.add('twofa-enabled');
        } else {
            btn.textContent = '🔓 2FA: OFF';
            btn.classList.remove('twofa-enabled');
        }
        btn.disabled = false;
        if (!btn.dataset.bound) {
            btn.addEventListener('click', openTwoFactorManagement);
            btn.dataset.bound = 'true';
        }
    }

    async function openTwoFactorManagement() {
        ensureUI();
        const status = await checkStatus();
        if (status.enabled) {
            const code = prompt('Enter your 6-digit authenticator code (or a backup code) to disable 2FA:');
            if (!code) return;
            showStep('loading');
            showModal();
            const payload = /^\d{6}$/.test(code.trim())
                ? { token: code.trim() }
                : { backup_code: code.trim().toUpperCase() };
            const { response, data } = await disableTwoFactor(payload);
            hideModal();
            if (response.ok) {
                alert('2FA has been disabled.');
                await initButton();
            } else {
                alert(data.error || 'Failed to disable 2FA.');
            }
        } else {
            showStep('step1');
            showModal();
        }
    }

    async function handleEnable2FA() {
        showStep('loading');
        const { response, data } = await startSetup();
        if (!response.ok) {
            showStep('step1');
            alert(data.error || 'Failed to start 2FA setup.');
            return;
        }
        const qrContainer = document.getElementById(selectors.qr);
        if (qrContainer) {
            qrContainer.innerHTML = `
                <div style="text-align:center;">
                    <img src="${data.qr_code}" alt="QR Code" style="max-width:250px;margin:20px auto;" />
                    <p><strong>Manual key:</strong></p>
                    <code style="background:#f5f5f5;padding:8px;display:inline-block;">${data.secret_key}</code>
                    <p style="font-size:12px;color:#555;margin-top:10px;">Scan using Google Authenticator, Authy, or any TOTP app.</p>
                </div>
            `;
        }
        showStep('step2');
    }

    async function handleVerify2FA() {
        const input = document.getElementById(selectors.codeInput);
        if (!input || input.value.trim().length !== 6) {
            alert('Please enter a valid 6-digit code.');
            return;
        }
        showStep('loading');
        const { response, data } = await enableTwoFactor(input.value.trim());
        if (!response.ok) {
            showStep('step2');
            alert(data.error || 'Verification failed.');
            return;
        }
        const backupContainer = document.getElementById(selectors.backupCodes);
        if (backupContainer) {
            const codes = (data.backup_codes || []).map(code =>
                `<code style="display:block;background:#f5f5f5;padding:8px;margin:5px 0;">${code}</code>`
            ).join('');
            backupContainer.innerHTML = `
                <div style="text-align:center;">
                    <h3>✅ 2FA Enabled!</h3>
                    <p>Store these backup codes in a safe place (shown only once):</p>
                    <div style="max-width:320px;margin:0 auto;">${codes}</div>
                </div>
            `;
        }
        showStep('step3');
        await initButton();
    }

    async function handleDisable2FA() {
        ensureUI();
        const status = await checkStatus();
        if (!status.enabled) {
            alert('Two-factor authentication is not enabled.');
            return;
        }
        const code = prompt('Enter your 6-digit authenticator code (or backup code) to disable 2FA:');
        if (!code) return;
        showStep('loading');
        showModal();
        const payload = /^\d{6}$/.test(code.trim())
            ? { token: code.trim() }
            : { backup_code: code.trim().toUpperCase() };
        const { response, data } = await disableTwoFactor(payload);
        hideModal();
        if (response.ok) {
            alert('2FA has been disabled.');
            await initButton();
        } else {
            alert(data.error || 'Failed to disable 2FA.');
        }
    }

    document.addEventListener('DOMContentLoaded', () => {
        ensureUI();
        initButton();
    });

    // Expose helpers for legacy inline handlers (citizen dashboard, etc.)
    window.openTwoFactorManagement = openTwoFactorManagement;
    window.handleEnable2FA = handleEnable2FA;
    window.handleVerify2FA = handleVerify2FA;
    window.handleDisable2FA = handleDisable2FA;
    // Backwards-compatible object used by older dashboards
    window.TwoFactorAuth = {
        open: openTwoFactorManagement,
        showModal,
        hideModal,
        handleEnable2FA,
        handleVerify2FA,
        handleDisable2FA,
        init: initButton
    };
})();
