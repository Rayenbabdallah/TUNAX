/**
 * Contentieux Officer Dashboard - aligns with /api/disputes endpoints.
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

async function fetchOfficerDisputes(status = '') {
    const query = status ? `?status=${status}` : '';
    const response = await fetch(`${API_BASE}/disputes/office${query}`, { headers: getAuthHeader() });
    if (!response.ok) throw new Error('Unable to load disputes');
    const data = await response.json();
    return data.disputes || [];
}

function renderDisputes(rows, elementId, emptyMessage = 'No disputes found') {
    const tbody = document.getElementById(elementId);
    tbody.innerHTML = '';

    if (!rows.length) {
        tbody.innerHTML = `<tr><td colspan="6">${emptyMessage}</td></tr>`;
        return;
    }

    rows.forEach(dispute => {
        const row = tbody.insertRow();
        const status = dispute.status || 'submitted';
        const badge = `<span class="status-badge status-${status}">${status.replace('_', ' ')}</span>`;
        const amount = dispute.claimed_amount ? `${dispute.claimed_amount.toFixed(2)} TND` : 'N/A';
        row.innerHTML = `
            <td>${dispute.id}</td>
            <td>${dispute.claimant_id}</td>
            <td>${dispute.dispute_type}</td>
            <td>${amount}</td>
            <td>${badge}</td>
            <td><button class="button" onclick="viewDisputeDetail(${dispute.id})">View</button></td>
        `;
    });
}

function showSection(sectionId, el) {
    document.querySelectorAll('.section').forEach(el => el.style.display = 'none');
    document.querySelectorAll('.nav-link').forEach(x => x.classList.remove('active'));
    document.getElementById(sectionId).style.display = 'block';
    if (el) el.classList.add('active');

    if (sectionId === 'overview') loadOverview();
    else if (sectionId === 'assigned') loadAssignedDisputes();
    else if (sectionId === 'commission') loadCommissionReview();
    else if (sectionId === 'decisions') loadFinalDecisions();
}

async function loadOverview() {
    try {
        const disputes = await fetchOfficerDisputes();
        const assigned = disputes.length;
        const pending = disputes.filter(d => d.status === 'submitted' || d.status === 'accepted').length;
        const decided = disputes.filter(d => d.status === 'resolved').length;
        const appeals = disputes.filter(d => d.status === 'appealed').length;

        document.getElementById('assigned-count').textContent = assigned;
        document.getElementById('pending-count').textContent = pending;
        document.getElementById('decided-count').textContent = decided;
        document.getElementById('appeals-count').textContent = appeals;
    } catch (error) {
        console.error('Error loading overview:', error);
        ['assigned-count', 'pending-count', 'decided-count', 'appeals-count'].forEach(id => {
            document.getElementById(id).textContent = '—';
        });
    }
}

async function loadAssignedDisputes() {
    try {
        const disputes = await fetchOfficerDisputes();
        renderDisputes(disputes, 'assigned-body', 'No disputes currently assigned to you');
    } catch (error) {
        console.error('Error loading assigned disputes:', error);
        document.getElementById('assigned-body').innerHTML = '<tr><td colspan="6">Error loading disputes</td></tr>';
    }
}

async function loadCommissionReview() {
    try {
        const reviewItems = await fetchOfficerDisputes('commission_review');
        const tbody = document.getElementById('commission-body');
        tbody.innerHTML = '';

        if (!reviewItems.length) {
            tbody.innerHTML = '<tr><td colspan="5">No disputes under commission review</td></tr>';
            return;
        }

        reviewItems.forEach(item => {
            const date = item.commission_review_date
                ? new Date(item.commission_review_date).toLocaleDateString()
                : '-';
            const row = tbody.insertRow();
            row.innerHTML = `
                <td>${item.id}</td>
                <td>${item.claimant_id}</td>
                <td>${item.commission_decision || 'Pending'}</td>
                <td>${date}</td>
                <td><button class="button" onclick="viewDisputeDetail(${item.id})">Details</button></td>
            `;
        });
    } catch (error) {
        console.error('Error loading commission review disputes:', error);
        document.getElementById('commission-body').innerHTML = '<tr><td colspan="5">Error loading disputes</td></tr>';
    }
}

async function loadFinalDecisions() {
    try {
        const decided = await fetchOfficerDisputes('resolved');
        const tbody = document.getElementById('decisions-body');
        tbody.innerHTML = '';

        if (!decided.length) {
            tbody.innerHTML = '<tr><td colspan="6">No final decisions yet</td></tr>';
            return;
        }

        decided.forEach(item => {
            const decisionDate = item.decision_date ? new Date(item.decision_date).toLocaleDateString() : '-';
            const row = tbody.insertRow();
            row.innerHTML = `
                <td>${item.id}</td>
                <td>${item.claimant_id}</td>
                <td>${item.claimed_amount ? item.claimed_amount.toFixed(2) + ' TND' : 'N/A'}</td>
                <td>${item.final_amount ? item.final_amount.toFixed(2) + ' TND' : 'N/A'}</td>
                <td>${item.final_decision || 'N/A'}</td>
                <td>${decisionDate}</td>
            `;
        });
    } catch (error) {
        console.error('Error loading decisions:', error);
        document.getElementById('decisions-body').innerHTML = '<tr><td colspan="6">Error loading decisions</td></tr>';
    }
}

async function handleCommissionReview(event) {
    event.preventDefault();
    const disputeId = document.getElementById('dispute-id-commission').value.trim();
    const decision = document.getElementById('commission-decision').value;
    const justification = document.getElementById('commission-justification').value;
    const amount = document.getElementById('adjustment-amount').value;

    if (!disputeId || !decision) return;

    try {
        const response = await fetch(`${API_BASE}/disputes/${disputeId}/commission-review`, {
            method: 'PATCH',
            headers: getAuthHeader(),
            body: JSON.stringify({
                commission_decision: `${decision}: ${justification}`,
                adjustment_amount: amount ? Number(amount) : undefined
            })
        });
        const data = await response.json();
        if (!response.ok) throw new Error(data.error || 'Failed to submit commission review');
        document.getElementById('commission-message').innerHTML =
            '<p style="color: green;">Commission review submitted.</p>';
        loadCommissionReview();
        loadOverview();
        event.target.reset();
    } catch (error) {
        document.getElementById('commission-message').innerHTML =
            `<p style="color: red;">${error.message}</p>`;
    }
}

async function handleFinalDecision(event) {
    event.preventDefault();
    const disputeId = document.getElementById('dispute-id-final').value.trim();
    const finalDecision = document.getElementById('final-decision').value;
    const finalAmount = Number(document.getElementById('final-amount').value);
    const justification = document.getElementById('final-justification').value;

    if (!disputeId || !finalDecision) return;

    try {
        const response = await fetch(`${API_BASE}/disputes/${disputeId}/decision`, {
            method: 'PATCH',
            headers: getAuthHeader(),
            body: JSON.stringify({
                final_decision: `${finalDecision}: ${justification}`,
                final_amount: isNaN(finalAmount) ? undefined : finalAmount
            })
        });
        const data = await response.json();
        if (!response.ok) throw new Error(data.error || 'Failed to issue decision');
        document.getElementById('decision-message').innerHTML =
            '<p style="color: green;">Final decision recorded.</p>';
        loadFinalDecisions();
        loadOverview();
        event.target.reset();
    } catch (error) {
        document.getElementById('decision-message').innerHTML =
            `<p style="color: red;">${error.message}</p>`;
    }
}

function viewDisputeDetail(id) {
    alert(`Dispute detail placeholder for ${id}`);
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
