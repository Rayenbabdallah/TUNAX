/**
 * Municipal Admin Dashboard - Municipality Administration
 * Staff management, municipality statistics, overview
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

    if (sectionId === 'staff') loadStaff();
    else if (sectionId === 'statistics') loadStatistics();
    else if (sectionId === 'overview') loadOverview();
    else if (sectionId === 'budget') loadBudgetProjects();
}
// Ensure inline handlers resolve
window.showSection = showSection;

// Load Overview
async function loadOverview() {
    try {
        const response = await fetch(`${API_BASE}/municipal/dashboard`, { headers: getAuthHeader() });
        if (!response.ok) throw new Error('Failed to load dashboard');
        const data = await response.json();

        // API returns nested structure: data.statistics.{properties, lands, etc}
        const stats = data.statistics || {};
        document.getElementById('total-properties').textContent = stats.properties || 0;
        document.getElementById('total-lands').textContent = stats.lands || 0;
        document.getElementById('total-taxes').textContent = stats.total_taxes || 0;
        document.getElementById('revenue').textContent = 
            `${(stats.revenue || 0).toFixed(2)} TND`;
    } catch (error) {
        console.error('Error loading overview:', error);
        document.getElementById('total-properties').textContent = '—';
        document.getElementById('total-lands').textContent = '—';
        document.getElementById('total-taxes').textContent = '—';
        document.getElementById('revenue').textContent = '—';
    }
}

// Load Staff
async function loadStaff() {
    try {
        const response = await fetch(`${API_BASE}/municipal/staff`, { headers: getAuthHeader() });
        if (!response.ok) throw new Error('Failed to load staff');
        const data = await response.json();

        const tbody = document.getElementById('staff-body');
        tbody.innerHTML = '';

        if (!data.staff || data.staff.length === 0) {
            tbody.innerHTML = '<tr><td colspan="5">No staff members found</td></tr>';
            return;
        }

        data.staff.forEach(member => {
            const row = tbody.insertRow();
            const statusClass = member.is_active ? 'status-approved' : 'status-rejected';
            row.innerHTML = `
                <td>${member.username}</td>
                <td>${member.email}</td>
                <td>${member.role}</td>
                <td><span class="status-badge ${statusClass}">${member.is_active ? 'Active' : 'Inactive'}</span></td>
                <td>
                    <button class="button" onclick="editStaff(${member.id})" style="font-size: 0.9em; padding: 5px 10px;">Edit</button>
                    ${member.is_active ? 
                        `<button class="button" onclick="deactivateStaff(${member.id})" style="font-size: 0.9em; padding: 5px 10px;">Deactivate</button>` : 
                        `<button class="button" onclick="activateStaff(${member.id})" style="font-size: 0.9em; padding: 5px 10px;">Activate</button>`
                    }
                </td>
            `;
        });
    } catch (error) {
        console.error('Error loading staff:', error);
        document.getElementById('staff-body').innerHTML = 
            '<tr><td colspan="5" style="color: red;">Failed to load staff</td></tr>';
    }
}

// Create Staff Member
async function handleCreateStaff(event) {
    event.preventDefault();
    const messageDiv = document.getElementById('create-message');
    messageDiv.innerHTML = '';

    const formData = {
        username: document.getElementById('username').value,
        email: document.getElementById('email').value,
        password: document.getElementById('password').value,
        role: document.getElementById('role').value
    };

    try {
        const response = await fetch(`${API_BASE}/municipal/staff`, {
            method: 'POST',
            headers: getAuthHeader(),
            body: JSON.stringify(formData)
        });

        const data = await response.json();

        if (!response.ok) {
            messageDiv.innerHTML = `<div style="color: #721c24; background: #f8d7da; padding: 10px; border-radius: 5px;">${data.error || 'Failed to create staff member'}</div>`;
            return;
        }

        messageDiv.innerHTML = `<div style="color: #155724; background: #d4edda; padding: 10px; border-radius: 5px;">✓ Staff member created successfully!</div>`;
        
        // Reset form
        event.target.reset();

    } catch (error) {
        console.error('Error creating staff:', error);
        messageDiv.innerHTML = `<div style="color: #721c24; background: #f8d7da; padding: 10px; border-radius: 5px;">Error: ${error.message}</div>`;
    }
}

// Edit Staff
function editStaff(staffId) {
    alert(`Edit staff member ${staffId}\n\nThis feature will allow you to update staff details.`);
}

// Deactivate Staff
async function deactivateStaff(staffId) {
    if (!confirm('Are you sure you want to deactivate this staff member?')) return;

    try {
        const response = await fetch(`${API_BASE}/municipal/staff/${staffId}`, {
            method: 'DELETE',
            headers: getAuthHeader()
        });

        const data = await response.json();

        if (!response.ok) {
            alert(`Error: ${data.error || 'Failed to deactivate staff'}`);
            return;
        }

        alert('Staff member deactivated successfully');
        loadStaff();
    } catch (error) {
        console.error('Error deactivating staff:', error);
        alert(`Error: ${error.message}`);
    }
}

// Activate Staff
function activateStaff(staffId) {
    alert(`Activate staff member ${staffId}\n\nThis feature will reactivate the staff member.`);
}

// Load Statistics
async function loadStatistics() {
    try {
        const response = await fetch(`${API_BASE}/municipal/dashboard`, { headers: getAuthHeader() });
        if (!response.ok) throw new Error('Failed to load statistics');
        const data = await response.json();

        // API returns nested structure
        const stats = data.statistics || {};
        const municipality = data.municipality || {};
        
        let html = `
            <div style="margin-bottom: 1.5rem;">
                <h3>Municipality: ${municipality.name || 'N/A'}</h3>
            </div>
            <p><strong>Properties:</strong> ${stats.properties || 0}</p>
            <p><strong>Lands:</strong> ${stats.lands || 0}</p>
            <p><strong>Total Taxes:</strong> ${stats.total_taxes || 0}</p>
            <p><strong>Paid Taxes:</strong> ${stats.paid_taxes || 0}</p>
            <p><strong>Collection Rate:</strong> ${(stats.collection_rate || 0).toFixed(1)}%</p>
            <p><strong>Revenue Collected:</strong> ${(stats.revenue || 0).toFixed(2)} TND</p>
        `;
        document.getElementById('stats-content').innerHTML = html;
    } catch (error) {
        console.error('Error loading statistics:', error);
        document.getElementById('stats-content').innerHTML = 
            '<p style="color: red;">Failed to load statistics</p>';
    }
}

// Logout
function logout() {
    localStorage.removeItem('access_token');
    window.location.href = '/common_login/';
}
window.logout = logout;

// ============ BUDGET PROJECTS ============

// Load Budget Projects
async function loadBudgetProjects() {
    try {
        const response = await fetch(`${API_BASE}/budget/projects`, { headers: getAuthHeader() });
        if (!response.ok) throw new Error('Failed to load budget projects');
        const data = await response.json();

        const tbody = document.getElementById('budget-projects-body');
        tbody.innerHTML = '';

        const projects = data.projects || [];
        if (projects.length === 0) {
            tbody.innerHTML = '<tr><td colspan="6">No budget projects found</td></tr>';
            return;
        }

        projects.forEach(project => {
            const row = tbody.insertRow();
            const statusClass = project.status === 'approved' ? 'status-approved' : 
                               project.status === 'rejected' ? 'status-rejected' : 'status-pending';
            const voteCount = project.votes_for || 0;
            const createdDate = new Date(project.created_at).toLocaleDateString();
            
            row.innerHTML = `
                <td>${project.title || project.project_name || 'N/A'}</td>
                <td>${(project.budget_amount || 0).toFixed(2)} TND</td>
                <td><span class="status-badge ${statusClass}">${project.status || 'pending'}</span></td>
                <td>${voteCount}</td>
                <td>${createdDate}</td>
                <td>
                    ${project.status === 'pending' ? `
                        <button class="button" onclick="openVoting(${project.id})" style="font-size: 0.9em; padding: 5px 10px;">Open Voting</button>
                    ` : ''}
                    ${project.voting_open && !project.voting_closed ? `
                        <button class="button" onclick="closeVoting(${project.id})" style="font-size: 0.9em; padding: 5px 10px;">Close Voting</button>
                    ` : ''}
                    <button class="button" onclick="viewProject(${project.id})" style="font-size: 0.9em; padding: 5px 10px;">View</button>
                </td>
            `;
        });
    } catch (error) {
        console.error('Error loading budget projects:', error);
        document.getElementById('budget-projects-body').innerHTML = 
            '<tr><td colspan="6" style="color: red;">Failed to load budget projects</td></tr>';
    }
}

// Open Budget Modal
function openBudgetModal() {
    document.getElementById('budgetModal').style.display = 'block';
    document.getElementById('budgetForm').reset();
    document.getElementById('budgetAlert').innerHTML = '';
}

// Close Budget Modal
function closeBudgetModal() {
    document.getElementById('budgetModal').style.display = 'none';
}

// Submit Budget Project
async function submitBudgetProject(event) {
    event.preventDefault();
    const alertDiv = document.getElementById('budgetAlert');
    alertDiv.innerHTML = '';

    const formData = new FormData(event.target);
    const projectData = {
        project_name: formData.get('title'),
        title: formData.get('title'),
        description: formData.get('description'),
        budget_amount: parseFloat(formData.get('budget_amount'))
    };

    try {
        const response = await fetch(`${API_BASE}/budget/projects`, {
            method: 'POST',
            headers: getAuthHeader(),
            body: JSON.stringify(projectData)
        });

        const data = await response.json();

        if (!response.ok) {
            alertDiv.innerHTML = `<div style="color: #721c24; background: #f8d7da; padding: 10px; border-radius: 5px; margin: 10px 0;">${data.error || 'Failed to create project'}</div>`;
            return;
        }

        alertDiv.innerHTML = `<div style="color: #155724; background: #d4edda; padding: 10px; border-radius: 5px; margin: 10px 0;">✓ Budget project created successfully!</div>`;
        
        setTimeout(() => {
            closeBudgetModal();
            loadBudgetProjects();
        }, 1500);

    } catch (error) {
        console.error('Error creating budget project:', error);
        alertDiv.innerHTML = `<div style="color: #721c24; background: #f8d7da; padding: 10px; border-radius: 5px; margin: 10px 0;">Error: ${error.message}</div>`;
    }
}

// Open Voting for Project
async function openVoting(projectId) {
    if (!confirm('Open voting for this project? Citizens will be able to vote.')) return;

    try {
        const response = await fetch(`${API_BASE}/budget/projects/${projectId}/open-voting`, {
            method: 'PATCH',
            headers: getAuthHeader(),
            body: JSON.stringify({})
        });

        const data = await response.json();

        if (!response.ok) {
            alert(`Error: ${data.error || 'Failed to open voting'}`);
            return;
        }

        alert('Voting opened successfully!');
        loadBudgetProjects();
    } catch (error) {
        console.error('Error opening voting:', error);
        alert(`Error: ${error.message}`);
    }
}

// Close Voting for Project
async function closeVoting(projectId) {
    if (!confirm('Close voting for this project?')) return;

    try {
        const response = await fetch(`${API_BASE}/budget/projects/${projectId}/close-voting`, {
            method: 'PATCH',
            headers: getAuthHeader(),
            body: JSON.stringify({})
        });

        const data = await response.json();

        if (!response.ok) {
            alert(`Error: ${data.error || 'Failed to close voting'}`);
            return;
        }

        alert('Voting closed successfully!');
        loadBudgetProjects();
    } catch (error) {
        console.error('Error closing voting:', error);
        alert(`Error: ${error.message}`);
    }
}

// View Project Details
async function viewProject(projectId) {
    try {
        const response = await fetch(`${API_BASE}/budget/projects/${projectId}`, {
            headers: getAuthHeader()
        });

        if (!response.ok) throw new Error('Failed to load project');
        
        const data = await response.json();
        const project = data.project || data;

        alert(`Project: ${project.title || project.project_name}
        
Description: ${project.description || 'N/A'}
Budget: ${(project.budget_amount || 0).toFixed(2)} TND
Status: ${project.status || 'pending'}
Votes For: ${project.votes_for || 0}
Votes Against: ${project.votes_against || 0}
Created: ${new Date(project.created_at).toLocaleString()}`);
    } catch (error) {
        console.error('Error viewing project:', error);
        alert(`Error: ${error.message}`);
    }
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', function() {
    if (!getToken()) {
        window.location.href = '/common_login/';
        return;
    }

    loadOverview();
    // Expose for inline handlers
    window.logout = logout;
    window.showSection = showSection;
    // Fallback: bind inline handlers explicitly
    bindInlineHandlers();
});

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

// ============================================================================
// DOCUMENT REQUIREMENTS MANAGEMENT
// ============================================================================

async function loadDocumentRequirements() {
    try {
        const response = await fetch(`${API_BASE}/municipal/document-requirements`, {
            headers: getAuthHeader()
        });

        if (!response.ok) throw new Error('Failed to load requirements');
        const data = await response.json();
        
        // Render property requirements
        const propertyBody = document.getElementById('property-reqs-body');
        propertyBody.innerHTML = '';
        
        const propertyReqs = data.by_type?.property || [];
        if (propertyReqs.length === 0) {
            propertyBody.innerHTML = '<tr><td colspan="4">No requirements defined</td></tr>';
        } else {
            propertyReqs.forEach(req => {
                const row = propertyBody.insertRow();
                row.innerHTML = `
                    <td>${req.document_name}</td>
                    <td><code>${req.document_code}</code></td>
                    <td><span class="status-badge ${req.is_mandatory ? 'status-approved' : 'status-pending'}">${req.is_mandatory ? 'Yes' : 'No'}</span></td>
                    <td>
                        <button class="button" onclick="editDocReq(${req.id})" style="font-size: 0.9em; padding: 5px 10px;">Edit</button>
                        <button class="button" onclick="deleteDocReq(${req.id})" style="font-size: 0.9em; padding: 5px 10px; background: #dc3545;">Delete</button>
                    </td>
                `;
            });
        }
        
        // Render land requirements
        const landBody = document.getElementById('land-reqs-body');
        landBody.innerHTML = '';
        
        const landReqs = data.by_type?.land || [];
        if (landReqs.length === 0) {
            landBody.innerHTML = '<tr><td colspan="4">No requirements defined</td></tr>';
        } else {
            landReqs.forEach(req => {
                const row = landBody.insertRow();
                row.innerHTML = `
                    <td>${req.document_name}</td>
                    <td><code>${req.document_code}</code></td>
                    <td><span class="status-badge ${req.is_mandatory ? 'status-approved' : 'status-pending'}">${req.is_mandatory ? 'Yes' : 'No'}</span></td>
                    <td>
                        <button class="button" onclick="editDocReq(${req.id})" style="font-size: 0.9em; padding: 5px 10px;">Edit</button>
                        <button class="button" onclick="deleteDocReq(${req.id})" style="font-size: 0.9em; padding: 5px 10px; background: #dc3545;">Delete</button>
                    </td>
                `;
            });
        }
    } catch (error) {
        console.error('Error loading document requirements:', error);
        document.getElementById('property-reqs-body').innerHTML = 
            '<tr><td colspan="4" style="color: red;">Failed to load requirements</td></tr>';
        document.getElementById('land-reqs-body').innerHTML = 
            '<tr><td colspan="4" style="color: red;">Failed to load requirements</td></tr>';
    }
}

function openDocReqModal() {
    document.getElementById('docReqForm').reset();
    document.getElementById('docReqAlert').innerHTML = '';
    document.getElementById('docReqModal').style.display = 'block';
}

function closeDocReqModal() {
    document.getElementById('docReqModal').style.display = 'none';
}

async function submitDocumentRequirement(event) {
    event.preventDefault();
    const alertDiv = document.getElementById('docReqAlert');
    alertDiv.innerHTML = '';

    const formData = {
        declaration_type: document.querySelector('select[name="declaration_type"]').value,
        document_name: document.querySelector('input[name="document_name"]').value,
        document_code: document.querySelector('input[name="document_code"]').value,
        description: document.querySelector('textarea[name="description"]').value,
        is_mandatory: document.querySelector('input[name="is_mandatory"]').checked
    };

    try {
        const response = await fetch(`${API_BASE}/municipal/document-requirements`, {
            method: 'POST',
            headers: getAuthHeader(),
            body: JSON.stringify(formData)
        });

        const result = await response.json();

        if (!response.ok) {
            alertDiv.innerHTML = `<div style="color: red; padding: 10px; background: #ffe6e6; border-radius: 5px;">${result.error || 'Error creating requirement'}</div>`;
            return;
        }

        alertDiv.innerHTML = `<div style="color: green; padding: 10px; background: #e6ffe6; border-radius: 5px;">Document requirement added successfully!</div>`;
        setTimeout(() => {
            closeDocReqModal();
            loadDocumentRequirements();
        }, 1500);
    } catch (error) {
        console.error('Error:', error);
        alertDiv.innerHTML = `<div style="color: red; padding: 10px; background: #ffe6e6; border-radius: 5px;">Error: ${error.message}</div>`;
    }
}

async function deleteDocReq(reqId) {
    if (!confirm('Are you sure you want to delete this requirement?')) return;

    try {
        const response = await fetch(`${API_BASE}/municipal/document-requirements/${reqId}`, {
            method: 'DELETE',
            headers: getAuthHeader()
        });

        if (!response.ok) throw new Error('Failed to delete requirement');
        
        alert('Document requirement deleted successfully');
        loadDocumentRequirements();
    } catch (error) {
        console.error('Error deleting requirement:', error);
        alert(`Error: ${error.message}`);
    }
}

function editDocReq(reqId) {
    alert('Edit functionality coming soon');
}

// Enhance showSection to load document requirements
const originalShowSection = showSection;
function showSection(sectionId, el) {
    document.querySelectorAll('.section').forEach(section => section.style.display = 'none');
    document.querySelectorAll('.nav-link').forEach(link => link.classList.remove('active'));
    document.getElementById(sectionId).style.display = 'block';
    if (el) el.classList.add('active');

    if (sectionId === 'staff') loadStaff();
    else if (sectionId === 'statistics') loadStatistics();
    else if (sectionId === 'overview') loadOverview();
    else if (sectionId === 'budget') loadBudgetProjects();
    else if (sectionId === 'doc-requirements') loadDocumentRequirements();
}

