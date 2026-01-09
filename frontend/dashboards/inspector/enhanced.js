/**
 * Inspector Dashboard wiring for the real API surface.
 * Pulls properties/lands awaiting inspection plus report history.
 */

// Use relative URLs so frontend works behind proxy/reverse-proxy (nginx, etc.)
const API_BASE = '/api/v1';
const EXTERNAL_BASE = `${API_BASE}/external`;

function getToken() {
    return localStorage.getItem('access_token');
}

function getAuthHeader() {
    return {
        'Authorization': `Bearer ${getToken()}`,
        'Content-Type': 'application/json'
    };
}

/**
 * Enhanced error handling for external API calls.
 * Distinguishes between: no results, auth errors, rate limits, timeouts, API failures.
 */
function getExternalAPIErrorMessage(response, error, defaultMsg) {
    if (!response || !response.ok) {
        const status = response?.status;
        if (status === 401) return '❌ Not authorized. Please log in.';
        if (status === 403) return '❌ Access denied to external APIs.';
        if (status === 429) return '⏱️  Rate limit exceeded. Wait a moment and try again.';
        if (status === 502 || status === 503) return '⚠️  Service temporarily unavailable. Try again in a moment.';
        if (status === 504) return '⏱️  Request timeout. The service took too long to respond.';
        return defaultMsg;
    }
    if (error.name === 'AbortError') return '⏱️  Request timeout.';
    return defaultMsg;
}

/**
 * Make a fetch request with timeout, proper error handling, and auth.
 */
async function fetchExternalAPI(url, timeoutMs = 10000) {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), timeoutMs);
    try {
        const res = await fetch(url, {
            headers: getAuthHeader(),
            signal: controller.signal
        });
        return { res, error: null };
    } catch (error) {
        return { res: null, error };
    } finally {
        clearTimeout(timeoutId);
    }
}

function showSection(sectionId, el) {
    document.querySelectorAll('.section').forEach(el => el.style.display = 'none');
    document.querySelectorAll('.nav-link').forEach(x => x.classList.remove('active'));
    document.getElementById(sectionId).style.display = 'block';
    if (el) el.classList.add('active');

    if (sectionId === 'to-inspect') loadToInspect();
    else if (sectionId === 'my-reports') loadMyReports();
    else if (sectionId === 'satellite') loadSatelliteSection();
    else if (sectionId === 'overview') loadOverview();
}

async function loadOverview() {
    try {
        const [propsRes, landsRes, reportsRes] = await Promise.all([
            fetch(`${API_BASE}/inspector/properties/to-inspect`, { headers: getAuthHeader() }),
            fetch(`${API_BASE}/inspector/lands/to-inspect`, { headers: getAuthHeader() }),
            fetch(`${API_BASE}/inspector/my-reports`, { headers: getAuthHeader() })
        ]);

        const props = await propsRes.json();
        const lands = await landsRes.json();
        const reports = await reportsRes.json();

        document.getElementById('prop-count').textContent = props.count || 0;
        document.getElementById('land-count').textContent = lands.count || 0;
        document.getElementById('report-count').textContent = reports.total || 0;
        document.getElementById('verified-count').textContent =
            (reports.inspections || []).filter(r => r.status === 'completed').length;
    } catch (error) {
        console.error('Error loading overview:', error);
    }
}

async function loadToInspect() {
    await Promise.all([loadPropertiesToInspect(), loadLandsToInspect()]);
}

async function loadPropertiesToInspect() {
    try {
        const response = await fetch(`${API_BASE}/inspector/properties/to-inspect`, { headers: getAuthHeader() });
        const data = await response.json();
        const tbody = document.getElementById('properties-body');
        tbody.innerHTML = '';

        if (!data.properties || data.properties.length === 0) {
            tbody.innerHTML = '<tr><td colspan="5">No properties awaiting inspection.</td></tr>';
            return;
        }

        data.properties.forEach(prop => {
            const row = tbody.insertRow();
            row.innerHTML = `
                <td>${prop.owner_id}</td>
                <td>${prop.street_address}, ${prop.city}</td>
                <td>${prop.surface_couverte || '-'} m2</td>
                <td><span class="status-badge status-${prop.status}">${prop.status}</span></td>
                <td><button class="button" onclick="prefillReport(${prop.id}, 'property')">Prepare Report</button></td>
            `;
        });
    } catch (error) {
        console.error('Error loading properties to inspect:', error);
        document.getElementById('properties-body').innerHTML = '<tr><td colspan="5">Failed to load properties</td></tr>';
    }
}

