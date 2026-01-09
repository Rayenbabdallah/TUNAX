/**
 * Citizen Dashboard - Enhanced Functionality
 * Complete implementation with modals, forms, and API integration
 */

// Use relative URLs so frontend works behind proxy/reverse-proxy (nginx, etc.)
const API_BASE = '/api/v1';
const EXTERNAL_BASE = `${API_BASE}/external`;

// State for maps and dropdowns
let propertyMap, propertyMarker;
let landMap, landMarker;
let communesCache = [];
let userCitiesCache = [];
const OTHER_VALUE = '__other__';

function getToken() {
    return localStorage.getItem('access_token');
}
    // Expose for inline handlers
    window.logout = logout;
    window.showSection = showSection;

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

// Section Navigation
function showSection(sectionId, el) {
    document.querySelectorAll('.section').forEach(el => el.style.display = 'none');
    document.querySelectorAll('.nav-link').forEach(x => x.classList.remove('active'));
    document.getElementById(sectionId).style.display = 'block';
    if (el) el.classList.add('active');

    if (sectionId === 'properties') loadProperties();
    else if (sectionId === 'lands') loadLands();
    else if (sectionId === 'taxes') loadTaxes();
    else if (sectionId === 'payments') loadPayments();
    else if (sectionId === 'disputes') loadDisputes();
    else if (sectionId === 'permits') loadPermits();
    else if (sectionId === 'reclamations') {
        populateReclamationCities();
        loadReclamations();
    }
    else if (sectionId === 'location-tools') loadLocationTools();
    else if (sectionId === 'overview') loadOverview();
}

async function ensureUserCities() {
    if (userCitiesCache.length) return userCitiesCache;
    const cities = new Set();
    try {
        const resProps = await fetch(`${API_BASE}/tib/properties`, { headers: getAuthHeader() });
        if (resProps.ok) {
            const data = await resProps.json();
            (data.properties || []).forEach(p => p.city && cities.add(p.city));
        }
    } catch {}
    try {
        const resLands = await fetch(`${API_BASE}/ttnb/lands`, { headers: getAuthHeader() });
        if (resLands.ok) {
            const data = await resLands.json();
            (data.lands || []).forEach(l => l.city && cities.add(l.city));
        }
    } catch {}
    userCitiesCache = Array.from(cities);
    return userCitiesCache;
}

async function populateReclamationCities() {
    const select = document.getElementById('reclamation_city');
    if (!select) return;
    select.innerHTML = '<option value="">Loading…</option>';
    const cities = await ensureUserCities();
    if (!cities.length) {
        select.innerHTML = '<option value="">No municipalities found</option>';
        select.disabled = true;
        return;
    }
    select.disabled = false;
    select.innerHTML = '<option value="">Select…</option>' + cities.map(c => `<option value="${c}">${c}</option>`).join('');
}

async function fetchRequiredDocuments(declarationType, communeId, targetElementId) {
    const target = document.getElementById(targetElementId);
    if (!communeId) {
        target.innerHTML = '<em>Select a municipality to load required documents.</em>';
        return;
    }

    target.innerHTML = '<span style="color:#4b5563;">Loading required documents…</span>';
    try {
        const res = await fetch(`${API_BASE}/public/document-requirements?declaration_type=${declarationType}&commune_id=${communeId}`);
        const data = await res.json();

        if (!res.ok) {
            target.innerHTML = `<span style="color:#b91c1c;">${data.error || 'Unable to load requirements'}</span>`;
            return;
        }

        if (!data.documents || data.documents.length === 0) {
            target.innerHTML = '<em>No mandatory documents configured for this municipality.</em>';
            return;
        }

        target.innerHTML = data.documents.map(doc => `
            <div style="padding:6px 8px; background:#fff; border:1px solid #e5e7eb; border-radius:6px; margin-bottom:6px; display:flex; align-items:center; gap:8px;">
                <span style="font-size:14px; font-weight:600; color:#111827;">${doc.document_name}</span>
                <span style="font-size:12px; color:#6b7280;">(${doc.document_code})</span>
                ${doc.is_mandatory ? '<span class="status-badge status-approved">Mandatory</span>' : '<span class="status-badge status-pending">Optional</span>'}
                ${doc.description ? `<span style="font-size:12px; color:#4b5563;">- ${doc.description}</span>` : ''}
            </div>
        `).join('');
    } catch (error) {
        console.error('Failed to load required documents', error);
        target.innerHTML = '<span style="color:#b91c1c;">Failed to load requirements</span>';
    }
}

// Overview Loading
async function loadOverview() {
    try {
        const [propsRes, landsRes, taxRes] = await Promise.all([
            fetch(`${API_BASE}/tib/properties`, { headers: getAuthHeader() }),
            fetch(`${API_BASE}/ttnb/lands`, { headers: getAuthHeader() }),
            fetch(`${API_BASE}/tib/my-taxes`, { headers: getAuthHeader() })
        ]);

        const props = await propsRes.json();
        const lands = await landsRes.json();
        const taxes = await taxRes.json();

        document.getElementById('property-count').textContent = props.properties?.length || 0;
        document.getElementById('land-count').textContent = lands.lands?.length || 0;
        
        const totalDue = taxes.taxes?.reduce((sum, t) => t.status === 'pending' ? sum + t.total_amount : sum, 0) || 0;
        const totalPaid = taxes.taxes?.reduce((sum, t) => t.status === 'paid' ? sum + t.total_amount : sum, 0) || 0;
        
        document.getElementById('total-due').textContent = totalDue.toFixed(2) + ' TND';
        document.getElementById('total-paid').textContent = totalPaid.toFixed(2) + ' TND';
    } catch (error) {
        console.error('Error loading overview:', error);
    }
}

