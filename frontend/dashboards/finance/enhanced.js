/**
 * Finance Officer Dashboard - Complete Implementation
 * View all payments, issue tax attestations, search taxpayers
 */

const API_BASE = '/api/v1';  // Use relative URL so frontend works behind proxy

function getToken() {
    return localStorage.getItem('access_token');
}

function getAuthHeader() {
    return {
        'Authorization': `Bearer ${getToken()}`,
        'Content-Type': 'application/json'
    };
}

// Section Navigation
function showSection(sectionId, el) {
    document.querySelectorAll('.section').forEach(el => el.style.display = 'none');
    document.querySelectorAll('.nav-link').forEach(x => x.classList.remove('active'));
    document.getElementById(sectionId).style.display = 'block';
    if (el) el.classList.add('active');

    if (sectionId === 'debtors') loadDebtors();
    else if (sectionId === 'revenue') loadRevenueReport();
    else if (sectionId === 'overview') loadOverview();
}

// Overview
async function loadOverview() {
    try {
        const [debtorsRes, revenueRes] = await Promise.all([
            fetch(`${API_BASE}/finance/debtors`, { headers: getAuthHeader() }),
            fetch(`${API_BASE}/finance/revenue-report`, { headers: getAuthHeader() })
        ]);

        const debtors = await debtorsRes.json();
        const revenue = await revenueRes.json();

        const outstanding = debtors.debtors?.reduce((sum, d) => sum + d.unpaid_amount, 0) || 0;

        document.getElementById('total-revenue').textContent = 
            (revenue.total_revenue || 0).toFixed(2) + ' TND';
        document.getElementById('debtor-count').textContent = debtors.total_debtors || 0;
        document.getElementById('outstanding').textContent = outstanding.toFixed(2) + ' TND';
        document.getElementById('attestation-count').textContent = 
            'Issue as needed'; // No aggregate endpoint, so display hint
    } catch (error) {
        console.error('Error loading overview:', error);
    }
}

// Tax debtors
async function loadDebtors() {
    try {
        const response = await fetch(`${API_BASE}/finance/debtors`, { headers: getAuthHeader() });
        const data = await response.json();
        const tbody = document.getElementById('debtors-body');
        tbody.innerHTML = '';

        if (!data.debtors || data.debtors.length === 0) {
            tbody.innerHTML = '<tr><td colspan="4">No unpaid taxpayers detected.</td></tr>';
            return;
        }

        data.debtors.forEach(debtor => {
            const row = tbody.insertRow();
            row.innerHTML = `
                <td>${debtor.username} (#${debtor.user_id})</td>
                <td>${debtor.unpaid_amount.toFixed(2)} TND</td>
                <td>${debtor.tax_count}</td>
                <td>
                    <button class="button" onclick="prefillAttestation(${debtor.user_id})">Attestation</button>
                </td>
            `;
        });
    } catch (error) {
        console.error('Error loading debtors:', error);
        document.getElementById('debtors-body').innerHTML = '<tr><td colspan="4">Failed to load debtors</td></tr>';
    }
}

function prefillAttestation(userId) {
    document.getElementById('user-id-input').value = userId;
    showSection('attestations', document.querySelector('[onclick*="attestations"]'));
}

async function issueAttestation() {
    const userId = document.getElementById('user-id-input').value.trim();
    const resultDiv = document.getElementById('attestation-result');
    resultDiv.textContent = '';

    if (!userId) {
        resultDiv.textContent = 'Enter a user ID first.';
        return;
    }

    try {
        const response = await fetch(`${API_BASE}/finance/attestation/${userId}`, {
            method: 'POST',
            headers: getAuthHeader()
        });
        const data = await response.json();

        if (!response.ok) {
            resultDiv.innerHTML = `<div class="alert alert-error">${data.error || 'Unable to issue attestation'}</div>`;
            return;
        }

        resultDiv.innerHTML = `
            <div class="alert alert-success">
                Attestation ${data.attestation_number} issued for user #${data.user_id}.<br>
                Valid for ${data.validity}.
            </div>
        `;
    } catch (error) {
        resultDiv.innerHTML = '<div class="alert alert-error">Network error while issuing attestation.</div>';
    }
}