async function loadLandsToInspect() {
    try {
        const response = await fetch(`${API_BASE}/inspector/lands/to-inspect`, { headers: getAuthHeader() });
        const data = await response.json();
        const tbody = document.getElementById('lands-body');
        tbody.innerHTML = '';

        if (!data.lands || data.lands.length === 0) {
            tbody.innerHTML = '<tr><td colspan="5">No lands awaiting inspection.</td></tr>';
            return;
        }

        data.lands.forEach(land => {
            const row = tbody.insertRow();
            row.innerHTML = `
                <td>${land.owner_id}</td>
                <td>${land.street_address || 'N/A'}, ${land.city}</td>
                <td>${land.surface || '-'} m2</td>
                <td><span class="status-badge status-${land.status}">${land.status}</span></td>
                <td><button class="button" onclick="prefillReport(${land.id}, 'land')">Prepare Report</button></td>
            `;
        });
    } catch (error) {
        console.error('Error loading lands to inspect:', error);
        document.getElementById('lands-body').innerHTML = '<tr><td colspan="5">Failed to load lands</td></tr>';
    }
}

function prefillReport(itemId, itemType) {
    document.getElementById('item-id').value = itemId;
    document.getElementById('item-type').value = itemType;
    showSection('submit-report', document.querySelector('[onclick*="submit-report"]'));
}

async function handleSubmitReport(event) {
    event.preventDefault();
    const id = document.getElementById('item-id').value.trim();
    const type = document.getElementById('item-type').value;
    const verified = document.getElementById('satellite-verified').value === 'true';
    const discrepancies = document.getElementById('discrepancies').value === 'true';
    const evidence = document.getElementById('evidence-urls').value
        .split(',')
        .map(url => url.trim())
        .filter(Boolean);
    const recommendation = document.getElementById('recommendation').value.trim();

    if (!id || !type) {
        document.getElementById('report-message').textContent = 'Select the item to report on.';
        return;
    }

    const payload = {
        property_id: type === 'property' ? Number(id) : null,
        land_id: type === 'land' ? Number(id) : null,
        satellite_verified: verified,
        discrepancies_found: discrepancies,
        evidence_urls: evidence,
        recommendation,
        notes: recommendation
    };

    try {
        const response = await fetch(`${API_BASE}/inspector/report`, {
            method: 'POST',
            headers: getAuthHeader(),
            body: JSON.stringify(payload)
        });
        const data = await response.json();

        if (!response.ok) {
            document.getElementById('report-message').innerHTML =
                `<div class="alert alert-error">${data.error || 'Unable to submit report.'}</div>`;
            return;
        }

        document.getElementById('report-message').innerHTML =
            '<div class="alert alert-success">Report submitted successfully! You can now upload inspection photos.</div>';
        
        // Store report ID and show document upload section
        document.getElementById('inspection_report_id').value = data.report.id || id;
        document.getElementById('inspectionForm').style.display = 'none';
        document.getElementById('inspectionDocUpload').style.display = 'block';
        
        loadOverview();
        loadMyReports();
        loadToInspect();
    } catch (error) {
        document.getElementById('report-message').innerHTML =
            '<div class="alert alert-error">Network error while submitting report.</div>';
    }
}

// Inspection Document Upload Functions
function showInspectionDocUpload() {
    document.getElementById('inspectionDocUpload').style.display = 'block';
}

