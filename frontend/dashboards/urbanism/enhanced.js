/**
 * Urbanism Officer Dashboard (matches backend /api/permits routes)
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

async function fetchPendingPermits() {
    const response = await fetch(`${API_BASE}/permits/pending`, { headers: getAuthHeader() });
    if (!response.ok) throw new Error('Pending permits endpoint unavailable');
    const data = await response.json();
    return data.permits || [];
}

async function fetchBlockedPermits() {
    const response = await fetch(`${API_BASE}/permits/blocked`, { headers: getAuthHeader() });
    if (!response.ok) throw new Error('Blocked permits endpoint unavailable');
    const data = await response.json();
    return data.blocked_permits || [];
}

async function fetchPermitHistory(status) {
    const query = status ? `?status=${status}` : '';
    const response = await fetch(`${API_BASE}/permits/history${query}`, { headers: getAuthHeader() });
    if (!response.ok) throw new Error('Permit history endpoint unavailable');
    const data = await response.json();
    return data.permits || [];
}

function renderPending(rows, elementId, { withActions = false } = {}) {
    const tbody = document.getElementById(elementId);
    tbody.innerHTML = '';

    if (!rows.length) {
        tbody.innerHTML = '<tr><td colspan="6">No permit requests available</td></tr>';
        return;
    }

    rows.forEach(permit => {
        const row = tbody.insertRow();
        const submitted = permit.submitted_date ? new Date(permit.submitted_date).toLocaleDateString() : '-';
        row.innerHTML = `
            <td>${permit.id}</td>
            <td>${permit.user_id}</td>
            <td>${permit.permit_type}</td>
            <td>${permit.description || 'N/A'}</td>
            <td>${submitted}</td>
            <td>
                ${withActions ? `
                    <button class="button approve-btn" onclick="approvePermit(${permit.id})">Approve</button>
                    <button class="button reject-btn" onclick="rejectPermit(${permit.id})">Reject</button>
                ` : '<span class="status-badge status-pending">pending</span>'}
            </td>
        `;
    });
}

function showSection(sectionId, el) {
    document.querySelectorAll('.section').forEach(el => el.style.display = 'none');
    document.querySelectorAll('.nav-link').forEach(x => x.classList.remove('active'));
    document.getElementById(sectionId).style.display = 'block';
    if (el) el.classList.add('active');

    if (sectionId === 'overview') loadOverview();
    else if (sectionId === 'pending') loadPendingPermits();
    else if (sectionId === 'approved') loadApprovedPermits();
    else if (sectionId === 'article13') loadArticle13Blocked();
}

async function loadOverview() {
    try {
        const [pending, blocked, history] = await Promise.all([
            fetchPendingPermits(),
            fetchBlockedPermits(),
            fetchPermitHistory()
        ]);
        document.getElementById('pending-count').textContent = pending.length;
        const approvedCount = history.filter(p => p.status === 'approved').length;
        const rejectedCount = history.filter(p => p.status === 'rejected').length;
        document.getElementById('approved-count').textContent = approvedCount;
        document.getElementById('rejected-count').textContent = rejectedCount;
        document.getElementById('blocked-count').textContent = blocked.length;
    } catch (error) {
        console.error('Error loading overview:', error);
        ['pending-count', 'approved-count', 'rejected-count', 'blocked-count'].forEach(id => {
            document.getElementById(id).textContent = '—';
        });
    }
}

async function loadPendingPermits() {
    try {
        const permits = await fetchPendingPermits();
        renderPending(permits, 'pending-body', { withActions: true });
    } catch (error) {
        console.error('Error loading pending permits:', error);
        document.getElementById('pending-body').innerHTML = '<tr><td colspan="6">Unable to load pending permits</td></tr>';
    }
}

async function loadApprovedPermits() {
    const tbody = document.getElementById('approved-body');
    tbody.innerHTML = '<tr><td colspan="5">Loading...</td></tr>';
    try {
        const permits = await fetchPermitHistory();
        if (!permits.length) {
            tbody.innerHTML = '<tr><td colspan="5">No approved or rejected permits found.</td></tr>';
            return;
        }
        tbody.innerHTML = '';
        permits.forEach(permit => {
            const decision = permit.decision_date ? new Date(permit.decision_date).toLocaleDateString() : '-';
            const row = tbody.insertRow();
            row.innerHTML = `
                <td>${permit.id}</td>
                <td>${permit.user_id}</td>
                <td>${permit.permit_type}</td>
                <td><span class="status-badge status-${permit.status}">${permit.status}</span></td>
                <td>${decision}</td>
            `;
        });
    } catch (error) {
        console.error('Error loading approved permits:', error);
        tbody.innerHTML = '<tr><td colspan="5">Unable to load approved permits.</td></tr>';
    }
}

async function loadArticle13Blocked() {
    const tbody = document.getElementById('blocked-body');
    tbody.innerHTML = '<tr><td colspan="5">Loading...</td></tr>';

    try {
        const blocked = await fetchBlockedPermits();
        if (!blocked.length) {
            tbody.innerHTML = '<tr><td colspan="5">No permits are blocked at the moment.</td></tr>';
            return;
        }

        tbody.innerHTML = '';
        blocked.forEach(item => {
            const submitted = item.submitted_date ? new Date(item.submitted_date).toLocaleDateString() : '-';
            const row = tbody.insertRow();
            row.innerHTML = `
                <td>${item.id}</td>
                <td>${item.user_id}</td>
                <td>${item.permit_type}</td>
                <td>${item.outstanding_amount.toFixed(2)} TND (${item.unpaid_taxes} unpaid)</td>
                <td>${submitted}</td>
            `;
        });
    } catch (error) {
        console.error('Error loading blocked permits:', error);
        tbody.innerHTML = '<tr><td colspan="5">Unable to load blocked permits.</td></tr>';
    }
}

async function updatePermitDecision(permitId, status, notes) {
    try {
        const response = await fetch(`${API_BASE}/permits/${permitId}/decide`, {
            method: 'PATCH',
            headers: getAuthHeader(),
            body: JSON.stringify({ status, notes })
        });
        const data = await response.json();
        if (!response.ok) {
            alert(data.error || 'Failed to update permit');
            return;
        }
        await loadOverview();
        await loadPendingPermits();
        alert(`Permit ${status}.`);
    } catch (error) {
        alert('Network error while updating permit.');
    }
}

async function approvePermit(permitId) {
    const notes = prompt('Approval notes (optional):') || '';
    await updatePermitDecision(permitId, 'approved', notes);
}

async function rejectPermit(permitId) {
    const notes = prompt('Rejection reason:');
    if (!notes) return;
    await updatePermitDecision(permitId, 'rejected', notes);
}

function logout() {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    localStorage.removeItem('role');
    window.location.href = '/common_login/index.html';
}

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
