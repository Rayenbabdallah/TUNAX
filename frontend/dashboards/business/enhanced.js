/**
 * Business (TTNB) dashboard wiring.
 * Matches the HTML forms to the backend routes that actually exist.
 */
const API_BASE = '/api/v1';  // Use relative URL so frontend works behind proxy
const OTHER_VALUE = '__other__';

function getToken() {
    return localStorage.getItem('access_token');
}
// Fallback: bind inline handlers explicitly
window.addEventListener('DOMContentLoaded', () => {
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

if (!getToken()) {
    window.location.href = '/common_login/index.html';
}

function getAuthHeader() {
    return {
        'Authorization': `Bearer ${getToken()}`,
        'Content-Type': 'application/json'
    };
}

const state = {
    selectedTaxId: null,
    selectedTaxAmount: 0,
    pendingTaxes: [],
    currentUserId: null,
    communes: [],
    userCities: [],
    maps: {
        land: null,
        landMarker: null,
        tib: null,
        tibMarker: null
    }
};

function getAuthHeader() {
    return {
        'Authorization': `Bearer ${getToken()}`,
        'Content-Type': 'application/json'
    };
}

async function fetchJSON(path, options = {}) {
    const response = await fetch(`${API_BASE}${path}`, {
        ...options,
        headers: {
            ...getAuthHeader(),
            ...(options.headers || {})
        }
    });
    const data = await response.json().catch(() => ({}));
    return { response, data };
}

function showSection(sectionId, el) {
    document.querySelectorAll('.section').forEach(sec => sec.style.display = 'none');
    document.querySelectorAll('.nav-link').forEach(link => link.classList.remove('active'));
    document.getElementById(sectionId).style.display = 'block';
    if (el) el.classList.add('active');

    if (sectionId === 'properties') loadProperties();
    else if (sectionId === 'tib') loadTibProperties();
    else if (sectionId === 'taxes') loadTaxes();
    else if (sectionId === 'payments') loadPayments();
    else if (sectionId === 'permits') loadPermits();
    else if (sectionId === 'disputes') loadDisputes();
    else if (sectionId === 'budget') loadBudgetProjects();
    else if (sectionId === 'reclamations') { populateReclamationCities(); loadReclamations(); }

    if (sectionId === 'properties' || sectionId === 'tib') {
        refreshLeafletMaps();
    }
}

async function fetchRequiredDocuments(declarationType, communeId, targetElementId) {
    const target = document.getElementById(targetElementId);
    if (!target) return;
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

async function loadOverview() {
    try {
        const [landsRes, taxesRes, permitsRes] = await Promise.all([
            fetchJSON('/ttnb/lands'),
            fetchJSON('/ttnb/my-taxes'),
            fetchJSON('/permits/my-requests')
        ]);

        const lands = landsRes.data.lands || [];
        const taxes = taxesRes.data.taxes || [];
        const permits = permitsRes.data.permits || [];

        document.getElementById('prop-count').textContent = lands.length;

        const totalDue = taxes
            .filter(t => t.status !== 'paid')
            .reduce((sum, t) => sum + t.total_amount, 0);
        const totalPaid = taxes
            .filter(t => t.status === 'paid')
            .reduce((sum, t) => sum + t.total_amount, 0);

        document.getElementById('total-due').textContent = `${totalDue.toFixed(2)} TND`;
        document.getElementById('total-paid').textContent = `${totalPaid.toFixed(2)} TND`;
        document.getElementById('permits-count').textContent = permits.filter(p => p.status === 'pending').length;
    } catch (error) {
        console.error('Error loading overview', error);
    }
}

// Common address UI helpers for Business dashboard
async function ensureCommunes() {
    if (state.communes.length) return state.communes;
    try {
        const res = await fetch(`${API_BASE}/public/communes`);
        const data = await res.json();
        state.communes = data.communes || [];
    } catch {}
    return state.communes;
}

async function fetchDelegations(communeId) {
    if (!communeId) return [];
    try {
        const res = await fetch(`${API_BASE}/public/delegations?commune_id=${communeId}`);
        const data = await res.json();
        return data.delegations || [];
    } catch {
        return [];
    }
}

function populateCommuneSelect(selectEl) {
    const base = '<option value="">Select…</option>' + state.communes.map(c => `<option value="${c.id}">${c.name}</option>`).join('');
    selectEl.innerHTML = base + `<option value="${OTHER_VALUE}">Other…</option>`;
}

async function refreshDelegations(communeId, selectEl) {
    if (!communeId) { selectEl.innerHTML = '<option value="">Select delegation…</option>'; return; }
    const list = await fetchDelegations(communeId);
    if (list.length) {
        selectEl.innerHTML = '<option value="">Select delegation…</option>' + list.map(d => `<option value="${d.name}">${d.name}</option>`).join('');
    } else {
        selectEl.innerHTML = '<option value="">No delegations found</option>';
    }
}

async function refreshLocalities(communeId, delegation, selectEl) {
    if (!communeId || !delegation) { selectEl.innerHTML = ''; return; }
    try {
        const res = await fetch(`${API_BASE}/public/localities?commune_id=${communeId}&delegation=${encodeURIComponent(delegation)}`);
        const data = await res.json();
        const list = (data.localities || []).map(x => x.name || x);
        if (list.length) {
            selectEl.innerHTML = '<option value="">(optional)</option>' + list.map(l => `<option>${l}</option>`).join('') + `<option value="${OTHER_VALUE}">Other…</option>`;
        } else {
            selectEl.innerHTML = `<option value="${OTHER_VALUE}">Other…</option>`;
        }
    } catch {
        selectEl.innerHTML = `<option value="${OTHER_VALUE}">Other…</option>`;
    }
}

async function ensureUserCities() {
    if (state.userCities.length) return state.userCities;
    const cities = new Set();
    try {
        const { response, data } = await fetchJSON('/tib/properties');
        if (response.ok) (data.properties || []).forEach(p => p.city && cities.add(p.city));
    } catch {}
    try {
        const { response, data } = await fetchJSON('/ttnb/lands');
        if (response.ok) (data.lands || []).forEach(l => l.city && cities.add(l.city));
    } catch {}
    state.userCities = Array.from(cities);
    return state.userCities;
}

async function populateReclamationCities() {
    const select = document.getElementById('biz_reclamation_city');
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

function setupBizAddressUI() {
    // TTNB (land)
    ensureCommunes().then(() => {
        const cSel = document.getElementById('biz_land_commune');
        const cOther = document.getElementById('biz_land_commune_other');
        const dSel = document.getElementById('biz_land_delegation');
        const lSel = document.getElementById('biz_land_locality');
        const lOther = document.getElementById('biz_land_locality_other');
        populateCommuneSelect(cSel);
        cSel.onchange = () => {
            cOther.style.display = cSel.value === OTHER_VALUE ? '' : 'none';
            dSel.innerHTML = '<option value="">Select delegation…</option>';
            lSel.innerHTML = '';
            if (cSel.value && cSel.value !== OTHER_VALUE) {
                refreshDelegations(cSel.value, dSel);
                lOther.style.display = 'none';
                fetchRequiredDocuments('land', cSel.value, 'biz_land_required_docs');
            } else {
                lSel.innerHTML = `<option value="${OTHER_VALUE}">Other…</option>`;
                lOther.style.display = '';
                fetchRequiredDocuments('land', null, 'biz_land_required_docs');
            }
        };
        dSel.onchange = () => {
            const delegation = dSel.value;
            if (!cSel.value || cSel.value === OTHER_VALUE || !delegation) {
                lSel.innerHTML = '';
                lOther.style.display = 'none';
                return;
            }
            refreshLocalities(cSel.value, delegation, lSel).then(() => {
                lOther.style.display = 'none';
            });
        };
        lSel.onchange = () => lOther.style.display = lSel.value === OTHER_VALUE ? '' : 'none';
    });

    // TIB (property)
    ensureCommunes().then(() => {
        const cSel = document.getElementById('biz_tib_commune');
        const cOther = document.getElementById('biz_tib_commune_other');
        const dSel = document.getElementById('biz_tib_delegation');
        const lSel = document.getElementById('biz_tib_locality');
        const lOther = document.getElementById('biz_tib_locality_other');
        populateCommuneSelect(cSel);
        cSel.onchange = () => {
            cOther.style.display = cSel.value === OTHER_VALUE ? '' : 'none';
            dSel.innerHTML = '<option value="">Select delegation…</option>';
            lSel.innerHTML = '';
            if (cSel.value && cSel.value !== OTHER_VALUE) {
                refreshDelegations(cSel.value, dSel);
                lOther.style.display = 'none';
                fetchRequiredDocuments('property', cSel.value, 'biz_tib_required_docs');
            } else {
                lSel.innerHTML = `<option value="${OTHER_VALUE}">Other…</option>`;
                lOther.style.display = '';
                fetchRequiredDocuments('property', null, 'biz_tib_required_docs');
            }
        };
        dSel.onchange = () => {
            const delegation = dSel.value;
            if (!cSel.value || cSel.value === OTHER_VALUE || !delegation) {
                lSel.innerHTML = '';
                lOther.style.display = 'none';
                return;
            }
            refreshLocalities(cSel.value, delegation, lSel).then(() => {
                lOther.style.display = 'none';
            });
        };
        lSel.onchange = () => lOther.style.display = lSel.value === OTHER_VALUE ? '' : 'none';
    });

    // Address mode toggles
    const landMode = document.getElementById('biz_land_address_mode');
    const landVilla = document.getElementById('biz_land_villa_group');
    const landRes = document.getElementById('biz_land_residence_group');
    if (landMode) landMode.onchange = () => {
        if (landMode.value === 'villa') { landVilla.style.display = ''; landRes.style.display = 'none'; }
        else { landVilla.style.display = 'none'; landRes.style.display = ''; }
    };
    const tibMode = document.getElementById('biz_tib_address_mode');
    const tibVilla = document.getElementById('biz_tib_villa_group');
    const tibRes = document.getElementById('biz_tib_residence_group');
    if (tibMode) tibMode.onchange = () => {
        if (tibMode.value === 'villa') { tibVilla.style.display = ''; tibRes.style.display = 'none'; }
        else { tibVilla.style.display = 'none'; tibRes.style.display = ''; }
    };

    // Maps
    const defaultCenter = [36.8065, 10.1815];
    try {
        state.maps.land?.remove();
        state.maps.land = L.map('bizLandMap').setView(defaultCenter, 12);
        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', { attribution: '&copy; OpenStreetMap' }).addTo(state.maps.land);
        state.maps.land.on('click', (e) => {
            const { lat, lng } = e.latlng;
            if (state.maps.landMarker) state.maps.land.removeLayer(state.maps.landMarker);
            state.maps.landMarker = L.marker([lat, lng], { draggable: true }).addTo(state.maps.land);
            document.getElementById('biz_land_lat').value = lat.toFixed(6);
            document.getElementById('biz_land_lng').value = lng.toFixed(6);
            state.maps.landMarker.on('dragend', () => {
                const p = state.maps.landMarker.getLatLng();
                document.getElementById('biz_land_lat').value = p.lat.toFixed(6);
                document.getElementById('biz_land_lng').value = p.lng.toFixed(6);
            });
        });
    } catch {}
    try {
        state.maps.tib?.remove();
        state.maps.tib = L.map('bizTibMap').setView(defaultCenter, 12);
        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', { attribution: '&copy; OpenStreetMap' }).addTo(state.maps.tib);
        state.maps.tib.on('click', (e) => {
            const { lat, lng } = e.latlng;
            if (state.maps.tibMarker) state.maps.tib.removeLayer(state.maps.tibMarker);
            state.maps.tibMarker = L.marker([lat, lng], { draggable: true }).addTo(state.maps.tib);
            document.getElementById('biz_tib_lat').value = lat.toFixed(6);
            document.getElementById('biz_tib_lng').value = lng.toFixed(6);
            state.maps.tibMarker.on('dragend', () => {
                const p = state.maps.tibMarker.getLatLng();
                document.getElementById('biz_tib_lat').value = p.lat.toFixed(6);
                document.getElementById('biz_tib_lng').value = p.lng.toFixed(6);
            });
        });
    } catch {}

    refreshLeafletMaps();
}

function refreshLeafletMaps() {
    setTimeout(() => {
        if (state.maps.land) state.maps.land.invalidateSize();
        if (state.maps.tib) state.maps.tib.invalidateSize();
    }, 200);
}

async function resolveCommuneByName(name) {
    if (!name) return null;
    try {
        const res = await fetch(`${API_BASE}/public/communes?search=${encodeURIComponent(name)}`);
        const data = await res.json();
        const matches = data.communes || [];
        if (matches.length === 1) return matches[0].id;
        return null;
    } catch { return null; }
}

async function loadProperties() {
    const tbody = document.getElementById('properties-body');
    tbody.innerHTML = '<tr><td colspan="6">Loading...</td></tr>';

    try {
        const { response, data } = await fetchJSON('/ttnb/lands');
        if (!response.ok) {
            tbody.innerHTML = `<tr><td colspan="6">${data.error || 'Failed to load lands'}</td></tr>`;
            return;
        }

        const lands = data.lands || [];
        if (!lands.length) {
            tbody.innerHTML = '<tr><td colspan="6">No declared lands yet.</td></tr>';
            return;
        }

        tbody.innerHTML = '';
        lands.forEach(land => {
            const taxAmount = land.tax ? `${land.tax.total_amount.toFixed(2)} TND` : 'N/A';
            const row = tbody.insertRow();
            row.innerHTML = `
                <td>${land.street_address || 'N/A'}, ${land.city || ''}</td>
                <td>${land.surface || 0} m2</td>
                <td>${land.vAcnale_value ? `${land.vAcnale_value} TND` : '—'}</td>
                <td>${taxAmount}</td>
                <td><span class="status-badge status-${land.status}">${land.status}</span></td>
                <td>
                    ${land.tax && land.tax.status !== 'paid'
                        ? `<button class="button" onclick="selectTaxForPayment(${land.tax.id}, ${land.tax.total_amount})">Pay Tax</button>`
                        : 'Up to date'}
                </td>
            `;
        });
    } catch (error) {
        console.error('Error loading lands', error);
        tbody.innerHTML = '<tr><td colspan="6">Unable to load lands</td></tr>';
    }
}

async function handleDeclareProperty(event) {
    event.preventDefault();
    const area = parseFloat(document.getElementById('biz_area').value);
    const land_type = document.getElementById('biz_land_type').value;
    const urban_zone = document.getElementById('biz_urban_zone').value;
    const mode = document.getElementById('biz_land_address_mode').value;
    const street = document.getElementById('biz_land_street_name').value.trim();
    let communeId = document.getElementById('biz_land_commune').value;
    const communeOther = document.getElementById('biz_land_commune_other').value.trim();
    let locality = document.getElementById('biz_land_locality').value || '';
    const localityOther = document.getElementById('biz_land_locality_other').value.trim();
    const villa = document.getElementById('biz_land_villa_number').value.trim();
    const resName = document.getElementById('biz_land_residence_name').value.trim();
    const lot = document.getElementById('biz_land_apartment_number').value.trim();
    const lat = document.getElementById('biz_land_lat').value;
    const lng = document.getElementById('biz_land_lng').value;
    const messageEl = document.getElementById('declare-message');
    messageEl.textContent = '';

    if (communeId === OTHER_VALUE) {
        const resolved = await resolveCommuneByName(communeOther);
        if (!resolved) { messageEl.textContent = 'Municipality not found. Refine your input.'; return; }
        communeId = resolved;
    }
    if (locality === OTHER_VALUE) locality = localityOther;
    if (!street || !communeId || !urban_zone) { messageEl.textContent = 'Please fill required fields.'; return; }

    const payload = {
        commune_id: Number(communeId),
        address_mode: mode,
        street_name: street,
        locality,
        surface: area,
        land_type,
        urban_zone
    };
    if (mode === 'villa') payload.villa_number = villa; else { payload.residence_name = resName; payload.apartment_number = lot; }
    if (lat && lng) { payload.latitude = Number(lat); payload.longitude = Number(lng); }

    try {
        const { response, data } = await fetchJSON('/ttnb/lands', {
            method: 'POST',
            body: JSON.stringify(payload)
        });

        if (!response.ok) {
            messageEl.textContent = data.error || 'Failed to declare land.';
            return;
        }

        messageEl.textContent = 'Land declaration submitted successfully.';
        event.target.reset();
        loadProperties();
        loadTaxes();
        loadOverview();
    } catch (error) {
        messageEl.textContent = 'Network error while declaring land.';
    }
}

async function loadTibProperties() {
    const tbody = document.getElementById('tib-properties-body');
    if (!tbody) return;
    tbody.innerHTML = '<tr><td colspan="6">Loading...</td></tr>';

    try {
        const { response, data } = await fetchJSON('/tib/properties');
        if (!response.ok) {
            tbody.innerHTML = `<tr><td colspan="6">${data.error || 'Failed to load properties'}</td></tr>`;
            return;
        }

        const props = data.properties || [];
        if (!props.length) {
            tbody.innerHTML = '<tr><td colspan="6">No properties declared yet.</td></tr>';
            return;
        }

        tbody.innerHTML = '';
        props.forEach(prop => {
            const tax = prop.tax;
            const statusLabel = tax
                ? `<span class="status-badge ${tax.status === 'paid' ? 'status-paid' : 'status-pending'}">${tax.status}</span>`
                : 'No tax';
            const action = tax && tax.status !== 'paid'
                ? `<button class="button" onclick="selectTaxForPayment(${tax.id}, ${tax.total_amount})">Pay Tax</button>`
                : 'Up to date';

            const row = tbody.insertRow();
            row.innerHTML = `
                <td>${prop.street_address}, ${prop.city}</td>
                <td>${prop.surface_couverte || 0} m2</td>
                <td>${prop.affectation || '—'}</td>
                <td>${prop.reference_price ? `${prop.reference_price.toFixed(2)} TND` : '—'}</td>
                <td>${statusLabel}</td>
                <td>${action}</td>
            `;
        });
    } catch (error) {
        console.error('Error loading TIB properties', error);
        tbody.innerHTML = '<tr><td colspan="6">Unable to load TIB properties</td></tr>';
    }
}

async function handleDeclareTibProperty(event) {
    event.preventDefault();
    const mode = document.getElementById('biz_tib_address_mode').value;
    const street = document.getElementById('biz_tib_street_name').value.trim();
    let communeId = document.getElementById('biz_tib_commune').value;
    const communeOther = document.getElementById('biz_tib_commune_other').value.trim();
    let locality = document.getElementById('biz_tib_locality').value || '';
    const localityOther = document.getElementById('biz_tib_locality_other').value.trim();
    const villa = document.getElementById('biz_tib_villa_number').value.trim();
    const resName = document.getElementById('biz_tib_residence_name').value.trim();
    const apt = document.getElementById('biz_tib_apartment_number').value.trim();
    const lat = document.getElementById('biz_tib_lat').value;
    const lng = document.getElementById('biz_tib_lng').value;
    const surface = parseFloat(document.getElementById('tib-surface').value);
    const affectation = document.getElementById('tib-affectation').value;
    const refPrice = parseFloat(document.getElementById('tib-reference-price').value);
    const serviceRate = parseInt(document.getElementById('tib-service-rate').value, 10);
    const messageEl = document.getElementById('tib-declare-message');
    messageEl.textContent = '';

    if (communeId === OTHER_VALUE) {
        const resolved = await resolveCommuneByName(communeOther);
        if (!resolved) { messageEl.textContent = 'Municipality not found. Refine your input.'; return; }
        communeId = resolved;
    }
    if (locality === OTHER_VALUE) locality = localityOther;
    if (!street || !communeId || !surface || !refPrice) { messageEl.textContent = 'Please fill required fields.'; return; }

    const payload = {
        commune_id: Number(communeId),
        address_mode: mode,
        street_name: street,
        locality,
        surface_couverte: surface,
        affectation,
        reference_price_per_m2: refPrice,
        service_rate: serviceRate
    };
    if (mode === 'villa') payload.villa_number = villa; else { payload.residence_name = resName; payload.apartment_number = apt; }
    if (lat && lng) { payload.latitude = Number(lat); payload.longitude = Number(lng); }

    try {
        const { response, data } = await fetchJSON('/tib/properties', {
            method: 'POST',
            body: JSON.stringify(payload)
        });

        if (!response.ok) {
            messageEl.textContent = data.error || 'Failed to declare property.';
            return;
        }

        messageEl.textContent = 'Property declared successfully.';
        event.target.reset();
        loadTibProperties();
        loadOverview();
        loadTaxes();
    } catch (error) {
        messageEl.textContent = 'Network error while declaring property.';
    }
}

async function loadTaxes() {
    const tbody = document.getElementById('taxes-body');
    tbody.innerHTML = '<tr><td colspan="8">Loading...</td></tr>';

    try {
        const { response, data } = await fetchJSON('/ttnb/my-taxes');
        if (!response.ok) {
            tbody.innerHTML = `<tr><td colspan="8">${data.error || 'Failed to load taxes'}</td></tr>`;
            return;
        }

        const taxes = data.taxes || [];
        state.pendingTaxes = taxes.filter(t => t.status !== 'paid');

        document.getElementById('summary-due').textContent = `${(data.summary?.total_due || 0).toFixed(2)} TND`;
        document.getElementById('summary-paid').textContent =
            `${(data.summary?.total_tax - (data.summary?.total_due || 0)).toFixed(2)} TND`;
        document.getElementById('summary-outstanding').textContent =
            `${(data.summary?.total_due || 0).toFixed(2)} TND`;

        if (!taxes.length) {
            tbody.innerHTML = '<tr><td colspan="8">No tax records yet.</td></tr>';
            return;
        }

        tbody.innerHTML = '';
        taxes.forEach(tax => {
            const outstanding = tax.status === 'paid' ? 0 : tax.total_amount;
            const row = tbody.insertRow();
            row.innerHTML = `
                <td>${tax.land_id || '—'}</td>
                <td>${tax.tax_year}</td>
                <td>${(tax.tax_amount || 0).toFixed(2)} TND</td>
                <td>${typeof tax.rate_percent === 'number' && tax.rate_percent > 0 ? `${tax.rate_percent.toFixed(3)} TND/m²` : '—'}</td>
                <td>${(tax.tax_amount || 0).toFixed(2)} TND</td>
                <td>${tax.status === 'paid' ? 'Yes' : 'No'}</td>
                <td>${outstanding.toFixed(2)} TND</td>
                <td>
                    ${tax.status === 'paid'
                        ? '<span class="status-badge status-paid">paid</span>'
                        : (tax.is_payable
                            ? `<button class="button" onclick="selectTaxForPayment(${tax.id}, ${tax.total_amount})">Select</button>`
                            : `Payable from ${tax.payable_from || '—'}`)}
                </td>
            `;
        });
    } catch (error) {
        console.error('Error loading taxes', error);
        tbody.innerHTML = '<tr><td colspan="8">Unable to load taxes</td></tr>';
    }
}

function selectTaxForPayment(taxId, amount) {
    state.selectedTaxId = taxId;
    state.selectedTaxAmount = amount;
    const amountInput = document.getElementById('pay-amount');
    amountInput.value = amount.toFixed(2);
    const message = document.getElementById('payment-message');
    message.textContent = `Selected tax #${taxId} (${amount.toFixed(2)} TND).`;
}

async function handlePayment(event) {
    event.preventDefault();
    if (!state.selectedTaxId) {
        if (state.pendingTaxes.length) {
            const next = state.pendingTaxes[0];
            selectTaxForPayment(next.id, next.total_amount);
        } else {
            document.getElementById('payment-message').textContent = 'No outstanding taxes to pay.';
            return;
        }
    }

    const amount = parseFloat(document.getElementById('pay-amount').value);
    const method = document.getElementById('pay-method').value;
    const messageEl = document.getElementById('payment-message');
    messageEl.textContent = '';

    const payload = {
        tax_id: state.selectedTaxId,
        amount,
        method
    };

    try {
        const { response, data } = await fetchJSON('/payments/pay', {
            method: 'POST',
            body: JSON.stringify(payload)
        });

        if (!response.ok) {
            messageEl.textContent = data.error || 'Payment failed.';
            return;
        }

        messageEl.textContent = `Payment recorded. Receipt: ${data.reference_number}`;
        state.selectedTaxId = null;
        state.selectedTaxAmount = 0;
        loadTaxes();
        loadPayments();
        loadOverview();
    } catch (error) {
        messageEl.textContent = 'Network error while processing payment.';
    }
}

async function loadPayments() {
    const tbody = document.getElementById('payments-body');
    tbody.innerHTML = '<tr><td colspan="5">Loading...</td></tr>';

    try {
        const { response, data } = await fetchJSON('/payments/my-payments');
        if (!response.ok) {
            tbody.innerHTML = `<tr><td colspan="5">${data.error || 'Failed to load payments'}</td></tr>`;
            return;
        }

        const payments = data.payments || [];
        if (!payments.length) {
            tbody.innerHTML = '<tr><td colspan="5">No payment history yet.</td></tr>';
            return;
        }

        tbody.innerHTML = '';
        payments.forEach(payment => {
            const row = tbody.insertRow();
            row.innerHTML = `
                <td>${formatDate(payment.payment_date)}</td>
                <td>${payment.amount.toFixed(2)} TND</td>
                <td>${payment.reference_number || 'N/A'}</td>
                <td>${payment.method}</td>
                <td><span class="status-badge status-paid">${payment.status}</span></td>
            `;
        });
    } catch (error) {
        console.error('Error loading payments', error);
        tbody.innerHTML = '<tr><td colspan="5">Unable to load payments</td></tr>';
    }
}

async function ensureCurrentUser() {
    if (state.currentUserId) return state.currentUserId;
    const { response, data } = await fetchJSON('/auth/me');
    if (response.ok) {
        state.currentUserId = data.id;
        return state.currentUserId;
    }
    throw new Error(data.error || 'Unable to load profile');
}

async function getAttestationStatus() {
    const statusEl = document.getElementById('attestation-status');
    statusEl.textContent = 'Checking...';
    try {
        const userId = await ensureCurrentUser();
        const { response, data } = await fetchJSON(`/payments/check-permit-eligibility/${userId}`);
        if (!response.ok) {
            statusEl.textContent = data.error || 'Unable to fetch eligibility.';
            return;
        }

        if (data.eligible_for_permit) {
            statusEl.textContent = 'All taxes are paid. You can request permits.';
        } else {
            statusEl.textContent = `Unpaid taxes detected: ${data.unpaid_taxes} items totalling ${data.total_due} TND.`;
        }
    } catch (error) {
        statusEl.textContent = 'Failed to check attestation status.';
    }
}

async function handlePermitRequest(event) {
    event.preventDefault();
    const propertyId = parseInt(document.getElementById('permit-land-id').value, 10);
    const typeSelection = document.getElementById('permit-type').value;
    const description = document.getElementById('permit-description').value.trim();
    const messageEl = document.getElementById('permit-message');

    const typeMap = {
        construction: 'construction',
        renovation: 'occupation',
        demolition: 'demolition'
    };

    const payload = {
        permit_type: typeMap[typeSelection] || 'construction',
        property_id: isNaN(propertyId) ? null : propertyId,
        description
    };

    try {
        const { response, data } = await fetchJSON('/permits/request', {
            method: 'POST',
            body: JSON.stringify(payload)
        });

        if (!response.ok) {
            messageEl.textContent = data.error || data.message || 'Permit request failed.';
            return;
        }

        messageEl.textContent = 'Permit request submitted.';
        event.target.reset();
        loadPermits();
        loadOverview();
    } catch (error) {
        messageEl.textContent = 'Network error while requesting permit.';
    }
}

async function loadPermits() {
    const tbody = document.getElementById('permits-body');
    tbody.innerHTML = '<tr><td colspan="6">Loading...</td></tr>';

    try {
        const { response, data } = await fetchJSON('/permits/my-requests');
        if (!response.ok) {
            tbody.innerHTML = `<tr><td colspan="6">${data.error || 'Failed to load permits'}</td></tr>`;
            return;
        }

        const permits = data.permits || [];
        if (!permits.length) {
            tbody.innerHTML = '<tr><td colspan="6">No permit requests yet.</td></tr>';
            return;
        }

        tbody.innerHTML = '';
        permits.forEach(permit => {
            const row = tbody.insertRow();
            row.innerHTML = `
                <td>${permit.id}</td>
                <td>${permit.permit_type}</td>
                <td><span class="status-badge status-${permit.status}">${permit.status}</span></td>
                <td>${formatDate(permit.submitted_date)}</td>
                <td>${formatDate(permit.decision_date)}</td>
                <td>${permit.notes || '—'}</td>
            `;
        });
    } catch (error) {
        console.error('Error loading permits', error);
        tbody.innerHTML = '<tr><td colspan="6">Unable to load permits</td></tr>';
    }
}

async function handleDispute(event) {
    event.preventDefault();
    const taxId = parseInt(document.getElementById('dispute-tax-id').value, 10);
    const amount = parseFloat(document.getElementById('dispute-amount').value);
    const reason = document.getElementById('dispute-reason').value.trim();
    const messageEl = document.getElementById('dispute-message');

    const payload = {
        dispute_type: 'calculation',
        subject: `Dispute for tax #${taxId}`,
        description: reason,
        tax_id: isNaN(taxId) ? null : taxId,
        claimed_amount: isNaN(amount) ? null : amount
    };

    try {
        const { response, data } = await fetchJSON('/disputes/', {
            method: 'POST',
            body: JSON.stringify(payload)
        });

        if (!response.ok) {
            messageEl.textContent = data.error || 'Failed to submit dispute.';
            return;
        }

        messageEl.textContent = 'Dispute submitted successfully.';
        event.target.reset();
        loadDisputes();
    } catch (error) {
        messageEl.textContent = 'Network error while submitting dispute.';
    }
}

async function loadDisputes() {
    const tbody = document.getElementById('disputes-body');
    tbody.innerHTML = '<tr><td colspan="6">Loading...</td></tr>';

    try {
        const { response, data } = await fetchJSON('/disputes/');
        if (!response.ok) {
            tbody.innerHTML = `<tr><td colspan="6">${data.error || 'Failed to load disputes'}</td></tr>`;
            return;
        }

        const disputes = data.disputes || [];
        if (!disputes.length) {
            tbody.innerHTML = '<tr><td colspan="6">No disputes filed.</td></tr>';
            return;
        }

        tbody.innerHTML = '';
        disputes.forEach(dispute => {
            const row = tbody.insertRow();
            row.innerHTML = `
                <td>${dispute.id}</td>
                <td>${dispute.claimed_amount || '—'}</td>
                <td>${dispute.claimed_amount || '—'}</td>
                <td>${dispute.status}</td>
                <td>${dispute.final_decision || 'Pending'}</td>
                <td>${formatDate(dispute.submission_date)}</td>
            `;
        });
    } catch (error) {
        console.error('Error loading disputes', error);
        tbody.innerHTML = '<tr><td colspan="6">Unable to load disputes</td></tr>';
    }
}

async function loadBudgetProjects() {
    const tbody = document.getElementById('budget-body');
    tbody.innerHTML = '<tr><td colspan="6">Loading...</td></tr>';

    try {
        const { response, data } = await fetchJSON('/budget/projects');
        if (!response.ok) {
            tbody.innerHTML = `<tr><td colspan="6">${data.error || 'Failed to load projects'}</td></tr>`;
            return;
        }

        const projects = data.projects || [];
        if (!projects.length) {
            tbody.innerHTML = '<tr><td colspan="6">No budget projects available.</td></tr>';
            return;
        }

        tbody.innerHTML = '';
        projects.forEach(project => {
            const row = tbody.insertRow();
            row.innerHTML = `
                <td>${project.id}</td>
                <td>${project.title}</td>
                <td>${project.budget_amount} TND</td>
                <td>${project.status}</td>
                <td>${project.total_votes}</td>
                <td>
                    ${project.status === 'open_for_voting'
                        ? `<button class="button" onclick="voteForProject(${project.id})">Vote</button>`
                        : 'Voting closed'}
                </td>
            `;
        });
    } catch (error) {
        tbody.innerHTML = '<tr><td colspan="6">Unable to load budget projects</td></tr>';
    }
}

async function voteForProject(projectId) {
    try {
        const { response, data } = await fetchJSON(`/budget/projects/${projectId}/vote`, {
            method: 'POST'
        });

        if (!response.ok) {
            alert(data.error || 'Unable to record vote.');
            return;
        }

        alert('Vote recorded successfully.');
        loadBudgetProjects();
    } catch (error) {
        alert('Network error while voting.');
    }
}

function formatDate(value) {
    if (!value) return '—';
    const date = new Date(value);
    return isNaN(date.getTime()) ? '—' : date.toLocaleDateString();
}

function logout() {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    localStorage.removeItem('role');
    window.location.href = '/common_login/index.html';
}

window.addEventListener('load', () => {
    setupBizAddressUI();
    loadOverview();
    loadProperties();
    loadTibProperties();
    loadTaxes();
    loadPayments();
    loadPermits();
    loadDisputes();
    loadBudgetProjects();
    populateReclamationCities();
    loadReclamations();
});
    // Expose for inline handlers
    window.logout = logout;
    window.showSection = showSection;

// Service complaints (reclamations)
async function submitReclamation(event) {
    event.preventDefault();
    const type = document.getElementById('biz_reclamation_type').value;
    const street = document.getElementById('biz_reclamation_street').value.trim();
    const city = document.getElementById('biz_reclamation_city').value;
    const priority = document.getElementById('biz_reclamation_priority').value || null;
    const description = document.getElementById('biz_reclamation_description').value.trim();
    const statusEl = document.getElementById('biz_reclamation_status');
    if (statusEl) statusEl.textContent = '';

    if (!type || !street || !city || !description) {
        if (statusEl) statusEl.textContent = 'Please fill all required fields.';
        return;
    }

    const payload = { reclamation_type: type, street_address: street, city, description, priority: priority || null };
    const { response, data } = await fetchJSON('/reclamations/', {
        method: 'POST',
        body: JSON.stringify(payload)
    });
    if (!response.ok) {
        if (statusEl) statusEl.textContent = data.error || 'Failed to submit complaint';
        return;
    }
    if (statusEl) statusEl.textContent = 'Complaint submitted';
    const form = document.getElementById('biz_reclamation_form');
    if (form) form.reset();
    loadReclamations();
}

async function loadReclamations() {
    const tbody = document.getElementById('reclamations-body');
    if (!tbody) return;
    tbody.innerHTML = '<tr><td colspan="4">Loading...</td></tr>';
    const { response, data } = await fetchJSON('/reclamations/my-reclamations');
    if (!response.ok) {
        tbody.innerHTML = '<tr><td colspan="4">Complaints endpoint unavailable</td></tr>';
        return;
    }
    const list = data.reclamations || data || [];
    if (!list.length) {
        tbody.innerHTML = '<tr><td colspan="4">No complaints submitted</td></tr>';
        return;
    }
    tbody.innerHTML = '';
    list.forEach(r => {
        const row = tbody.insertRow();
        const status = r.status?.toLowerCase?.() || r.status || 'submitted';
        row.innerHTML = `
            <td>${r.type || r.reclamation_type || '-'}</td>
            <td>${r.street_address ? `${r.street_address}, ${r.city || ''}` : '-'}</td>
            <td><span class="status-badge status-${status}">${r.status || status}</span></td>
            <td>${r.priority || '-'}</td>
        `;
    });
}
