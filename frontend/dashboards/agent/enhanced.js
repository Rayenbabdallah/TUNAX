/**
 * Municipal Agent dashboard wiring for address verification and complaints.
 * Aligns UI sections with the existing /api/agent endpoints.
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

function showSection(sectionId, el) {
    document.querySelectorAll('.section').forEach(sec => sec.style.display = 'none');
    document.querySelectorAll('.nav-link').forEach(link => link.classList.remove('active'));
    document.getElementById(sectionId).style.display = 'block';
    if (el) el.classList.add('active');

    if (sectionId === 'overview') loadOverview();
    else if (sectionId === 'reclamations') loadReclamations();
    else if (sectionId === 'my-assignments') loadAssignments();
}

async function loadOverview() {
    try {
        const response = await fetch(`${API_BASE}/agent/reclamations`, { headers: getAuthHeader() });
        const data = await response.json();
        const complaints = data.reclamations || [];

        document.getElementById('pending-count').textContent =
            complaints.filter(c => c.status !== 'resolved').length;
        document.getElementById('assigned-count').textContent = complaints.length;
        document.getElementById('resolved-count').textContent =
            complaints.filter(c => c.status === 'resolved').length;
    } catch (error) {
        console.error('Error loading overview:', error);
    }
}

async function loadReclamations() {
    try {
        const response = await fetch(`${API_BASE}/agent/reclamations`, { headers: getAuthHeader() });
        const data = await response.json();
        const tbody = document.getElementById('reclamations-body');
        tbody.innerHTML = '';

        if (!data.reclamations || data.reclamations.length === 0) {
            tbody.innerHTML = '<tr><td colspan="6">No complaints assigned to you yet.</td></tr>';
            return;
        }

        data.reclamations.forEach(rec => {
            const row = tbody.insertRow();
            row.innerHTML = `
                <td>${rec.id}</td>
                <td>${rec.type}</td>
                <td>${rec.city || 'N/A'}</td>
                <td>${rec.status}</td>
                <td>${rec.created_at ? new Date(rec.created_at).toLocaleDateString() : '-'}</td>
                <td>
                    ${rec.status === 'assigned' ? `<button class="button" onclick="claimComplaint(${rec.id})">Work on it</button>` : 'In progress'}
                </td>
            `;
        });
    } catch (error) {
        console.error('Error loading complaints:', error);
        document.getElementById('reclamations-body').innerHTML = '<tr><td colspan="6">Failed to load complaints</td></tr>';
    }
}

async function loadAssignments() {
    try {
        const response = await fetch(`${API_BASE}/agent/reclamations`, { headers: getAuthHeader() });
        const data = await response.json();
        const tbody = document.getElementById('assignments-body');
        tbody.innerHTML = '';

        if (!data.reclamations || data.reclamations.length === 0) {
            tbody.innerHTML = '<tr><td colspan="5">No assignments yet.</td></tr>';
            return;
        }

        data.reclamations.forEach(rec => {
            const row = tbody.insertRow();
            row.innerHTML = `
                <td>${rec.id}</td>
                <td>${rec.type}</td>
                <td>${rec.street_address || '-'}, ${rec.city || ''}</td>
                <td>${rec.status}</td>
                <td>
                    <button class="button" onclick="prefillUpdate(${rec.id}, '${rec.status}')">Update</button>
                </td>
            `;
        });
    } catch (error) {
        console.error('Error loading assignments:', error);
        document.getElementById('assignments-body').innerHTML = '<tr><td colspan="5">Failed to load assignments</td></tr>';
    }
}

async function claimComplaint(complaintId) {
    try {
        const response = await fetch(`${API_BASE}/agent/reclamations/${complaintId}/assign`, {
            method: 'PATCH',
            headers: getAuthHeader()
        });
        const data = await response.json();

        if (!response.ok) {
            alert(data.error || 'Unable to claim complaint.');
            return;
        }

        loadOverview();
        loadReclamations();
        loadAssignments();
    } catch (error) {
        alert('Network error while assigning complaint.');
    }
}

function prefillUpdate(id, status) {
    document.getElementById('complaint-id-update').value = id;
    document.getElementById('new-status').value = status === 'resolved' ? 'resolved' : 'in-progress';
    document.getElementById('resolution-details').focus();
}

async function updateComplaintStatus() {
    const id = document.getElementById('complaint-id-update').value.trim();
    const status = document.getElementById('new-status').value;
    const resolution = document.getElementById('resolution-details').value.trim();
    const messageDiv = document.getElementById('update-message');

    if (!id) {
        messageDiv.textContent = 'Enter a complaint ID.';
        return;
    }

    const payload = { status: status.replace('-', '_') };
    if (resolution) payload.resolution = resolution;

    try {
        const response = await fetch(`${API_BASE}/agent/reclamations/${id}/update`, {
            method: 'PATCH',
            headers: getAuthHeader(),
            body: JSON.stringify(payload)
        });
        const data = await response.json();

        if (!response.ok) {
            messageDiv.innerHTML = `<div class="alert alert-error">${data.error || 'Update failed.'}</div>`;
            return;
        }

        messageDiv.innerHTML = '<div class="alert alert-success">Complaint updated.</div>';
        loadOverview();
        loadAssignments();
        loadReclamations();
    } catch (error) {
        messageDiv.innerHTML = '<div class="alert alert-error">Network error while updating complaint.</div>';
    }
}

async function verifyAddress() {
    const rawAddress = document.getElementById('address-input').value.trim();
    const resultDiv = document.getElementById('verify-result');
    resultDiv.textContent = '';

    if (!rawAddress || !rawAddress.includes(',')) {
        resultDiv.textContent = 'Enter address as "Street, City".';
        return;
    }

    const [street, city] = rawAddress.split(',').map(v => v.trim());

    try {
        const response = await fetch(`${API_BASE}/agent/verify/address`, {
            method: 'POST',
            headers: getAuthHeader(),
            body: JSON.stringify({ street, city })
        });
        const data = await response.json();

        if (!response.ok || !data.found) {
            resultDiv.innerHTML = `<div class="alert alert-error">${data.error || 'Address not found.'}</div>`;
            if (data.suggestions) {
                resultDiv.innerHTML += `<p>Suggestions: ${data.suggestions.join(', ')}</p>`;
            }
            return;
        }

        resultDiv.innerHTML = `
            <div class="alert alert-success">
                Found coordinates (${data.latitude.toFixed(6)}, ${data.longitude.toFixed(6)}).
                ${data.address_info ? `<p>${data.address_info.display_name || ''}</p>` : ''}
            </div>
        `;
    } catch (error) {
        resultDiv.innerHTML = '<div class="alert alert-error">Network error while verifying address.</div>';
    }
}

async function submitVerification() {
    const id = document.getElementById('item-id-verify').value.trim();
    const type = document.getElementById('item-type-verify').value;
    const result = document.getElementById('verification-result-select').value;
    const notes = document.getElementById('verification-notes').value;
    const messageDiv = document.getElementById('verification-message');

    if (!id) {
        messageDiv.textContent = 'Enter an ID.';
        return;
    }

    const endpoint = type === 'property'
        ? `${API_BASE}/agent/verify/property/${id}`
        : `${API_BASE}/agent/verify/land/${id}`;

    try {
        const response = await fetch(endpoint, {
            method: 'POST',
            headers: getAuthHeader(),
            body: JSON.stringify({ notes: notes || result })
        });
        const data = await response.json();

        if (!response.ok) {
            messageDiv.innerHTML = `<div class="alert alert-error">${data.error || 'Verification failed.'}</div>`;
            return;
        }

        messageDiv.innerHTML = '<div class="alert alert-success">Verification saved.</div>';
    } catch (error) {
        messageDiv.innerHTML = '<div class="alert alert-error">Network error while verifying.</div>';
    }
}

// Document Review Functions for Agent
async function loadDeclarationDocuments() {
    const id = document.getElementById('item-id-verify').value.trim();
    const type = document.getElementById('item-type-verify').value;
    
    if (!id) {
        alert('Please enter a Property/Land ID');
        return;
    }
    
    try {
        // Get declaration details
        const declEndpoint = type === 'property'
            ? `${API_BASE}/tib/properties/${id}`
            : `${API_BASE}/ttnb/lands/${id}`;
            
        const declResponse = await fetch(declEndpoint, { headers: getAuthHeader() });
        const declData = await declResponse.json();
        
        // Display declaration info
        const declInfoDiv = document.getElementById('declaration-info');
        const property = declData.property || declData.land;
        
        if (property) {
            declInfoDiv.innerHTML = `
                <div>
                    <strong>ID:</strong> ${property.id}<br>
                    <strong>Address:</strong> ${property.street_address || 'N/A'}<br>
                    <strong>Status:</strong> <span style="color: #667eea;">${property.status}</span><br>
                    <strong>Type:</strong> ${type === 'property' ? 'Property (TIB)' : 'Land (TTNB)'}<br>
                    ${property.surface_couverte ? `<strong>Covered Surface:</strong> ${property.surface_couverte} m²<br>` : ''}
                    ${property.surface ? `<strong>Surface:</strong> ${property.surface} m²<br>` : ''}
                </div>
            `;
        }
        
        // Get documents
        const docsResponse = await fetch(`${API_BASE}/documents/declarations/${id}/documents`, {
            headers: getAuthHeader()
        });
        const docsData = await docsResponse.json();
        
        // Display documents
        const listDiv = document.getElementById('documents-list');
        if (docsData.documents && docsData.documents.length > 0) {
            listDiv.innerHTML = docsData.documents.map(doc => `
                <div style="padding: 12px; background: white; border: 1px solid #ddd; border-radius: 6px; margin-bottom: 8px;">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <div>
                            <span style="font-weight: 500;">📄 ${doc.document_type}</span><br>
                            <small style="color: #666;">Status: ${doc.status}</small>
                        </div>
                        <a href="${API_BASE}/documents/documents/${doc.id}/file" target="_blank" class="button" style="padding: 6px 12px; font-size: 12px;">Download</a>
                    </div>
                </div>
            `).join('');
        } else {
            listDiv.innerHTML = '<div style="padding: 12px; background: #fff3cd; border-radius: 6px; color: #856404;">ℹ️ No documents uploaded yet</div>';
        }
        
        // Show document review section
        document.getElementById('document-review-section').style.display = 'block';
    } catch (error) {
        console.error('Error loading documents:', error);
        alert('Failed to load declaration and documents');
    }
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
