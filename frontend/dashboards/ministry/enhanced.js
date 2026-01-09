/**
 * Ministry Dashboard - National Administration
 * Manages municipalities, municipal admins, and nation-wide statistics
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
    document.querySelectorAll('.section').forEach(section => section.style.display = 'none');
    document.querySelectorAll('.nav-link').forEach(link => link.classList.remove('active'));
    document.getElementById(sectionId).style.display = 'block';
    if (el) el.classList.add('active');

    if (sectionId === 'municipalities') loadMunicipalities();
    else if (sectionId === 'admins') loadAdmins();
    else if (sectionId === 'statistics') loadStatistics();
    else if (sectionId === 'audit') loadAuditLog();
    else if (sectionId === 'overview') loadOverview();
}

// Load Overview Dashboard
async function loadOverview() {
    try {
        const response = await fetch(`${API_BASE}/ministry/dashboard`, { headers: getAuthHeader() });
        if (!response.ok) throw new Error('Failed to load ministry dashboard');
        const data = await response.json();

        document.getElementById('total-properties').textContent = data.total_properties || 0;
        document.getElementById('total-lands').textContent = data.total_lands || 0;
        document.getElementById('total-taxes').textContent = data.total_taxes || 0;
        document.getElementById('paid-taxes').textContent = data.paid_taxes || 0;
        document.getElementById('payment-rate').textContent = 
            `${(data.payment_rate || 0).toFixed(1)}%`;
        document.getElementById('municipality-count').textContent = 
            data.commune_statistics ? data.commune_statistics.length : 0;
    } catch (error) {
        console.error('Error loading overview:', error);
        showError('overview', 'Failed to load dashboard statistics');
    }
}

// Load Municipalities
async function loadMunicipalities() {
    try {
        const response = await fetch(`${API_BASE}/ministry/municipalities`, { headers: getAuthHeader() });
        if (!response.ok) throw new Error('Failed to load municipalities');
        const data = await response.json();
        
        const tbody = document.getElementById('municipalities-body');
        tbody.innerHTML = '';

        if (!data.municipalities || data.municipalities.length === 0) {
            tbody.innerHTML = '<tr><td colspan="7">No municipalities found</td></tr>';
            return;
        }

        data.municipalities.forEach(commune => {
            const row = tbody.insertRow();
            row.innerHTML = `
                <td><strong>${commune.nom_municipalite_fr}</strong></td>
                <td>${commune.nom_gouvernorat_fr || '—'}</td>
                <td>${commune.properties_count || 0}</td>
                <td>${commune.lands_count || 0}</td>
                <td>${commune.taxes_count || 0}</td>
                <td>${commune.admin_name || '—'}</td>
                <td>
                    <button class="button" onclick="viewMunicipalityDetails(${commune.id})" style="font-size: 0.9em; padding: 5px 10px;">View</button>
                </td>
            `;
        });
    } catch (error) {
        console.error('Error loading municipalities:', error);
        showError('municipalities', 'Failed to load municipalities');
    }
}

// Load Municipal Admins
async function loadAdmins() {
    try {
        const response = await fetch(`${API_BASE}/ministry/municipal-admins`, { headers: getAuthHeader() });
        if (!response.ok) throw new Error('Failed to load municipal admins');
        const data = await response.json();

        const tbody = document.getElementById('admins-body');
        tbody.innerHTML = '';

        if (!data.municipal_admins || data.municipal_admins.length === 0) {
            tbody.innerHTML = '<tr><td colspan="6">No municipal admins found</td></tr>';
            return;
        }

        data.municipal_admins.forEach(admin => {
            const row = tbody.insertRow();
            const created = new Date(admin.created_at).toLocaleDateString();
            const statusClass = admin.is_active ? 'status-approved' : 'status-rejected';
            row.innerHTML = `
                <td><strong>${admin.username}</strong></td>
                <td>${admin.email}</td>
                <td>${admin.commune_name || '—'}</td>
                <td><span class="status-badge ${statusClass}">${admin.is_active ? 'Active' : 'Inactive'}</span></td>
                <td>${created}</td>
                <td>
                    ${admin.is_active ? 
                        `<button class="button" onclick="toggleAdminStatus(${admin.id}, false)" style="font-size: 0.9em; padding: 5px 10px;">Disable</button>` : 
                        `<button class="button" onclick="toggleAdminStatus(${admin.id}, true)" style="font-size: 0.9em; padding: 5px 10px;">Enable</button>`
                    }
                </td>
            `;
        });
    } catch (error) {
        console.error('Error loading admins:', error);
        showError('admins', 'Failed to load municipal administrators');
    }
}

// Load Municipalities for dropdown
async function loadMunicipalitiesForDropdown() {
    try {
        const response = await fetch(`${API_BASE}/ministry/municipalities`, { headers: getAuthHeader() });
        if (!response.ok) throw new Error('Failed to load municipalities');
        const data = await response.json();

        const select = document.getElementById('admin-commune');
        select.innerHTML = '<option value="">-- Select Municipality --</option>';

        if (data.municipalities && data.municipalities.length > 0) {
            data.municipalities.forEach(commune => {
                const option = document.createElement('option');
                option.value = commune.id;
                option.textContent = commune.nom_municipalite_fr;
                select.appendChild(option);
            });
        }
    } catch (error) {
        console.error('Error loading municipalities:', error);
    }
}

// Create Admin
async function handleCreateAdmin(event) {
    event.preventDefault();
    const messageDiv = document.getElementById('create-message');
    messageDiv.innerHTML = '';

    const formData = {
        username: document.getElementById('admin-username').value,
        email: document.getElementById('admin-email').value,
        password: document.getElementById('admin-password').value,
        first_name: document.getElementById('admin-first-name').value,
        last_name: document.getElementById('admin-last-name').value,
        commune_id: parseInt(document.getElementById('admin-commune').value)
    };

    if (!formData.commune_id) {
        messageDiv.innerHTML = '<div class="error">Please select a municipality</div>';
        return;
    }

    try {
        const response = await fetch(`${API_BASE}/ministry/municipal-admins`, {
            method: 'POST',
            headers: getAuthHeader(),
            body: JSON.stringify(formData)
        });

        const data = await response.json();

        if (!response.ok) {
            messageDiv.innerHTML = `<div class="error">${data.error || 'Failed to create admin'}</div>`;
            return;
        }

        messageDiv.innerHTML = `<div class="success">✓ Municipal administrator created successfully! Username: ${data.username}</div>`;
        
        // Reset form
        document.getElementById('admin-username').value = '';
        document.getElementById('admin-email').value = '';
        document.getElementById('admin-password').value = '';
        document.getElementById('admin-first-name').value = '';
        document.getElementById('admin-last-name').value = '';
        document.getElementById('admin-commune').value = '';

    } catch (error) {
        console.error('Error creating admin:', error);
        messageDiv.innerHTML = `<div class="error">Error: ${error.message}</div>`;
    }
}

// Toggle Admin Status
async function toggleAdminStatus(adminId, enable) {
    const action = enable ? 'enable' : 'disable';
    if (!confirm(`Are you sure you want to ${action} this administrator?`)) return;

    try {
        const response = await fetch(`${API_BASE}/ministry/municipal-admins/${adminId}/status`, {
            method: 'PATCH',
            headers: getAuthHeader(),
            body: JSON.stringify({ is_active: enable })
        });

        const data = await response.json();

        if (!response.ok) {
            alert(`Error: ${data.error || 'Failed to update status'}`);
            return;
        }

        alert(`Administrator ${enable ? 'enabled' : 'disabled'} successfully`);
        loadAdmins();
    } catch (error) {
        console.error('Error updating admin status:', error);
        alert(`Error: ${error.message}`);
    }
}

// Load Statistics
async function loadStatistics() {
    try {
        const response = await fetch(`${API_BASE}/ministry/dashboard`, { headers: getAuthHeader() });
        if (!response.ok) throw new Error('Failed to load statistics');
        const data = await response.json();

        let html = '<table>';
        html += '<tr><th>Municipality</th><th>Properties</th><th>Lands</th><th>Taxes</th></tr>';

        if (data.commune_statistics && data.commune_statistics.length > 0) {
            data.commune_statistics.forEach(comm => {
                html += `<tr>
                    <td>${comm.commune_name}</td>
                    <td>${comm.properties}</td>
                    <td>${comm.lands || 0}</td>
                    <td>${comm.taxes}</td>
                </tr>`;
            });
        }

        html += '</table>';
        document.getElementById('stats-content').innerHTML = html;
    } catch (error) {
        console.error('Error loading statistics:', error);
        showError('statistics', 'Failed to load statistics');
    }
}

// Load Audit Log
async function loadAuditLog() {
    try {
        const response = await fetch(`${API_BASE}/ministry/audit-log`, { headers: getAuthHeader() });
        if (!response.ok) throw new Error('Failed to load audit log');
        const data = await response.json();

        const tbody = document.getElementById('audit-body');
        tbody.innerHTML = '';

        if (!data.logs || data.logs.length === 0) {
            tbody.innerHTML = '<tr><td colspan="5">No audit logs found</td></tr>';
            return;
        }

        data.logs.slice(0, 50).forEach(log => {
            const row = tbody.insertRow();
            const timestamp = new Date(log.created_at).toLocaleString();
            row.innerHTML = `
                <td>${timestamp}</td>
                <td>${log.user_id}</td>
                <td>${log.action}</td>
                <td>${log.details || '—'}</td>
                <td><span class="status-badge status-approved">Success</span></td>
            `;
        });
    } catch (error) {
        console.error('Error loading audit log:', error);
        showError('audit', 'Failed to load audit log');
    }
}

// View Municipality Details
function viewMunicipalityDetails(communeId) {
    alert(`Municipality details for ID: ${communeId}\n\nThis feature will show detailed statistics for the selected municipality.`);
}

// Show Error Message
function showError(sectionId, message) {
    const section = document.getElementById(sectionId);
    if (section) {
        const card = section.querySelector('.card');
        if (card) {
            const errorDiv = document.createElement('div');
            errorDiv.className = 'error';
            errorDiv.textContent = message;
            card.insertBefore(errorDiv, card.firstChild);
        }
    }
}

// Logout
function logout() {
    localStorage.removeItem('access_token');
    window.location.href = '/common_login/';
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', function() {
    if (!getToken()) {
        window.location.href = '/common_login/';
        return;
    }

    loadOverview();
    loadMunicipalitiesForDropdown();
    bindInlineHandlers();
});
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
    window.logout = logout;
    window.showSection = showSection;