async function getReceipts() {
    const userId = document.getElementById('user-id-receipts').value.trim();
    const messageDiv = document.getElementById('receipts-message');
    const table = document.getElementById('receipts-table');
    const tbody = document.getElementById('receipts-body');

    messageDiv.textContent = '';
    tbody.innerHTML = '';

    if (!userId) {
        messageDiv.textContent = 'Enter a user ID to view receipts.';
        table.style.display = 'none';
        return;
    }

    try {
        const response = await fetch(`${API_BASE}/finance/payment-receipts/${userId}`, { headers: getAuthHeader() });
        const data = await response.json();

        if (!response.ok) {
            messageDiv.innerHTML = `<div class="alert alert-error">${data.error || 'Unable to load receipts.'}</div>`;
            table.style.display = 'none';
            return;
        }

        if (!data.payments || data.payments.length === 0) {
            messageDiv.textContent = 'No receipts found for this user.';
            table.style.display = 'none';
            return;
        }

        data.payments.forEach(payment => {
            const row = tbody.insertRow();
            row.innerHTML = `
                <td>${payment.payment_date ? new Date(payment.payment_date).toLocaleDateString() : '-'}</td>
                <td>${payment.amount.toFixed(2)} TND</td>
                <td>${payment.reference_number || 'N/A'}</td>
                <td>${payment.method}</td>
                <td>${payment.status || 'completed'}</td>
            `;
        });

        table.style.display = 'table';
    } catch (error) {
        messageDiv.innerHTML = '<div class="alert alert-error">Failed to load receipts.</div>';
        table.style.display = 'none';
    }
}

async function loadRevenueReport() {
    const container = document.getElementById('revenue-content');
    container.innerHTML = 'Loading...';

    try {
        const response = await fetch(`${API_BASE}/finance/revenue-report`, { headers: getAuthHeader() });
        const data = await response.json();

        if (!response.ok) {
            container.innerHTML = `<div class="alert alert-error">${data.error || 'Unable to load revenue report.'}</div>`;
            return;
        }

        const monthlyRows = Object.entries(data.monthly_breakdown || {}).map(
            ([month, amount]) => `<li>Month ${month}: <strong>${amount.toFixed(2)} TND</strong></li>`
        ).join('');

        container.innerHTML = `
            <p>Total revenue ${data.year}: <strong>${data.total_revenue.toFixed(2)} TND</strong> (${data.payment_count} payments)</p>
            <ul>${monthlyRows || '<li>No completed payments this year.</li>'}</ul>
        `;
    } catch (error) {
        container.innerHTML = '<div class="alert alert-error">Failed to load revenue report.</div>';
    }
}

// Modal Management
function closeModal(modalId) {
    document.getElementById(modalId).style.display = 'none';
}

// Close modals when clicking outside
window.onclick = function(event) {
    if (event.target.classList.contains('modal')) {
        event.target.style.display = 'none';
    }
}

// Detail views
function viewAttestation(id) {
    alert('Attestation detail view for ID ' + id + ' - Full PDF would open here');
}

function viewTaxpayerDetails(id) {
    alert('Taxpayer detail view for ID ' + id + ' - Full profile would open here');
}

// Logout
function logout() {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    localStorage.removeItem('role');
    window.location.href = '/common_login/index.html';
}

// Initialize on page load
window.addEventListener('load', () => {
    if (!getToken()) {
        window.location.href = '/common_login/index.html';
        return;
    }
    loadOverview();
    bindInlineHandlers();
});
    // Expose for inline handlers
    window.logout = logout;
    window.showSection = showSection;

function bindInlineHandlers() {
    document.querySelectorAll('[onclick]').forEach(el => {
        const attr = el.getAttribute('onclick') || '';
        if (attr.includes('logout')) {
            el.addEventListener('click', e => { e.preventDefault(); logout(); });
        }
        const m = attr.match(/showSection\('([^']+)'/);
        if (m) {
            el.addEventListener('click', e => { e.preventDefault(); showSection(m[1], el); });
        }
    });
}