// Properties
async function loadProperties() {
    try {
        const response = await fetch(`${API_BASE}/tib/properties`, { headers: getAuthHeader() });
        const data = await response.json();
        const tbody = document.getElementById('properties-body');
        tbody.innerHTML = '';

        if (!data.properties || data.properties.length === 0) {
            tbody.innerHTML = '<tr><td colspan="5">No properties declared. Click "Declare New Property" to add one.</td></tr>';
            return;
        }

        data.properties.forEach(prop => {
            const row = tbody.insertRow();
            row.innerHTML = `
                <td>${prop.street_address}, ${prop.city}</td>
                <td>${prop.surface_couverte}</td>
                <td>${prop.affectation}</td>
                <td><span class="status-badge status-${prop.status}">${prop.status}</span></td>
                <td><button class="button" onclick="viewPropertyDetail(${prop.id})">View</button></td>
            `;
        });
    } catch (error) {
        console.error('Error loading properties:', error);
        document.getElementById('properties-body').innerHTML = '<tr><td colspan="5">Error loading properties</td></tr>';
    }
}

function openPropertyModal() {
    document.getElementById('propertyModal').style.display = 'block';
    document.getElementById('propertyForm').reset();
    document.getElementById('propertyAlert').innerHTML = '';
    setupAddressUI('property');
}

async function submitProperty(event) {
    event.preventDefault();
    const form = event.target;
    let communeId = document.getElementById('property_commune').value;
    const communeOther = document.getElementById('property_commune_other').value.trim();
    let locality = document.getElementById('property_locality').value || '';
    const localityOther = document.getElementById('property_locality_other').value.trim();
    const mode = document.getElementById('property_address_mode').value;
    const street = document.getElementById('property_street_name').value.trim();
    const villa = document.getElementById('property_villa_number').value.trim();
    const res = document.getElementById('property_residence_name').value.trim();
    const apt = document.getElementById('property_apartment_number').value.trim();
    const lat = document.getElementById('property_lat').value;
    const lng = document.getElementById('property_lng').value;
    const surface_couverte = form.querySelector('[name="surface_couverte"]').value;
    const affectation = form.querySelector('[name="affectation"]').value;

    if (communeId === OTHER_VALUE) {
        communeId = await resolveOtherCommune(communeOther, 'propertyAlert');
        if (!communeId) return;
    }
    if (!communeId) {
        document.getElementById('propertyAlert').innerHTML = '<div class="alert alert-error">Please choose a municipality.</div>';
        return;
    }
    if (!street) {
        document.getElementById('propertyAlert').innerHTML = '<div class="alert alert-error">Street name is required.</div>';
        return;
    }

    if (locality === OTHER_VALUE) locality = localityOther;
    const payload = {
        commune_id: Number(communeId),
        address_mode: mode,
        street_name: street,
        locality,
        surface_couverte: Number(surface_couverte),
        affectation
    };
    if (mode === 'villa') payload.villa_number = villa;
    else {
        payload.residence_name = res;
        payload.apartment_number = apt;
    }
    if (lat && lng) {
        payload.latitude = Number(lat);
        payload.longitude = Number(lng);
    }

    try {
        const response = await fetch(`${API_BASE}/tib/properties`, {
            method: 'POST',
            headers: getAuthHeader(),
            body: JSON.stringify(payload)
        });

        const result = await response.json();
        
        if (response.ok) {
            document.getElementById('propertyAlert').innerHTML = 
                '<div class="alert alert-success">Property declared successfully! You can now upload supporting documents.</div>';
            
            // Store declaration ID and show document upload section
            document.getElementById('property_declaration_id').value = result.property.id;
            document.getElementById('propertyForm').style.display = 'none';
            document.getElementById('propertyDocUpload').style.display = 'block';
            document.getElementById('propertySubmitBtn').disabled = true;
            
            loadOverview();
        } else {
            document.getElementById('propertyAlert').innerHTML = 
                '<div class="alert alert-error">' + (result.error || 'Failed to declare property') + '</div>';
        }
    } catch (error) {
        document.getElementById('propertyAlert').innerHTML = 
            '<div class="alert alert-error">Network error. Please try again.</div>';
    }
}

// Document upload functions for property
async function uploadPropertyDocument() {
    const declarationId = document.getElementById('property_declaration_id').value;
    const docType = document.getElementById('property_doc_type').value;
    const fileInput = document.getElementById('property_doc_file');
    const statusDiv = document.getElementById('property_doc_status');
    
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
        const response = await fetch(`${API_BASE}/documents/declarations/${declarationId}/documents`, {
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
            loadPropertyDocuments(declarationId);
        } else {
            statusDiv.innerHTML = '<div class="alert alert-error">' + (result.error || 'Upload failed') + '</div>';
        }
    } catch (error) {
        statusDiv.innerHTML = '<div class="alert alert-error">Network error. Please try again.</div>';
    }
}