async function uploadInspectionDocument() {
    const reportId = document.getElementById('inspection_report_id').value;
    const docType = document.getElementById('inspection_doc_type').value;
    const fileInput = document.getElementById('inspection_doc_file');
    const statusDiv = document.getElementById('inspection_doc_status');
    
    if (!reportId) {
        statusDiv.innerHTML = '<div class="alert alert-error">Please submit the inspection report first</div>';
        return;
    }
    
    if (!fileInput.files || fileInput.files.length === 0) {
        statusDiv.innerHTML = '<div class="alert alert-error">Please select a file</div>';
        return;
    }
    
    const file = fileInput.files[0];
    if (file.size > 10 * 1024 * 1024) {
        statusDiv.innerHTML = '<div class="alert alert-error">File size must be less than 10MB</div>';
        return;
    }
    
    const formData = new FormData();
    formData.append('file', file);
    formData.append('document_type', docType);
    
    statusDiv.innerHTML = '<div class="alert alert-info">Uploading...</div>';
    
    try {
        const response = await fetch(`${API_BASE}/documents/declarations/${reportId}/documents`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${getToken()}`
            },
            body: formData
        });
        
        const result = await response.json();
        
        if (response.ok) {
            statusDiv.innerHTML = '<div class="alert alert-success">Document uploaded successfully!</div>';
            fileInput.value = '';
            loadInspectionDocuments(reportId);
        } else {
            statusDiv.innerHTML = '<div class="alert alert-error">' + (result.error || 'Upload failed') + '</div>';
        }
    } catch (error) {
        statusDiv.innerHTML = '<div class="alert alert-error">Network error. Please try again.</div>';
    }
}

async function loadInspectionDocuments(reportId) {
    try {
        const response = await fetch(`${API_BASE}/documents/declarations/${reportId}/documents`, {
            headers: getAuthHeader()
        });
        const result = await response.json();
        
        const listDiv = document.getElementById('inspection_doc_list');
        if (result.documents && result.documents.length > 0) {
            listDiv.innerHTML = '<h5 style="margin-bottom: 10px;">Uploaded Documents:</h5>' +
                result.documents.map(doc => `
                    <div style="padding: 8px; background: white; border-radius: 4px; margin-bottom: 5px; display: flex; justify-content: space-between; align-items: center;">
                        <span>📄 ${doc.document_type} - ${doc.status}</span>
                        <a href="${API_BASE}/documents/documents/${doc.id}/file" target="_blank" class="button" style="padding: 4px 8px; font-size: 12px;">View</a>
                    </div>
                `).join('');
        }
    } catch (error) {
        console.error('Error loading documents:', error);
    }
}

function completeInspectionUpload() {
    document.getElementById('inspectionForm').style.display = 'block';
    document.getElementById('inspectionDocUpload').style.display = 'none';
    document.getElementById('inspectionForm').reset();
}

async function loadMyReports() {
    try {
        const response = await fetch(`${API_BASE}/inspector/my-reports`, { headers: getAuthHeader() });
        const data = await response.json();
        const tbody = document.getElementById('reports-body');
        tbody.innerHTML = '';

        if (!data.inspections || data.inspections.length === 0) {
            tbody.innerHTML = '<tr><td colspan="6">No reports submitted yet.</td></tr>';
            return;
        }

        data.inspections.forEach(report => {
            const row = tbody.insertRow();
            const date = report.date ? new Date(report.date).toLocaleDateString() : '-';
            const itemId = report.property_id || report.land_id;
            const type = report.property_id ? 'Property' : 'Land';

            row.innerHTML = `
                <td>${date}</td>
                <td>${itemId || '-'}</td>
                <td>${type}</td>
                <td>${report.status}</td>
                <td>${report.discrepancies_found ? 'Yes' : 'No'}</td>
                <td><button class="button" onclick="viewReport(${report.id})">Details</button></td>
            `;
        });
    } catch (error) {
        console.error('Error loading reports:', error);
        document.getElementById('reports-body').innerHTML = '<tr><td colspan="6">Failed to load reports</td></tr>';
    }
}

async function viewReport(inspectionId) {
    try {
        const response = await fetch(`${API_BASE}/inspector/report/${inspectionId}`, { headers: getAuthHeader() });
        const data = await response.json();

        if (!response.ok) {
            alert(data.error || 'Unable to load report.');
            return;
        }

        alert(`Report #${data.id}
Status: ${data.status}
Notes: ${data.notes || 'N/A'}
Recommendation: ${data.recommendation || 'N/A'}`);
    } catch (error) {
        alert('Failed to load report details.');
    }
}

async function getSatelliteInfo() {
    const id = document.getElementById('prop-id-satellite').value.trim();
    const infoDiv = document.getElementById('satellite-info');
    infoDiv.textContent = '';

    if (!id) {
        infoDiv.textContent = 'Enter a property ID first.';
        return;
    }

    const endpoints = [
        `${API_BASE}/inspector/property/${id}/satellite-imagery`,
        `${API_BASE}/inspector/land/${id}/satellite-imagery`
    ];

    for (const endpoint of endpoints) {
        try {
            const response = await fetch(endpoint, { headers: getAuthHeader() });
            const data = await response.json();

            if (!response.ok) {
                continue;
            }

            infoDiv.innerHTML = `
                <h4>Imagery Information</h4>
                <p>Provider: ${data.provider}</p>
                <p>Resolution: ${data.resolution || 'N/A'}</p>
                <p>License: ${data.license || 'N/A'}</p>
                <p>URL: <a href="${data.url}" target="_blank">${data.url}</a></p>
            `;
            return;
        } catch (error) {
            continue;
        }
    }

    infoDiv.innerHTML = '<div class="alert alert-error">Unable to fetch imagery for that ID.</div>';
}

// Satellite Imagery Section backed by external API endpoints
let inspEventsLoaded = false;

function loadSatelliteSection() {
    if (!inspEventsLoaded) inspLoadNasaEvents();
}

async function inspRunGeocodeLookup() {
    const address = (document.getElementById('insp_geo_address')?.value || '').trim();
    const target = document.getElementById('insp-geocode-results');
    if (!address) {
        target.innerHTML = '<div class="alert alert-error">Enter an address first.</div>';
        return;
    }
    target.innerHTML = '<div class="alert alert-info">Looking up address…</div>';
    
    const { res, error } = await fetchExternalAPI(`${EXTERNAL_BASE}/geocode?q=${encodeURIComponent(address)}`);
    
    if (error) {
        const msg = getExternalAPIErrorMessage(res, error, 'Geocoding failed. Check your connection.');
        target.innerHTML = `<div class="alert alert-error">${msg}</div>`;
        return;
    }
    
    const data = await res.json();
    if (!res.ok) {
        const msg = getExternalAPIErrorMessage(res, null, data.error || 'Geocoding failed');
        target.innerHTML = `<div class="alert alert-error">${msg}</div>`;
        return;
    }
    
    const items = data.results || [];
    if (!items.length) {
        target.innerHTML = '<div class="alert alert-warning">No address matches found. Try a different query.</div>';
        return;
    }
    
    const first = items[0];
    target.innerHTML = `
        <div class="alert alert-success">Found ${items.length} result(s).</div>
        <div style="margin-top:10px;">
            <div><strong>${first.display_name || 'Unnamed location'}</strong></div>
            <div>Lat: ${first.lat.toFixed(6)}, Lon: ${first.lon.toFixed(6)}</div>
            <div>Type: ${first.type || 'n/a'} (${first.category || 'n/a'})</div>
        </div>
    `;
    document.getElementById('insp_geo_lat').value = first.lat;
    document.getElementById('insp_geo_lng').value = first.lon;
}

async function inspRunReverseGeocode() {
    const lat = document.getElementById('insp_geo_lat')?.value;
    const lon = document.getElementById('insp_geo_lng')?.value;
    const target = document.getElementById('insp-geocode-results');
    if (!lat || !lon) {
        target.innerHTML = '<div class="alert alert-error">Provide both latitude and longitude.</div>';
        return;
    }
    target.innerHTML = '<div class="alert alert-info">Resolving coordinates…</div>';
    
    const { res, error } = await fetchExternalAPI(`${EXTERNAL_BASE}/reverse-geocode?lat=${encodeURIComponent(lat)}&lon=${encodeURIComponent(lon)}`);
    
    if (error) {
        const msg = getExternalAPIErrorMessage(res, error, 'Reverse geocoding failed. Check your connection.');
        target.innerHTML = `<div class="alert alert-error">${msg}</div>`;
        return;
    }
    
    const data = await res.json();
    if (!res.ok) {
        const msg = getExternalAPIErrorMessage(res, null, data.error || 'Reverse geocoding failed');
        target.innerHTML = `<div class="alert alert-error">${msg}</div>`;
        return;
    }
    
    const address = data.address || {};
    target.innerHTML = `
        <div class="alert alert-success">Reverse geocode success.</div>
        <div style="margin-top:10px;">
            <div><strong>${data.display_name || 'Unnamed location'}</strong></div>
            <div>Type: ${data.type || 'n/a'} (${data.category || 'n/a'})</div>
            <div style="font-size:13px; color:#555;">${Object.entries(address).slice(0,5).map(([k,v]) => `${k}: ${v}`).join(', ')}</div>
        </div>
    `;
}

async function inspRunNasaImagerySearch() {
    const query = (document.getElementById('insp_nasa_query')?.value || 'Tunisia earth').trim();
    const target = document.getElementById('insp-nasa-imagery-results');
    target.innerHTML = '<div class="alert alert-info">Searching NASA imagery…</div>';
    
    const { res, error } = await fetchExternalAPI(`${EXTERNAL_BASE}/nasa/imagery?q=${encodeURIComponent(query)}&page_size=5`);
    
    if (error) {
        const msg = getExternalAPIErrorMessage(res, error, 'NASA search failed. Check your connection.');
        target.innerHTML = `<div class="alert alert-error">${msg}</div>`;
        return;
    }
    
    const data = await res.json();
    if (!res.ok) {
        const msg = getExternalAPIErrorMessage(res, null, data.error || 'NASA imagery search failed');
        target.innerHTML = `<div class="alert alert-error">${msg}</div>`;
        return;
    }
    
    const items = data.items || [];
    if (!items.length) {
        target.innerHTML = '<div class="alert alert-warning">No imagery available for this location or timeframe. Try a broader search.</div>';
        return;
    }
    
    target.innerHTML = items.map(item => `
        <div style="padding:12px; border:1px solid #e5e7eb; border-radius:6px; margin-bottom:10px; background:#f9fafb;">
            <div style="font-weight:600;">${item.title || 'Untitled'}</div>
            <div style="font-size:13px; color:#555;">${item.description ? item.description.substring(0,140) + '…' : 'No description'}</div>
            ${item.href ? `<div style="margin-top:6px;"><a href="${item.href}" target="_blank" class="button" style="padding:6px 10px; font-size:12px;">Open Image</a></div>` : ''}
        </div>
    `).join('');
}

async function inspLoadNasaEvents() {
    const target = document.getElementById('insp-nasa-events');
    target.innerHTML = '<div class="alert alert-info">Loading recent Earth events…</div>';
    
    const { res, error } = await fetchExternalAPI(`${EXTERNAL_BASE}/nasa/events?limit=6`);
    
    if (error) {
        const msg = getExternalAPIErrorMessage(res, error, 'Failed to load Earth events.');
        target.innerHTML = `<div class="alert alert-error">${msg}</div>`;
        return;
    }
    
    const data = await res.json();
    if (!res.ok) {
        const msg = getExternalAPIErrorMessage(res, null, data.error || 'Events unavailable');
        target.innerHTML = `<div class="alert alert-error">${msg}</div>`;
        return;
    }
    
    const events = data.events || [];
    if (!events.length) {
        target.innerHTML = '<div class="alert alert-warning">No Earth events currently reported in your region.</div>';
        return;
    }
    
    target.innerHTML = events.map(ev => `
        <div style="padding:12px; border:1px solid #e5e7eb; border-radius:6px; margin-bottom:8px; background:#f9fafb;">
            <div style="font-weight:600;">${ev.title || 'Event'}</div>
            <div style="font-size:13px; color:#555;">Updated: ${ev.updated || 'n/a'}</div>
            ${ev.categories && ev.categories.length ? `<div style="font-size:12px; color:#444;">Categories: ${ev.categories.map(c => c.title || c).join(', ')}</div>` : ''}
            ${ev.geometry ? `<div style="font-size:12px; color:#444;">Location: ${JSON.stringify(ev.geometry[0]?.coordinates || ev.geometry)}</div>` : ''}
        </div>
    `).join('');
}

async function submitImageVerification() {
    const imageUrl = (document.getElementById('verify_image_url')?.value || '').trim();
    const status = document.getElementById('verify_status')?.value;
    const severity = document.getElementById('verify_severity')?.value;
    const notes = document.getElementById('verify_notes')?.value;
    const photoAttached = document.getElementById('verify_photo_attached')?.checked;
    const source = document.getElementById('verify_image_source')?.value;
    
    const resultDiv = document.getElementById('verify-submission-status');
    
    if (!status) {
        resultDiv.innerHTML = '<div class="alert alert-error">Please select a verification status.</div>';
        return;
    }
    
    resultDiv.innerHTML = '<div class="alert alert-info">Submitting verification…</div>';
    
    try {
        const payload = {
            satellite_image_url: imageUrl || null,
            image_source: source,
            verification_status: status,
            discrepancy_severity: severity || null,
            discrepancy_notes: notes,
            has_photo_evidence: photoAttached,
            verified_at: new Date().toISOString()
        };
        
        const res = await fetch(`${API_BASE}/inspector/satellite-verification`, {
            method: 'POST',
            headers: getAuthHeader(),
            body: JSON.stringify(payload)
        });
        
        const data = await res.json();
        
        if (!res.ok) {
            resultDiv.innerHTML = `<div class="alert alert-error">${data.error || 'Failed to submit verification'}</div>`;
            return;
        }
        
        resultDiv.innerHTML = `<div class="alert alert-success">✓ Verification recorded successfully. ID: ${data.id}</div>`;
        
        // Clear form
        document.getElementById('verify_image_url').value = '';
        document.getElementById('verify_status').value = '';
        document.getElementById('verify_severity').value = '';
        document.getElementById('verify_notes').value = '';
        document.getElementById('verify_photo_attached').checked = false;
        
        // Reload data if available
        loadToInspect();
    } catch (error) {
        resultDiv.innerHTML = `<div class="alert alert-error">Error submitting verification: ${error.message}</div>`;
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
    window.showSection = showSection;