async function loadPropertyDocuments(declarationId) {
    try {
        const response = await fetch(`${API_BASE}/documents/declarations/${declarationId}/documents`, {
            headers: getAuthHeader()
        });
        const result = await response.json();
        
        const listDiv = document.getElementById('property_doc_list');
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

function skipPropertyDocuments() {
    closeModal('propertyModal');
    loadProperties();
    // Reset form for next use
    document.getElementById('propertyForm').style.display = 'block';
    document.getElementById('propertyDocUpload').style.display = 'none';
    document.getElementById('propertyForm').reset();
    document.getElementById('propertySubmitBtn').disabled = false;
}

// Lands
async function loadLands() {
    try {
        const response = await fetch(`${API_BASE}/ttnb/lands`, { headers: getAuthHeader() });
        const data = await response.json();
        const tbody = document.getElementById('lands-body');
        tbody.innerHTML = '';

        if (!data.lands || data.lands.length === 0) {
            tbody.innerHTML = '<tr><td colspan="5">No lands declared. Click "Declare New Land" to add one.</td></tr>';
            return;
        }

        data.lands.forEach(land => {
            const row = tbody.insertRow();
            row.innerHTML = `
                <td>${land.street_address}, ${land.city}</td>
                <td>${land.surface}</td>
                <td>${land.land_type}</td>
                <td><span class="status-badge status-${land.status}">${land.status}</span></td>
                <td><button class="button" onclick="viewLandDetail(${land.id})">View</button></td>
            `;
        });
    } catch (error) {
        console.error('Error loading lands:', error);
        document.getElementById('lands-body').innerHTML = '<tr><td colspan="5">Error loading lands</td></tr>';
    }
}

function openLandModal() {
    document.getElementById('landModal').style.display = 'block';
    document.getElementById('landForm').reset();
    document.getElementById('landAlert').innerHTML = '';
    setupAddressUI('land');
}

// Declare land (TTNB)
async function submitLand(event) {
    event.preventDefault();
    const form = event.target;
    const alertBox = document.getElementById('landAlert');
    alertBox.innerHTML = '';

    let communeId = document.getElementById('land_commune').value;
    const communeOther = document.getElementById('land_commune_other').value.trim();
    let locality = document.getElementById('land_locality').value || '';
    const localityOther = document.getElementById('land_locality_other').value.trim();
    const mode = document.getElementById('land_address_mode').value;
    const street = document.getElementById('land_street_name').value.trim();
    const villa = document.getElementById('land_villa_number').value.trim();
    const res = document.getElementById('land_residence_name').value.trim();
    const apt = document.getElementById('land_apartment_number').value.trim();
    const lat = document.getElementById('land_lat').value;
    const lng = document.getElementById('land_lng').value;
    const surface = form.querySelector('[name="surface"]').value;
    const landType = form.querySelector('[name="land_type"]').value;
    const urbanZone = form.querySelector('[name="urban_zone"]').value;
    const nature = form.querySelector('[name="nature"]').value;

    if (communeId === OTHER_VALUE) {
        communeId = await resolveOtherCommune(communeOther, 'landAlert');
        if (!communeId) return;
    }
    if (!communeId) {
        alertBox.innerHTML = '<div class="alert alert-error">Please choose a municipality.</div>';
        return;
    }
    if (!street) {
        alertBox.innerHTML = '<div class="alert alert-error">Street name is required.</div>';
        return;
    }
    if (locality === OTHER_VALUE) locality = localityOther;

    const payload = {
        commune_id: Number(communeId),
        address_mode: mode,
        street_name: street,
        locality,
        surface: Number(surface),
        land_type: landType,
        urban_zone: urbanZone,
        nature
    };
    if (mode === 'villa') payload.villa_number = villa;
    else {
        payload.residence_name = res;
        payload.apartment_number = apt;
    }
    if (lat && lng) {
        payload.latitude = Number(lat);
        payload.longitude = Number(lng);
    }

    try {
        const response = await fetch(`${API_BASE}/ttnb/lands`, {
            method: 'POST',
            headers: getAuthHeader(),
            body: JSON.stringify(payload)
        });
        const result = await response.json();
        if (response.ok) {
            alertBox.innerHTML = '<div class="alert alert-success">Land declared successfully. You can upload documents now.</div>';
            document.getElementById('land_declaration_id').value = result.land?.id || result.id;
            document.getElementById('landForm').style.display = 'none';
            document.getElementById('landDocUpload').style.display = 'block';
            document.getElementById('landSubmitBtn').disabled = true;
            loadOverview();
        } else {
            alertBox.innerHTML = '<div class="alert alert-error">' + (result.error || 'Failed to declare land') + '</div>';
        }
    } catch (error) {
        alertBox.innerHTML = '<div class="alert alert-error">Network error. Please try again.</div>';
    }
}
// Reverse geocode: look up address by lat/lon
async function runReverseGeocode() {
    const lat = parseFloat(document.getElementById('geo_lat')?.value || '');
    const lon = parseFloat(document.getElementById('geo_lng')?.value || '');
    if (Number.isNaN(lat) || Number.isNaN(lon)) {
        document.getElementById('geocode-results').innerHTML = '<div class="alert alert-error">Enter latitude and longitude first.</div>';
        return;
    }
    const { res, error } = await fetchExternalAPI(`${EXTERNAL_BASE}/reverse-geocode?lat=${encodeURIComponent(lat)}&lon=${encodeURIComponent(lon)}`);
    if (error) {
        const msg = getExternalAPIErrorMessage(res, error, 'Reverse geocoding failed. Check your connection.');
        document.getElementById('geocode-results').innerHTML = `<div class="alert alert-error">${msg}</div>`;
        return;
    }
    const data = await res.json();
    if (!res.ok) {
        const msg = getExternalAPIErrorMessage(res, null, data.error || 'Reverse geocoding failed');
        document.getElementById('geocode-results').innerHTML = `<div class="alert alert-error">${msg}</div>`;
        return;
    }
    const address = data.address || {};
    document.getElementById('geocode-results').innerHTML = `
        <div class="alert alert-success">Reverse geocode success.</div>
        <div style="margin-top:10px;">
            <div><strong>${data.display_name || 'Unnamed location'}</strong></div>
            <div>Type: ${data.type || 'n/a'} (${data.category || 'n/a'})</div>
            <div style="font-size:13px; color:#555;">${Object.entries(address).slice(0,5).map(([k,v]) => `${k}: ${v}`).join(', ')}</div>
        </div>
    `;
}

// NASA imagery search by query string
async function searchNasaImagery() {
    const query = (document.getElementById('nasa_query')?.value || '').trim();
    if (!query) {
        document.getElementById('nasa-imagery-results').innerHTML = '<div class="alert alert-error">Enter a search query first.</div>';
        return;
    }
    const { res, error } = await fetchExternalAPI(`${EXTERNAL_BASE}/nasa/imagery?q=${encodeURIComponent(query)}&page_size=5`);
    if (error) {
        const msg = getExternalAPIErrorMessage(res, error, 'NASA search failed. Check your connection.');
        document.getElementById('nasa-imagery-results').innerHTML = `<div class="alert alert-error">${msg}</div>`;
        return;
    }
    const data = await res.json();
    if (!res.ok) {
        const msg = getExternalAPIErrorMessage(res, null, data.error || 'NASA imagery search failed');
        document.getElementById('nasa-imagery-results').innerHTML = `<div class="alert alert-error">${msg}</div>`;
        return;
    }
    const items = data.items || [];
    if (!items.length) {
        document.getElementById('nasa-imagery-results').innerHTML = '<div class="alert alert-warning">No imagery available for this location or timeframe. Try a broader search.</div>';
        return;
    }
    document.getElementById('nasa-imagery-results').innerHTML = items.map(item => `
        <div style="padding:12px; border:1px solid #e5e7eb; border-radius:6px; margin-bottom:10px; background:#f9fafb;">
            <div style="font-weight:600;">${item.title || 'Untitled'}</div>
            <div style="font-size:13px; color:#555;">${item.description ? item.description.substring(0,140) + '…' : 'No description'}</div>
            ${item.href ? `<div style=\"margin-top:6px;\"><a href=\"${item.href}\" target=\"_blank\" class=\"button\" style=\"padding:6px 10px; font-size:12px;\">Open Image</a></div>` : ''}
        </div>
    `).join('');
}

// Document upload functions for land
async function uploadLandDocument() {
    const declarationId = document.getElementById('land_declaration_id').value;
    const docType = document.getElementById('land_doc_type').value;
    const fileInput = document.getElementById('land_doc_file');
    const statusDiv = document.getElementById('land_doc_status');
    
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
        const response = await fetch(`${API_BASE}/documents/declarations/${declarationId}/documents`, {
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
            loadLandDocuments(declarationId);
        } else {
            statusDiv.innerHTML = '<div class="alert alert-error">' + (result.error || 'Upload failed') + '</div>';
        }
    } catch (error) {
        statusDiv.innerHTML = '<div class="alert alert-error">Network error. Please try again.</div>';
    }
}

async function loadLandDocuments(declarationId) {
    try {
        const response = await fetch(`${API_BASE}/documents/declarations/${declarationId}/documents`, {
            headers: getAuthHeader()
        });
        const result = await response.json();
        
        const listDiv = document.getElementById('land_doc_list');
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

function skipLandDocuments() {
    closeModal('landModal');
    loadLands();
    // Reset form for next use
    document.getElementById('landForm').style.display = 'block';
    document.getElementById('landDocUpload').style.display = 'none';
    document.getElementById('landForm').reset();
    document.getElementById('landSubmitBtn').disabled = false;
}

// Taxes
async function loadTaxes() {
    try {
        const response = await fetch(`${API_BASE}/tib/my-taxes`, { headers: getAuthHeader() });
        const data = await response.json();
        const tbody = document.getElementById('taxes-body');
        tbody.innerHTML = '';

        if (!data.taxes || data.taxes.length === 0) {
            tbody.innerHTML = '<tr><td colspan="6">No taxes found</td></tr>';
            return;
        }

        data.taxes.forEach(tax => {
            const row = tbody.insertRow();
            const statusClass = tax.status === 'paid' ? 'status-paid' : 'status-pending';
            const actionCell = (tax.status === 'paid')
                ? 'Paid'
                : (tax.is_payable
                    ? '<button class="button" onclick="openPaymentModal(' + tax.id + ', ' + tax.total_amount + ')">Pay Now</button>'
                    : 'Payable from ' + (tax.payable_from || '—'));
            row.innerHTML = `
                <td>TIB</td>
                <td>${tax.tax_year}</td>
                <td>${tax.property_id ? 'Property #' + tax.property_id : 'N/A'}</td>
                <td>${tax.total_amount.toFixed(2)} TND</td>
                <td><span class="status-badge ${statusClass}">${tax.status}</span></td>
                <td>${actionCell}</td>
            `;
        });
    } catch (error) {
        console.error('Error loading taxes:', error);
        document.getElementById('taxes-body').innerHTML = '<tr><td colspan="6">Error loading taxes</td></tr>';
    }
}

function openPaymentModal(taxId, amount) {
    document.getElementById('paymentModal').style.display = 'block';
    document.getElementById('payment_tax_id').value = taxId;
    document.getElementById('payment_amount').value = amount;
    document.getElementById('paymentAlert').innerHTML = '';
}

async function submitPayment(event) {
    event.preventDefault();
    const formData = new FormData(event.target);
    const data = Object.fromEntries(formData.entries());

    try {
        const response = await fetch(`${API_BASE}/payments/pay`, {
            method: 'POST',
            headers: getAuthHeader(),
            body: JSON.stringify(data)
        });

        const result = await response.json();
        
        if (response.ok) {
            document.getElementById('paymentAlert').innerHTML = 
                '<div class="alert alert-success">Payment processed successfully! Receipt: ' + result.receipt_number + '</div>';
            setTimeout(() => {
                closeModal('paymentModal');
                loadTaxes();
                loadPayments();
                loadOverview();
            }, 2000);
        } else {
            document.getElementById('paymentAlert').innerHTML = 
                '<div class="alert alert-error">' + (result.error || 'Payment failed') + '</div>';
        }
    } catch (error) {
        document.getElementById('paymentAlert').innerHTML = 
            '<div class="alert alert-error">Network error. Please try again.</div>';
    }
}

// Payments
async function loadPayments() {
    try {
        const response = await fetch(`${API_BASE}/payments/my-payments`, { headers: getAuthHeader() });
        const tbody = document.getElementById('payments-body');
        tbody.innerHTML = '';

        if (!response.ok) {
            tbody.innerHTML = '<tr><td colspan="5">Payments endpoint unavailable</td></tr>';
            return;
        }

        const data = await response.json();
        const list = data.payments || data || [];

        if (list.length === 0) {
            tbody.innerHTML = '<tr><td colspan="5">No payment history</td></tr>';
            return;
        }

        list.forEach(payment => {
            const row = tbody.insertRow();
            const date = payment.payment_date ? new Date(payment.payment_date).toLocaleDateString() : '-';
            row.innerHTML = `
                <td>${date}</td>
                <td>${Number(payment.amount || payment.total_amount || 0).toFixed(2)} TND</td>
                <td>${payment.receipt_number || 'N/A'}</td>
                <td><span class="status-badge status-paid">${payment.status || 'paid'}</span></td>
            `;
        });
    } catch (error) {
        console.error('Error loading payments:', error);
        document.getElementById('payments-body').innerHTML = '<tr><td colspan="5">Error loading payments</td></tr>';
    }
}

// Disputes
async function loadDisputes() {
    try {
        const response = await fetch(`${API_BASE}/disputes/`, { headers: getAuthHeader() });
        const tbody = document.getElementById('disputes-body');
        tbody.innerHTML = '';

        if (!response.ok) {
            tbody.innerHTML = '<tr><td colspan="4">Disputes endpoint unavailable</td></tr>';
            return;
        }

        const data = await response.json();
        const list = data.disputes || data || [];

        if (list.length === 0) {
            tbody.innerHTML = '<tr><td colspan="4">No disputes submitted</td></tr>';
            return;
        }

        list.forEach(dispute => {
            const row = tbody.insertRow();
            const date = (dispute.submission_date || dispute.submitted_at) ? new Date(dispute.submission_date || dispute.submitted_at).toLocaleDateString() : '-';
            const type = dispute.dispute_type?.value || dispute.dispute_type || '-';
            const status = dispute.status?.value || dispute.status || 'submitted';
            row.innerHTML = `
                <td>${dispute.subject || '-'}</td>
                <td>${type}</td>
                <td><span class="status-badge status-${String(status).toLowerCase()}">${status}</span></td>
                <td>${date}</td>
            `;
        });
    } catch (error) {
        console.error('Error loading disputes:', error);
        document.getElementById('disputes-body').innerHTML = '<tr><td colspan="4">Error loading disputes</td></tr>';
    }
}

function openDisputeModal() {
    document.getElementById('disputeModal').style.display = 'block';
    document.getElementById('disputeForm').reset();
    document.getElementById('disputeAlert').innerHTML = '';
}

async function submitDispute(event) {
    event.preventDefault();
    const formData = new FormData(event.target);
    const data = Object.fromEntries(formData.entries());

    try {
        const response = await fetch(`${API_BASE}/disputes/`, {
            method: 'POST',
            headers: getAuthHeader(),
            body: JSON.stringify(data)
        });

        const result = await response.json();
        
        if (response.ok) {
            document.getElementById('disputeAlert').innerHTML = 
                '<div class="alert alert-success">Dispute submitted successfully!</div>';
            setTimeout(() => {
                closeModal('disputeModal');
                loadDisputes();
            }, 1500);
        } else {
            document.getElementById('disputeAlert').innerHTML = 
                '<div class="alert alert-error">' + (result.error || 'Failed to submit dispute') + '</div>';
        }
    } catch (error) {
        document.getElementById('disputeAlert').innerHTML = 
            '<div class="alert alert-error">Network error. Please try again.</div>';
    }
}

// Permits
async function loadPermits() {
    try {
        const response = await fetch(`${API_BASE}/permits/my-requests`, { headers: getAuthHeader() });
        const tbody = document.getElementById('permits-body');
        tbody.innerHTML = '';

        if (!response.ok) {
            tbody.innerHTML = '<tr><td colspan="5">Permits endpoint unavailable</td></tr>';
            return;
        }

        const data = await response.json();
        const list = data.permits || data || [];

        if (list.length === 0) {
            tbody.innerHTML = '<tr><td colspan="5">No permit requests</td></tr>';
            return;
        }

        list.forEach(permit => {
            const row = tbody.insertRow();
            const date = permit.request_date ? new Date(permit.request_date).toLocaleDateString() : '-';
            const status = permit.status?.value || permit.status || 'submitted';
            const statusClass = String(status).toLowerCase() === 'approved' ? 'status-approved' : 
                               String(status).toLowerCase() === 'rejected' ? 'status-rejected' : 'status-pending';
            row.innerHTML = `
                <td>${permit.permit_type || '-'}</td>
                <td><span class="status-badge ${statusClass}">${status}</span></td>
                <td>${date}</td>
                <td>${permit.decision_date ? new Date(permit.decision_date).toLocaleDateString() : '-'}</td>
            `;
        });

    } catch (error) {
        console.error('Error loading permits:', error);
        document.getElementById('permits-body').innerHTML = '<tr><td colspan="4">Error loading permits</td></tr>';
    }
}

// Reclamations (Service Complaints)
async function loadReclamations() {
    try {
        const response = await fetch(`${API_BASE}/reclamations/my-reclamations`, { headers: getAuthHeader() });
        const tbody = document.getElementById('reclamations-body');
        tbody.innerHTML = '';

        if (!response.ok) {
            tbody.innerHTML = '<tr><td colspan="4">Complaints endpoint unavailable</td></tr>';
            return;
        }

        const data = await response.json();
        const list = data.reclamations || data || [];

        if (list.length === 0) {
            tbody.innerHTML = '<tr><td colspan="4">No complaints submitted</td></tr>';
            return;
        }

        list.forEach(r => {
            const row = tbody.insertRow();
            const status = r.status?.value || r.status || 'submitted';
            const date = r.created_at ? new Date(r.created_at).toLocaleDateString() : '-';
            row.innerHTML = `
                <td>${r.type || r.reclamation_type || '-'}</td>
                <td>${r.street_address ? r.street_address + ', ' + (r.city || '') : '-'}</td>
                <td><span class="status-badge status-${String(status).toLowerCase()}">${status}</span></td>
                <td>${r.priority || '-'}</td>
            `;
        });
    } catch (error) {
        console.error('Error loading complaints:', error);
        document.getElementById('reclamations-body').innerHTML = '<tr><td colspan="4">Error loading complaints</td></tr>';
    }
}

async function submitReclamation(event) {
    event.preventDefault();
    const type = document.getElementById('reclamation_type').value;
    const street = document.getElementById('reclamation_street').value.trim();
    const city = document.getElementById('reclamation_city').value;
    const priority = document.getElementById('reclamation_priority').value || null;
    const description = document.getElementById('reclamation_description').value.trim();
    const statusEl = document.getElementById('reclamation_status');
    statusEl.textContent = '';

    if (!type || !street || !city || !description) {
        statusEl.textContent = 'Please fill all required fields.';
        return;
    }

    try {
        const response = await fetch(`${API_BASE}/reclamations/`, {
            method: 'POST',
            headers: getAuthHeader(),
            body: JSON.stringify({
                reclamation_type: type,
                street_address: street,
                city,
                description,
                priority: priority || null
            })
        });
        const data = await response.json();
        if (!response.ok) {
            statusEl.textContent = data.error || 'Failed to submit complaint';
            return;
        }
        statusEl.textContent = 'Complaint submitted';
        document.getElementById('reclamation-form').reset();
        loadReclamations();
    } catch (error) {
        statusEl.textContent = 'Network error while submitting complaint';
    }
}

function openPermitModal() {
    document.getElementById('permitModal').style.display = 'block';
    document.getElementById('permitForm').reset();
    document.getElementById('permitAlert').innerHTML = '';
}

async function submitPermit(event) {
    event.preventDefault();
    const formData = new FormData(event.target);
    const data = Object.fromEntries(formData.entries());

    try {
        const response = await fetch(`${API_BASE}/permits/request`, {
            method: 'POST',
            headers: getAuthHeader(),
            body: JSON.stringify(data)
        });

        const result = await response.json();
        
        if (response.ok) {
            document.getElementById('permitAlert').innerHTML = 
                '<div class="alert alert-success">Permit request submitted successfully!</div>';
            setTimeout(() => {
                closeModal('permitModal');
                loadPermits();
            }, 1500);
        } else {
            document.getElementById('permitAlert').innerHTML = 
                '<div class="alert alert-error">' + (result.error || 'Failed to submit permit request') + '</div>';
        }
    } catch (error) {
        document.getElementById('permitAlert').innerHTML = 
            '<div class="alert alert-error">Network error. Please try again.</div>';
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
function viewPropertyDetail(id) {
    alert('Property detail view for ID ' + id + ' - Full view would open here');
}

function viewLandDetail(id) {
    alert('Land detail view for ID ' + id + ' - Full view would open here');
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
    populateReclamationCities();
    loadOverview();
});

// External integrations
let nasaEventsLoaded = false;

function loadLocationTools() {
    if (!nasaEventsLoaded) loadNasaEvents();
}

async function runGeocodeLookup() {
    const address = (document.getElementById('geo_address')?.value || '').trim();
    if (!address) {
        document.getElementById('geocode-results').innerHTML = '<div class="alert alert-error">Enter an address first.</div>';
        return;
    }
    document.getElementById('geocode-results').innerHTML = '<div class="alert alert-info">Looking up address…</div>';
    
    const { res, error } = await fetchExternalAPI(`${EXTERNAL_BASE}/geocode?q=${encodeURIComponent(address)}`);
    
    if (error) {
        const msg = getExternalAPIErrorMessage(res, error, 'Geocoding failed. Check your connection.');
        document.getElementById('geocode-results').innerHTML = `<div class="alert alert-error">${msg}</div>`;
        return;
    }
    
    const data = await res.json();
    if (!res.ok) {
        const msg = getExternalAPIErrorMessage(res, null, data.error || 'Geocoding failed');
        document.getElementById('geocode-results').innerHTML = `<div class="alert alert-error">${msg}</div>`;
        return;
    }
    
    const items = data.results || [];
    if (!items.length) {
        document.getElementById('geocode-results').innerHTML = '<div class="alert alert-warning">No address matches found. Try a different query.</div>';
        return;
    }
    
    const first = items[0];
    document.getElementById('geocode-results').innerHTML = `
        <div class="alert alert-success">Found ${items.length} result(s).</div>
        <div style="margin-top:10px;">
            <div><strong>${first.display_name || 'Unnamed location'}</strong></div>
            <div>Lat: ${first.lat.toFixed(6)}, Lon: ${first.lon.toFixed(6)}</div>
            <div>Type: ${first.type || 'n/a'} (${first.category || 'n/a'})</div>
        </div>
    `;
    document.getElementById('geo_lat').value = first.lat;
    document.getElementById('geo_lng').value = first.lon;
}

async function loadNasaEvents() {
    document.getElementById('nasa-events').innerHTML = '<div class="alert alert-info">Loading recent Earth events…</div>';
    try {
        const res = await fetch(`${EXTERNAL_BASE}/nasa/events?limit=6`);
        const data = await res.json();
        if (!res.ok) throw new Error(data.error || 'Events unavailable');
        const events = data.events || [];
        if (!events.length) {
            document.getElementById('nasa-events').innerHTML = '<div class="alert alert-error">No events found.</div>';
            return;
        }
        nasaEventsLoaded = true;
        document.getElementById('nasa-events').innerHTML = events.map(ev => `
            <div style="padding:12px; border:1px solid #e5e7eb; border-radius:6px; margin-bottom:8px; background:#f9fafb;">
                <div style="font-weight:600;">${ev.title || 'Event'}</div>
                <div style="font-size:13px; color:#555;">Updated: ${ev.updated || 'n/a'}</div>
                ${ev.categories && ev.categories.length ? `<div style="font-size:12px; color:#444;">Categories: ${ev.categories.join(', ')}</div>` : ''}
                ${ev.geometry ? `<div style="font-size:12px; color:#444;">Location: ${ev.geometry.coordinates || ev.geometry}</div>` : ''}
            </div>
        `).join('');
    } catch (error) {
        document.getElementById('nasa-events').innerHTML = `<div class="alert alert-error">${error.message}</div>`;
    }
}

// Address UI helpers
async function setupAddressUI(prefix) {
    if (!communesCache.length) {
        try {
            const res = await fetch(`${API_BASE}/public/communes`);
            const data = await res.json();
            communesCache = data.communes || [];
        } catch (e) {
            console.error('Failed to load communes', e);
        }
    }

    const communeSelect = document.getElementById(`${prefix}_commune`);
    communeSelect.innerHTML = '<option value="">Select…</option>' + communesCache.map(c => `<option value="${c.id}">${c.name}</option>`).join('') + `<option value="${OTHER_VALUE}">Other…</option>`;

    const delegationSelect = document.getElementById(`${prefix}_delegation`);
    const localitySelect = document.getElementById(`${prefix}_locality`);
    delegationSelect.innerHTML = '<option value="">Select delegation…</option>';
    localitySelect.innerHTML = '';
    const communeOther = document.getElementById(`${prefix}_commune_other`);
    const localityOther = document.getElementById(`${prefix}_locality_other`);

    communeSelect.onchange = async () => {
        const val = communeSelect.value;
        communeOther.style.display = val === OTHER_VALUE ? '' : 'none';

        delegationSelect.innerHTML = '<option value="">Select delegation…</option>';
        localitySelect.innerHTML = '';

        if (!val || val === OTHER_VALUE) {
            localityOther.style.display = val === OTHER_VALUE ? '' : 'none';
            if (prefix === 'property') fetchRequiredDocuments('property', null, 'property_required_docs');
            if (prefix === 'land') fetchRequiredDocuments('land', null, 'land_required_docs');
            return;
        }

        try {
            const res = await fetch(`${API_BASE}/public/delegations?commune_id=${val}`);
            const data = await res.json();
            const list = data.delegations || [];
            if (list.length) {
                delegationSelect.innerHTML = '<option value="">Select delegation…</option>' + list.map(d => `<option value="${d.name}">${d.name}</option>`).join('');
            } else {
                delegationSelect.innerHTML = '<option value="">No delegations found</option>';
            }
        } catch (e) {
            delegationSelect.innerHTML = '<option value="">Delegations unavailable</option>';
        }
        localityOther.style.display = 'none';
        localitySelect.innerHTML = '';

        if (prefix === 'property') fetchRequiredDocuments('property', val, 'property_required_docs');
        if (prefix === 'land') fetchRequiredDocuments('land', val, 'land_required_docs');
    };

    delegationSelect.onchange = async () => {
        const communeId = communeSelect.value;
        const delegation = delegationSelect.value;
        localitySelect.innerHTML = '';
        if (!communeId || !delegation) {
            localityOther.style.display = 'none';
            return;
        }
        try {
            const res = await fetch(`${API_BASE}/public/localities?commune_id=${communeId}&delegation=${encodeURIComponent(delegation)}`);
            const data = await res.json();
            const list = (data.localities || []).map(x => x.name || x);
            if (list.length) {
                localitySelect.innerHTML = '<option value="">(optional)</option>' + list.map(l => `<option>${l}</option>`).join('') + `<option value="${OTHER_VALUE}">Other…</option>`;
            } else {
                localitySelect.innerHTML = `<option value="${OTHER_VALUE}">Other…</option>`;
            }
        } catch (e) {
            localitySelect.innerHTML = `<option value="${OTHER_VALUE}">Other…</option>`;
        }
        localityOther.style.display = 'none';
    };

    localitySelect.onchange = () => {
        localityOther.style.display = localitySelect.value === OTHER_VALUE ? '' : 'none';
    };

    const modeSelect = document.getElementById(`${prefix}_address_mode`);
    const villaGroup = document.getElementById(`${prefix}_villa_group`);
    const resGroup = document.getElementById(`${prefix}_residence_group`);
    modeSelect.onchange = () => {
        if (modeSelect.value === 'villa') {
            villaGroup.style.display = '';
            resGroup.style.display = 'none';
        } else {
            villaGroup.style.display = 'none';
            resGroup.style.display = '';
        }
    };

    const mapId = `${prefix}Map`;
    const latInput = document.getElementById(`${prefix}_lat`);
    const lngInput = document.getElementById(`${prefix}_lng`);
    const defaultCenter = [36.8065, 10.1815];
    if (prefix === 'property') {
        propertyMap?.remove();
        propertyMap = L.map(mapId).setView(defaultCenter, 12);
        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', { attribution: '&copy; OpenStreetMap' }).addTo(propertyMap);
        propertyMarker = null;
        propertyMap.on('click', (e) => {
            const { lat, lng } = e.latlng;
            if (propertyMarker) propertyMap.removeLayer(propertyMarker);
            propertyMarker = L.marker([lat, lng], { draggable: true }).addTo(propertyMap);
            latInput.value = lat.toFixed(6);
            lngInput.value = lng.toFixed(6);
            propertyMarker.on('dragend', () => {
                const p = propertyMarker.getLatLng();
                latInput.value = p.lat.toFixed(6);
                lngInput.value = p.lng.toFixed(6);
            });
        });
    } else {
        landMap?.remove();
        landMap = L.map(mapId).setView(defaultCenter, 12);
        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', { attribution: '&copy; OpenStreetMap' }).addTo(landMap);
        landMarker = null;
        landMap.on('click', (e) => {
            const { lat, lng } = e.latlng;
            if (landMarker) landMap.removeLayer(landMarker);
            landMarker = L.marker([lat, lng], { draggable: true }).addTo(landMap);
            latInput.value = lat.toFixed(6);
            lngInput.value = lng.toFixed(6);
            landMarker.on('dragend', () => {
                const p = landMarker.getLatLng();
                latInput.value = p.lat.toFixed(6);
                lngInput.value = p.lng.toFixed(6);
            });
        });
    }
}

async function resolveOtherCommune(name, alertContainerId) {
    const alertBox = document.getElementById(alertContainerId);
    if (!name) {
        alertBox.innerHTML = '<div class="alert alert-error">Type the municipality name.</div>';
        return null;
    }
    try {
        const res = await fetch(`${API_BASE}/public/communes?search=${encodeURIComponent(name)}`);
        const data = await res.json();
        const matches = data.communes || [];
        if (matches.length === 1) return matches[0].id;
        if (matches.length === 0) {
            alertBox.innerHTML = '<div class="alert alert-error">No municipality found. Refine your input.</div>';
        } else {
            alertBox.innerHTML = '<div class="alert alert-error">Multiple matches found. Please refine.</div>';
        }
    } catch (e) {
        alertBox.innerHTML = '<div class="alert alert-error">Unable to search municipalities.</div>';
    }
    return null;
}
window.logout = logout;
window.showSection = showSection;
// Fallback: bind inline handlers explicitly
window.addEventListener('DOMContentLoaded', () => {
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
});
