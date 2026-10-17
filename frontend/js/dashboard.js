/**
 * DTCM — Digital Twin CO2 Monitor
 * Master Enterprise Dashboard Controller (India Infrastructure Edition)
 */

const API_BASE = '/api';

// Station GPS coordinate dictionary for India
const INDIA_STATION_COORDS = {
    1: { lat: 28.6469, lon: 77.3160, city: "New Delhi", zone: "Transit Corridor" },
    2: { lat: 19.0657, lon: 72.8687, city: "Mumbai", zone: "Commercial Center" },
    3: { lat: 13.0287, lon: 77.5197, city: "Bengaluru", zone: "Manufacturing Hub" },
    4: { lat: 28.5355, lon: 77.2732, city: "New Delhi", zone: "Industrial Area" },
    5: { lat: 13.1652, lon: 80.2612, city: "Chennai", zone: "Petrochemical Corridor" },
    6: { lat: 22.5735, lon: 88.4331, city: "Kolkata", zone: "IT Sector" }
};

// Rich Real-World Indian City & Air Shed Intelligence
const CITY_INTELLIGENCE = {
    1: {
        id: 1,
        code: "DL-01",
        city: "New Delhi",
        stationName: "Anand Vihar ISBT",
        state: "Delhi NCR",
        lat: 28.6469,
        lon: 77.3160,
        elevation: "216m ASL",
        zoneCategory: "Interstate Transit Hub & Heavy Traffic Corridor",
        populationDensity: "16,400 persons / km²",
        climateClassification: "Semi-arid continental with severe winter radiation inversions",
        majorEmissionSources: [
            "Heavy interstate diesel bus idling (>3,200 buses/day at ISBT terminal)",
            "Ghazipur landfill methane & surface combustion emissions",
            "Diurnal traffic flux along Vikas Marg & Delhi-Meerut Expressway",
            "Winter agricultural biomass smoke advection from northwest corridors"
        ],
        meteorologicalVulnerability: "High winter boundary-layer depression (dropping to <150m AGL at night), trapping CO₂ and PM2.5 in near-surface stagnation pockets.",
        dacAction: "Deploy Dual Solid-Sorbent Direct Air Capture (DAC) Scrubbers (800t CO₂/yr capacity) with electrostatic particulate pre-filters.",
        dacMitigation: "-28.5 ppm across adjacent 5 km² air shed",
        priorityRank: "Priority 1 (National Hotspot)",
        capexTier: "Tier 1 ($$$)"
    },
    2: {
        id: 2,
        code: "MH-01",
        city: "Mumbai",
        stationName: "Bandra Kurla Complex (BKC)",
        state: "Maharashtra",
        lat: 19.0657,
        lon: 72.8687,
        elevation: "14m ASL",
        zoneCategory: "Commercial Central Business District & Arterial Expressway",
        populationDensity: "12,800 persons / km²",
        climateClassification: "Tropical maritime with diurnal sea-breeze circulation",
        majorEmissionSources: [
            "Heavy private commuter traffic along Western Express Highway & BKC connector",
            "Commercial skyscraper central HVAC and chiller plant energy dissipation",
            "Mithi River channel thermal reflection & micro-climate trapping",
            "Proximity to domestic and international aviation flight corridors"
        ],
        meteorologicalVulnerability: "High ambient relative humidity (>70%) provides moderate natural carbon wash, but afternoon sea-breeze wind reversals cause localized stagnation pockets.",
        dacAction: "Deploy Rooftop Micro-Algae Photobioreactors & Commercial Building Flue Direct Capture Modules.",
        dacMitigation: "-16.2 ppm localized commercial core mitigation",
        priorityRank: "Priority 3 (Commercial Corridor)",
        capexTier: "Tier 1 ($$$)"
    },
    3: {
        id: 3,
        code: "KA-01",
        city: "Bengaluru",
        stationName: "Peenya Industrial Area",
        state: "Karnataka",
        lat: 13.0287,
        lon: 77.5197,
        elevation: "920m ASL",
        zoneCategory: "Heavy Machinery, Precision Engineering & Industrial Cluster",
        populationDensity: "7,200 persons / km²",
        climateClassification: "Tropical savanna highland climate with moderate natural ventilation",
        majorEmissionSources: [
            "Point-source industrial boilers, furnaces, and metal casting flues",
            "Heavy diesel freight transport along NH-48 / Tumkur Road arterial",
            "Industrial diesel generator backup sets (DG power banks)",
            "Precision machining, chemical electroplating, and plastic moulding units"
        ],
        meteorologicalVulnerability: "High altitude (920m) improves overall wind dispersion, but localized valley geometry around Peenya holds point-source industrial plumes.",
        dacAction: "Point-Source Flue Gas Amine Scrubbers coupled with Industrial Micro-Grid Carbon Mineralization Units.",
        dacMitigation: "-22.0 ppm local point-source industrial capture",
        priorityRank: "Priority 5 (Point-Source Cluster)",
        capexTier: "Tier 2 ($$)"
    },
    4: {
        id: 4,
        code: "DL-02",
        city: "New Delhi",
        stationName: "Okhla Industrial Area Phase-III",
        state: "Delhi NCR",
        lat: 28.5355,
        lon: 77.2732,
        elevation: "212m ASL",
        zoneCategory: "Industrial Manufacturing & Commercial Transit Corridor",
        populationDensity: "14,200 persons / km²",
        climateClassification: "Semi-arid continental with severe winter radiation inversions",
        majorEmissionSources: [
            "Okhla Waste-to-Energy incineration plant combustion emissions",
            "Light to medium fabrication machinery and industrial printing presses",
            "Mathura Road and Outer Ring Road heavy commercial freight flux",
            "Dense informal transit clusters and container logistics yards"
        ],
        meteorologicalVulnerability: "Proximity to the Yamuna floodplains causes high moisture retention during morning hours, exacerbating winter photochemical smog.",
        dacAction: "Deploy Modular Solid-Sorbent DAC Pods (500t/yr) combined with Urban Miyawaki Forestry Buffers.",
        dacMitigation: "-24.8 ppm across adjacent industrial corridor",
        priorityRank: "Priority 2 (Industrial Inversion)",
        capexTier: "Tier 1 ($$$)"
    },
    5: {
        id: 5,
        code: "TN-01",
        city: "Chennai",
        stationName: "Manali Industrial Area",
        state: "Tamil Nadu",
        lat: 13.1678,
        lon: 80.2605,
        elevation: "6m ASL",
        zoneCategory: "Petrochemical Corridor & Fertilizer Refining Belt",
        populationDensity: "5,400 persons / km²",
        climateClassification: "Tropical wet-and-dry coastal climate with northeast monsoon",
        majorEmissionSources: [
            "Petroleum refinery flare stacks and crude distillation columns",
            "Fertilizer and chemical manufacturing facilities",
            "Heavy container trailers heading to Chennai and Kamarajar Ports",
            "Thermal power plant stack emissions in adjacent Ennore basin"
        ],
        meteorologicalVulnerability: "Strong coastal breezes aid daytime horizontal dispersion, but nocturnal land breezes carry petrochemical emissions inland toward residential belts.",
        dacAction: "Chemical Amine Absorption Units on Industrial Flues and Bio-Mineralization Micro-Ponds.",
        dacMitigation: "-19.4 ppm industrial plume capture",
        priorityRank: "Priority 6 (Petrochemical Belt)",
        capexTier: "Tier 2 ($$)"
    },
    6: {
        id: 6,
        code: "WB-01",
        city: "Kolkata",
        stationName: "Salt Lake Sector V",
        state: "West Bengal",
        lat: 22.5804,
        lon: 88.4378,
        elevation: "9m ASL",
        zoneCategory: "High-Density IT Commercial & Commuter Arterial",
        populationDensity: "10,500 persons / km²",
        climateClassification: "Tropical wet-and-dry climate with deltaic moisture",
        majorEmissionSources: [
            "Heavy commuter bus and car flux along Eastern Metropolitan (EM) Bypass",
            "High concentration of corporate office diesel generator backups",
            "Construction dust and concrete batching along suburban transit expansions",
            "Regional advection of brick kiln combustion plumes from South 24 Parganas"
        ],
        meteorologicalVulnerability: "Proximity to East Kolkata Wetlands provides natural bio-filtration, but winter calm winds create regional smog accumulation.",
        dacAction: "Deploy Urban Miyawaki Forest Expansion along EM Bypass combined with Modular Bio-Filters.",
        dacMitigation: "-18.0 ppm transit corridor mitigation",
        priorityRank: "Priority 4 (Urban IT Corridor)",
        capexTier: "Tier 2 ($$)"
    }
};

// Application State
const AppState = {
    token: localStorage.getItem('dtcm_token') || '',
    user: JSON.parse(localStorage.getItem('dtcm_user') || 'null'),
    currentPage: 'overview',
    liveData: [],
    activeAlerts: [],
    map: null,
    mapMarkers: [],
    charts: {
        liveStream: null,
        prediction: null,
        simulation: null
    },
    pollingInterval: null
};

document.addEventListener('DOMContentLoaded', () => {
    initClock();
    initAuthUI();
    initCharts();
    initMap();

    // Initial Telemetry Fetch
    fetchLiveData();
    fetchAlerts();
    fetchHotspots();
    fetchOptimizer();
    fetchModelMetrics();

    // Polling every 30 seconds
    AppState.pollingInterval = setInterval(() => {
        fetchLiveData(true);
        fetchAlerts(true);
    }, 30000);
});

// ==========================================
// 1. CLOCK & NAVIGATION
// ==========================================

function initClock() {
    const updateTime = () => {
        const now = new Date();
        // Indian Standard Time (UTC+5:30)
        const istString = now.toLocaleTimeString('en-US', { timeZone: 'Asia/Kolkata', hour12: false });
        const utcString = now.toLocaleTimeString('en-US', { timeZone: 'UTC', hour12: false }) + ' UTC';
        const el = document.getElementById('systemClock');
        if (el) el.innerText = `${istString} IST | ${utcString}`;
    };
    updateTime();
    setInterval(updateTime, 1000);
}

function navigateTo(pageId) {
    AppState.currentPage = pageId;

    document.querySelectorAll('#sidebarNav li').forEach(li => {
        li.classList.toggle('active', li.dataset.page === pageId);
    });

    document.querySelectorAll('.tab-page').forEach(page => {
        page.classList.remove('active');
    });

    const targetPage = document.getElementById(`page-${pageId}`);
    if (targetPage) targetPage.classList.add('active');

    const headings = {
        'overview': 'Metropolitan Telemetry Overview',
        'gis-map': 'National Geospatial Sensor Grid',
        'predictions': 'Empirical Autoregressive Forecasting Engine',
        'sandbox': 'Digital Twin Intervention Sandbox',
        'optimizer': 'Carbon Capture Site Prioritization Matrix',
        'alerts': 'Environmental Incident Registry',
        'reports-hub': 'Regulatory Compliance & Telemetry Ingestion'
    };
    const headingEl = document.getElementById('pageHeading');
    if (headingEl) headingEl.innerText = headings[pageId] || 'Command Center';

    if (pageId === 'gis-map') {
        setTimeout(() => {
            if (AppState.map) {
                AppState.map.invalidateSize();
                AppState.map.setView([21.5, 78.5], 5);
            }
        }, 150);
    } else if (pageId === 'predictions') {
        if (!AppState.charts.prediction) initPredictionChart();
        executePrediction();
        fetchZoneClassification();
    } else if (pageId === 'sandbox') {
        if (!AppState.charts.simulation) initSimulationChart();
        executeDigitalTwinSimulation();
    } else if (pageId === 'optimizer') {
        fetchOptimizer();
    } else if (pageId === 'alerts') {
        fetchAlertsTable('Active');
    }
}

// ==========================================
// 2. AUTHENTICATION & ACCESS CONTROL
// ==========================================

function initAuthUI() {
    const sidebarUser = document.getElementById('sidebarUserName');
    const sidebarRole = document.getElementById('sidebarUserRole');
    const topAuthBtn = document.getElementById('topAuthBtn');

    if (AppState.token && AppState.user) {
        if (sidebarUser) sidebarUser.innerText = AppState.user.name || AppState.user.email.split('@')[0];
        if (sidebarRole) sidebarRole.innerText = formatRole(AppState.user.role);
        if (topAuthBtn) {
            topAuthBtn.innerText = 'Sign Out';
            topAuthBtn.onclick = logout;
        }
    } else {
        if (sidebarUser) sidebarUser.innerText = 'Official Observer';
        if (sidebarRole) sidebarRole.innerText = 'CPCB Public Read-Only';
        if (topAuthBtn) {
            topAuthBtn.innerText = 'Sign In';
            topAuthBtn.onclick = openAuthModal;
        }
    }
}

function formatRole(role) {
    if (!role) return 'General';
    return role.replace(/_/g, ' ').toUpperCase();
}

function openAuthModal() {
    const modal = document.getElementById('authModal');
    if (modal) modal.classList.add('open');
}

function closeAuthModal() {
    const modal = document.getElementById('authModal');
    if (modal) modal.classList.remove('open');
}

let authMode = 'login';
function switchAuthTab(mode) {
    authMode = mode;
    const loginBtn = document.getElementById('tabLoginBtn');
    const regBtn = document.getElementById('tabRegisterBtn');
    const nameGrp = document.getElementById('regNameGroup');
    const roleGrp = document.getElementById('regRoleGroup');
    const submitBtn = document.getElementById('authSubmitBtn');

    if (mode === 'register') {
        loginBtn.classList.remove('active');
        regBtn.classList.add('active');
        nameGrp.style.display = 'block';
        roleGrp.style.display = 'block';
        submitBtn.innerText = 'Register Official Account';
    } else {
        loginBtn.classList.add('active');
        regBtn.classList.remove('active');
        nameGrp.style.display = 'none';
        roleGrp.style.display = 'none';
        submitBtn.innerText = 'Authenticate';
    }
}

async function handleAuthSubmit(e) {
    e.preventDefault();
    const email = document.getElementById('authEmail').value;
    const password = document.getElementById('authPassword').value;
    const name = document.getElementById('authName').value;
    const role = document.getElementById('authRole').value;

    const endpoint = authMode === 'register' ? `${API_BASE}/auth/register` : `${API_BASE}/auth/login`;
    const payload = authMode === 'register' ? { email, password, name, role } : { email, password };

    try {
        const res = await fetch(endpoint, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                ...(AppState.token ? { 'Authorization': `Bearer ${AppState.token}` } : {})
            },
            body: JSON.stringify(payload)
        });

        const data = await res.json();
        if (!res.ok) throw new Error(data.msg || data.error || 'Authentication rejected');

        if (authMode === 'register') {
            showToast('Account registered successfully.');
            await quickLoginAs(email, password, name);
        } else {
            AppState.token = data.access_token;
            AppState.user = {
                id: data.user_id,
                email: data.email,
                name: data.name || email.split('@')[0],
                role: data.role
            };
            localStorage.setItem('dtcm_token', AppState.token);
            localStorage.setItem('dtcm_user', JSON.stringify(AppState.user));

            initAuthUI();
            closeAuthModal();
            showToast(`Session established: ${formatRole(data.role)}`);
        }
    } catch (err) {
        showToast(err.message, 'error');
    }
}

async function quickLoginAs(email, password, label) {
    try {
        const res = await fetch(`${API_BASE}/auth/login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email, password })
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.msg || 'Login failed');

        AppState.token = data.access_token;
        AppState.user = {
            id: data.user_id,
            email: data.email,
            name: data.name || label,
            role: data.role
        };
        localStorage.setItem('dtcm_token', AppState.token);
        localStorage.setItem('dtcm_user', JSON.stringify(AppState.user));

        initAuthUI();
        closeAuthModal();
        showToast(`Authenticated: ${formatRole(data.role)}`);
    } catch (err) {
        showToast(err.message, 'error');
    }
}

function logout() {
    AppState.token = '';
    AppState.user = null;
    localStorage.removeItem('dtcm_token');
    localStorage.removeItem('dtcm_user');
    initAuthUI();
    showToast('Session terminated');
    setTimeout(() => {
        window.location.href = '/login';
    }, 600);
}

// ==========================================
// 3. LIVE DATA & METRICS
// ==========================================

async function fetchLiveData(isBackground = false) {
    try {
        const res = await fetch(`${API_BASE}/data/live`);
        const data = await res.json();
        AppState.liveData = data;

        updateKPIs(data);
        renderSensorNodeList(data);
        updateMapMarkers(data);
        updateForecastSensorOptions(data);

        if (AppState.charts.liveStream && data.length > 0) {
            updateLiveChart(data);
        }

        if (!isBackground) {
            const statusEl = document.getElementById('telemetryStatusText');
            if (statusEl) statusEl.innerText = `${data.length} National Nodes Active`;
        }
    } catch (err) {
        console.error('Error fetching live telemetry:', err);
    }
}

function updateKPIs(data) {
    if (!data || data.length === 0) return;

    let totalCo2 = 0;
    let totalAqi = 0;
    let totalTemp = 0;
    let totalHumidity = 0;
    let totalPm25 = 0;

    data.forEach(d => {
        totalCo2 += d.co2;
        totalAqi += d.aqi;
        totalTemp += d.temperature;
        totalHumidity += d.humidity;
        totalPm25 += d.pm25;
    });

    const count = data.length;
    const avgCo2 = totalCo2 / count;
    const avgAqi = totalAqi / count;
    const avgTemp = totalTemp / count;
    const avgHum = totalHumidity / count;
    const avgPm25 = totalPm25 / count;

    // CO2
    const co2El = document.getElementById('kpi-co2-val');
    const co2Pill = document.getElementById('kpi-co2-pill');
    if (co2El) co2El.innerText = avgCo2.toFixed(1);
    if (co2Pill) {
        if (avgCo2 > 500) {
            co2Pill.className = 'tag-status tag-critical';
            co2Pill.innerText = 'Severe Threshold Exceeded';
        } else if (avgCo2 > 450) {
            co2Pill.className = 'tag-status tag-elevated';
            co2Pill.innerText = 'Elevated Inversion';
        } else {
            co2Pill.className = 'tag-status tag-normal';
            co2Pill.innerText = 'Standard';
        }
    }

    // AQI
    const aqiEl = document.getElementById('kpi-aqi-val');
    const aqiPill = document.getElementById('kpi-aqi-pill');
    const pm25El = document.getElementById('kpi-pm25-text');
    if (aqiEl) aqiEl.innerText = avgAqi.toFixed(0);
    if (pm25El) pm25El.innerText = `PM2.5: ${avgPm25.toFixed(1)} µg/m³`;
    if (aqiPill) {
        if (avgAqi > 300) {
            aqiPill.className = 'tag-status tag-critical';
            aqiPill.innerText = 'Severe / Very Poor';
        } else if (avgAqi > 200) {
            aqiPill.className = 'tag-status tag-elevated';
            aqiPill.innerText = 'Poor';
        } else if (avgAqi > 100) {
            aqiPill.className = 'tag-status tag-moderate';
            aqiPill.innerText = 'Moderate';
        } else {
            aqiPill.className = 'tag-status tag-normal';
            aqiPill.innerText = 'Satisfactory';
        }
    }

    // Weather
    const tempEl = document.getElementById('kpi-temp-val');
    const humEl = document.getElementById('kpi-humidity-text');
    if (tempEl) tempEl.innerText = avgTemp.toFixed(1);
    if (humEl) humEl.innerText = `Relative Humidity: ${avgHum.toFixed(0)}%`;
}

function renderSensorNodeList(data) {
    const container = document.getElementById('sensorNodesList');
    if (!container) return;

    container.innerHTML = '';
    const badge = document.getElementById('sensorCountBadge');
    if (badge) badge.innerText = `${data.length} Stations Online`;

    data.forEach(sensor => {
        let tagClass = 'tag-normal';
        let nodeClass = 'node-normal';
        let severity = 'Nominal';

        if (sensor.co2 > 500) {
            tagClass = 'tag-critical';
            nodeClass = 'node-critical';
            severity = 'Critical';
        } else if (sensor.co2 > 450) {
            tagClass = 'tag-elevated';
            nodeClass = 'node-elevated';
            severity = 'Elevated';
        }

        const div = document.createElement('div');
        div.className = `sensor-row-item ${nodeClass}`;
        div.style.cursor = 'pointer';
        div.title = 'Click to inspect detailed city intelligence and atmospheric profile';
        div.onclick = () => openCityDetailModal(sensor.sensor_id);
        div.innerHTML = `
            <div>
                <div class="node-text-title">${sensor.location}</div>
                <div class="node-text-meta">
                    <span>Node #${sensor.sensor_id}</span>
                    <span>·</span>
                    <span>PM2.5: ${sensor.pm25.toFixed(1)}</span>
                    <span>·</span>
                    <span>${sensor.temperature.toFixed(1)}°C</span>
                </div>
                <div style="font-size: 0.66rem; color: var(--accent-blue); margin-top: 2px;">Inspect City Profile &rarr;</div>
            </div>
            <div>
                <div class="node-numeric-val">${sensor.co2.toFixed(1)} ppm</div>
                <div style="text-align: right; margin-top: 2px;">
                    <span class="tag-status ${tagClass}">${severity}</span>
                </div>
            </div>
        `;
        container.appendChild(div);
    });
}

function updateForecastSensorOptions(data) {
    const select = document.getElementById('forecast-sensor-select');
    if (!select || select.options.length > 0) return;

    data.forEach(d => {
        const opt = document.createElement('option');
        opt.value = d.sensor_id;
        opt.textContent = `${d.location} (Station #${d.sensor_id})`;
        select.appendChild(opt);
    });
}

// ==========================================
// 4. CHART.JS VISUALIZATIONS (PURE BLACK MINIMAL)
// ==========================================

function initCharts() {
    const canvas = document.getElementById('liveStreamChart');
    if (!canvas) return;
    const ctx = canvas.getContext('2d');

    AppState.charts.liveStream = new Chart(ctx, {
        type: 'line',
        data: {
            labels: [],
            datasets: [{
                label: 'National Mean CO₂ (ppm)',
                data: [],
                borderColor: '#ffffff',
                borderWidth: 1.5,
                fill: false,
                tension: 0.2,
                pointRadius: 2.5,
                pointBackgroundColor: '#ffffff'
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    labels: { color: '#a1a1aa', font: { family: 'Inter', size: 10 } }
                },
                tooltip: {
                    backgroundColor: '#09090b',
                    borderColor: '#27272e',
                    borderWidth: 1,
                    titleColor: '#ffffff',
                    bodyColor: '#a1a1aa',
                    padding: 8,
                    callbacks: {
                        label: (ctx) => ` Concentration: ${ctx.parsed.y.toFixed(1)} ppm`
                    }
                }
            },
            scales: {
                x: {
                    grid: { color: '#141418' },
                    ticks: { color: '#52525b', font: { family: 'JetBrains Mono', size: 9 } }
                },
                y: {
                    grid: { color: '#141418' },
                    ticks: { color: '#52525b', font: { family: 'JetBrains Mono', size: 9 } },
                    suggestedMin: 400,
                    suggestedMax: 550
                }
            }
        }
    });

    fetchInitialHistoricalCurve();
}

let currentChartRange = '1h';

async function fetchInitialHistoricalCurve(range = '1h') {
    currentChartRange = range;
    try {
        let hours = 1;
        let limit = 20;
        if (range === '6h') {
            hours = 6;
            limit = 36;
        } else if (range === '24h') {
            hours = 24;
            limit = 48;
        }

        const res = await fetch(`${API_BASE}/data/history?hours=${hours}&limit=${limit}`);
        const history = await res.json();
        if (history && history.length > 0) {
            const chart = AppState.charts.liveStream;
            if (!chart) return;
            
            // Format labels cleanly: HH:mm with unique minute buckets
            chart.data.labels = history.map(h => {
                const rawTs = h.timestamp || h.Timestamp;
                const d = rawTs ? new Date(rawTs) : new Date();
                const hh = String(d.getHours()).padStart(2, '0');
                const mm = String(d.getMinutes()).padStart(2, '0');
                return `${hh}:${mm}`;
            });
            chart.data.datasets[0].data = history.map(h => {
                const val = h.co2 ?? h.CO2Level;
                return val !== undefined && val !== null ? Number(Number(val).toFixed(1)) : 0;
            });
            chart.update();
        }
    } catch (e) {
        console.warn('History fallback:', e);
    }
}

function updateLiveChart(data) {
    const chart = AppState.charts.liveStream;
    if (!chart || !data || data.length === 0) return;

    const avgCo2 = Number((data.reduce((acc, cur) => acc + (cur.co2 ?? cur.CO2Level ?? 0), 0) / data.length).toFixed(1));
    const now = new Date();
    const hh = String(now.getHours()).padStart(2, '0');
    const mm = String(now.getMinutes()).padStart(2, '0');
    const timeLabel = `${hh}:${mm}`;

    const labels = chart.data.labels;
    const values = chart.data.datasets[0].data;

    // If the last label is the current minute, update in-place rather than creating duplicate labels
    if (labels.length > 0 && labels[labels.length - 1] === timeLabel) {
        values[values.length - 1] = avgCo2;
    } else {
        const maxPoints = currentChartRange === '24h' ? 48 : (currentChartRange === '6h' ? 36 : 24);
        if (labels.length >= maxPoints) {
            labels.shift();
            values.shift();
        }
        labels.push(timeLabel);
        values.push(avgCo2);
    }
    chart.update('none');
}

function switchChartRange(range) {
    document.querySelectorAll('.range-toggle-group .range-toggle-btn').forEach(btn => {
        btn.classList.toggle('active', btn.innerText.toLowerCase() === range.toLowerCase());
    });
    fetchInitialHistoricalCurve(range);
}

// ==========================================
// 5. GEOSPATIAL MAP (INDIA TILES)
// ==========================================

function initMap() {
    const mapEl = document.getElementById('map');
    if (!mapEl) return;

    AppState.map = L.map('map', {
        zoomControl: true,
        attributionControl: false
    }).setView([21.5, 78.5], 5); // Centered on India

    // Pure black CartoDB Dark Matter tiles
    L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
        maxZoom: 19,
        subdomains: 'abcd'
    }).addTo(AppState.map);
}

function updateMapMarkers(data) {
    if (!AppState.map) return;

    AppState.mapMarkers.forEach(m => AppState.map.removeLayer(m));
    AppState.mapMarkers = [];

    data.forEach((d) => {
        const coords = INDIA_STATION_COORDS[d.sensor_id] || { lat: 28.6139, lon: 77.2090, city: "Delhi", zone: "National Grid" };

        let color = '#10b981';
        let severityTag = 'Standard';
        if (d.co2 > 500) {
            color = '#ef4444';
            severityTag = 'Critical Threshold Breach';
        } else if (d.co2 > 450) {
            color = '#f59e0b';
            severityTag = 'Elevated Concentration';
        }

        // Dispersion radius
        const circle = L.circle([coords.lat, coords.lon], {
            radius: 8000,
            color: color,
            fillColor: color,
            fillOpacity: 0.12,
            weight: 1
        }).addTo(AppState.map);

        circle.on('click', () => {
            openCityDetailModal(d.sensor_id);
        });

        // Solid station pin
        const marker = L.circleMarker([coords.lat, coords.lon], {
            radius: 7,
            color: '#000000',
            fillColor: color,
            fillOpacity: 1,
            weight: 1.5
        }).addTo(AppState.map);

        marker.on('click', () => {
            openCityDetailModal(d.sensor_id);
        });

        marker.bindPopup(`
            <div style="font-family: 'Inter', sans-serif; color: #000; padding: 4px; min-width: 210px;">
                <div style="font-weight: 700; font-size: 0.88rem; margin-bottom: 2px;">${d.location}</div>
                <div style="font-size: 0.74rem; color: #52525b; margin-bottom: 6px;">Station ID: #${d.sensor_id} · ${coords.city} (${coords.zone})</div>
                <div style="font-size: 0.82rem; font-family: 'JetBrains Mono', monospace; font-weight: 700;">
                    CO₂ Level: ${d.co2.toFixed(1)} ppm
                </div>
                <div style="font-size: 0.74rem; color: #71717a; margin-top: 2px;">
                    AQI: ${d.aqi.toFixed(0)} · Ambient Temp: ${d.temperature.toFixed(1)}°C
                </div>
                <div style="margin-top: 4px; font-size: 0.68rem; font-weight: 700; text-transform: uppercase; color: ${color};">
                    ${severityTag}
                </div>
                <button onclick="openCityDetailModal(${d.sensor_id})" style="width: 100%; margin-top: 8px; background: #000000; color: #ffffff; border: 1px solid #333338; padding: 6px 10px; border-radius: 3px; font-size: 0.72rem; font-weight: 600; cursor: pointer; display: flex; align-items: center; justify-content: center; gap: 4px;">
                    <span>Inspect City Intelligence</span> &rarr;
                </button>
            </div>
        `);

        AppState.mapMarkers.push(circle, marker);
    });
}

// ==========================================
// 5.1 CITY INTELLIGENCE & DEEP-DIVE MODAL
// ==========================================

let cityHistoryChart = null;

window.openCityDetailModal = function(sensorId) {
    const sId = parseInt(sensorId) || 1;
    const meta = CITY_INTELLIGENCE[sId] || CITY_INTELLIGENCE[1];
    const live = (AppState.liveData || []).find(d => d.sensor_id === sId) || {
        co2: 440.0,
        temperature: 28.0,
        humidity: 60.0,
        pm25: 50.0,
        aqi: 130.0
    };

    AppState.activeCitySensorId = sId;

    // Populate header
    const codeEl = document.getElementById('cityModalCode');
    const titleEl = document.getElementById('cityModalTitle');
    const subEl = document.getElementById('cityModalSubtitle');
    if (codeEl) codeEl.innerText = meta.code;
    if (titleEl) titleEl.innerText = `${meta.stationName}, ${meta.city}`;
    if (subEl) subEl.innerText = `${meta.zoneCategory} • ${meta.state} (${meta.lat.toFixed(4)}°N, ${meta.lon.toFixed(4)}°E)`;

    // Populate metrics
    const co2El = document.getElementById('cityModalCo2');
    const sevEl = document.getElementById('cityModalSeverity');
    if (co2El) co2El.innerText = `${live.co2.toFixed(1)} ppm`;
    if (sevEl) {
        if (live.co2 > 500) {
            sevEl.innerText = 'Critical Inversion Breach';
            sevEl.style.color = 'var(--status-critical)';
        } else if (live.co2 > 450) {
            sevEl.innerText = 'Elevated Threshold';
            sevEl.style.color = 'var(--status-warning)';
        } else {
            sevEl.innerText = 'Normal Concentration';
            sevEl.style.color = 'var(--status-normal)';
        }
    }

    const tempEl = document.getElementById('cityModalTemp');
    const humEl = document.getElementById('cityModalHum');
    const aqiEl = document.getElementById('cityModalAqi');
    const pm25El = document.getElementById('cityModalPm25');
    const popEl = document.getElementById('cityModalPop');
    const elevEl = document.getElementById('cityModalElev');

    if (tempEl) tempEl.innerText = `${live.temperature.toFixed(1)} °C`;
    if (humEl) humEl.innerText = `Humidity: ${live.humidity.toFixed(0)}%`;
    if (aqiEl) aqiEl.innerText = `AQI ${live.aqi.toFixed(0)}`;
    if (pm25El) pm25El.innerText = `PM2.5: ${live.pm25.toFixed(1)} µg/m³`;
    if (popEl) popEl.innerText = meta.populationDensity;
    if (elevEl) elevEl.innerText = `Elevation: ${meta.elevation}`;

    // Populate environmental vulnerability & drivers
    const vulEl = document.getElementById('cityModalVulnerability');
    const climEl = document.getElementById('cityModalClimate');
    const driversUl = document.getElementById('cityModalDrivers');

    if (vulEl) vulEl.innerText = meta.meteorologicalVulnerability;
    if (climEl) climEl.innerText = meta.climateClassification;

    if (driversUl) {
        driversUl.innerHTML = '';
        meta.majorEmissionSources.forEach(src => {
            const li = document.createElement('li');
            li.style.marginBottom = '4px';
            li.innerText = src;
            driversUl.appendChild(li);
        });
    }

    // Populate DAC & mitigation
    const dacEl = document.getElementById('cityModalDacAction');
    const mitEl = document.getElementById('cityModalMitigation');
    const capexEl = document.getElementById('cityModalCapex');
    const priEl = document.getElementById('cityModalPriority');

    if (dacEl) dacEl.innerText = meta.dacAction;
    if (mitEl) mitEl.innerText = meta.dacMitigation;
    if (capexEl) capexEl.innerText = meta.capexTier;
    if (priEl) priEl.innerText = meta.priorityRank;

    // Show modal
    const overlay = document.getElementById('cityModalOverlay');
    if (overlay) overlay.style.display = 'flex';

    // Fetch and render 24h historical curve
    loadCityHistoryChart(sId);
};

window.closeCityModal = function() {
    const overlay = document.getElementById('cityModalOverlay');
    if (overlay) overlay.style.display = 'none';
    if (cityHistoryChart) {
        cityHistoryChart.destroy();
        cityHistoryChart = null;
    }
};

window.loadCityHistoryChart = async function(sensorId) {
    const canvas = document.getElementById('cityHistoryChartCanvas');
    if (!canvas) return;

    if (cityHistoryChart) {
        cityHistoryChart.destroy();
        cityHistoryChart = null;
    }

    try {
        const res = await fetch(`${API_BASE}/data/history?sensor_id=${sensorId}&hours=24`);
        const historyData = await res.json();
        
        let labels = [];
        let co2Vals = [];

        if (Array.isArray(historyData) && historyData.length > 0) {
            labels = historyData.map(d => {
                const rawTs = d.timestamp || d.Timestamp;
                const date = rawTs ? new Date(rawTs) : new Date();
                const h = isNaN(date.getHours()) ? 0 : date.getHours();
                const m = isNaN(date.getMinutes()) ? 0 : date.getMinutes();
                return `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}`;
            });
            co2Vals = historyData.map(d => {
                const val = d.co2 ?? d.CO2Level;
                return val !== undefined && val !== null && !isNaN(val) ? Number(val) : null;
            }).filter(v => v !== null);
        }

        // Smooth diurnal fallback if database has no history for this sensor
        if (co2Vals.length === 0) {
            labels = [];
            const liveMatch = (AppState.liveData || []).find(d => d.sensor_id === parseInt(sensorId));
            const baseCo2 = liveMatch?.co2 || 435.0;
            const currentHour = new Date().getHours();
            for (let i = 24; i >= 0; i--) {
                const h = (currentHour - i + 24) % 24;
                labels.push(`${String(h).padStart(2, '0')}:00`);
                const peak = Math.sin((h - 4) / 12 * Math.PI) * 25;
                co2Vals.push(Number((baseCo2 + peak + Math.sin(h * 2) * 4).toFixed(1)));
            }
        }

        const minVal = Math.min(...co2Vals);
        const maxVal = Math.max(...co2Vals);

        const ctx = canvas.getContext('2d');
        cityHistoryChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [{
                    label: 'CO₂ Concentration (ppm)',
                    data: co2Vals,
                    borderColor: '#ffffff',
                    backgroundColor: 'rgba(255, 255, 255, 0.05)',
                    borderWidth: 1.5,
                    pointRadius: 1,
                    pointHoverRadius: 4,
                    pointBackgroundColor: '#ffffff',
                    fill: true,
                    tension: 0.3
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        mode: 'index',
                        intersect: false,
                        backgroundColor: '#111115',
                        titleColor: '#a1a1aa',
                        bodyColor: '#ffffff',
                        borderColor: '#27272e',
                        borderWidth: 1,
                        callbacks: {
                            label: (ctx) => `CO₂: ${ctx.parsed.y.toFixed(1)} ppm`
                        }
                    }
                },
                scales: {
                    x: {
                        grid: { display: false },
                        ticks: { color: '#71717a', font: { family: 'JetBrains Mono', size: 9 }, maxTicksLimit: 8 }
                    },
                    y: {
                        grid: { color: '#1c1c21' },
                        ticks: { color: '#71717a', font: { family: 'JetBrains Mono', size: 9 } },
                        suggestedMin: Math.floor(minVal - 10),
                        suggestedMax: Math.ceil(maxVal + 10)
                    }
                }
            }
        });
    } catch (e) {
        console.warn('Could not load city history chart:', e);
    }
};

window.simulateCityInSandbox = function() {
    const sId = AppState.activeCitySensorId || 1;
    closeCityModal();
    navigateTo('sandbox');
    showToast(`Loaded ${CITY_INTELLIGENCE[sId]?.stationName || 'Station'} into Digital Twin Sandbox.`);
};

window.exportCityCsv = function() {
    const sId = AppState.activeCitySensorId || 1;
    window.open(`${API_BASE}/reports/export?sensor_id=${sId}&format=csv`, '_blank');
    showToast(`Downloading telemetry CSV for Station #${sId}...`);
};

async function fetchHotspots() {
    try {
        const res = await fetch(`${API_BASE}/data/hotspots`);
        const data = await res.json();
        const container = document.getElementById('hotspotListContainer');
        if (!container) return;

        container.innerHTML = '';
        data.forEach((item, idx) => {
            const isSevere = item.co2 > 450;
            container.innerHTML += `
                <div class="hotspot-row" onclick="openCityDetailModal(${item.sensor_id})" style="cursor: pointer;" title="Inspect Station Telemetry & Demographics">
                    <div>
                        <span class="hotspot-idx">0${idx + 1}</span>
                        <span>${item.location}</span>
                    </div>
                    <span style="font-family: var(--font-mono); font-weight: 600; color: ${isSevere ? 'var(--status-critical)' : 'var(--text-primary)'}">
                        ${item.co2.toFixed(1)} ppm
                    </span>
                </div>
            `;
        });
    } catch (e) {
        console.warn('Hotspot fetch error:', e);
    }
}

// ==========================================
// 6. FORECASTING ENGINE
// ==========================================

function initPredictionChart() {
    const canvas = document.getElementById('predictionChartCanvas');
    if (!canvas) return;
    const ctx = canvas.getContext('2d');

    AppState.charts.prediction = new Chart(ctx, {
        type: 'line',
        data: {
            labels: [],
            datasets: [
                {
                    label: 'Projected CO₂ Mean',
                    data: [],
                    borderColor: '#ffffff',
                    borderWidth: 1.5,
                    tension: 0.2,
                    pointRadius: 1,
                    fill: false
                },
                {
                    label: '95th Percentile Bound',
                    data: [],
                    borderColor: '#3f3f46',
                    borderDash: [3, 3],
                    pointRadius: 0,
                    fill: '+1',
                    backgroundColor: 'rgba(255, 255, 255, 0.04)'
                },
                {
                    label: '5th Percentile Bound',
                    data: [],
                    borderColor: '#3f3f46',
                    borderDash: [3, 3],
                    pointRadius: 0,
                    fill: false
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { labels: { color: '#a1a1aa', font: { family: 'Inter', size: 10 } } }
            },
            scales: {
                x: {
                    grid: { color: '#141418' },
                    ticks: { color: '#52525b', font: { family: 'JetBrains Mono', size: 9 } }
                },
                y: {
                    grid: { color: '#141418' },
                    ticks: { color: '#52525b', font: { family: 'JetBrains Mono', size: 9 } }
                }
            }
        }
    });
}

async function executePrediction() {
    const sensorSelect = document.getElementById('forecast-sensor-select');
    const horizonSelect = document.getElementById('forecast-horizon-select');
    const sensorId = sensorSelect ? (sensorSelect.value || 1) : 1;
    const horizon = horizonSelect ? horizonSelect.value : '24h';

    if (!AppState.token) {
        await ensureDemoAuth();
    }

    const isLongTerm = horizon !== '24h';
    const endpoint = isLongTerm ? `${API_BASE}/predict/long-term` : `${API_BASE}/predict/short-term`;
    const payload = isLongTerm
        ? { sensor_id: parseInt(sensorId), days: horizon === '7d' ? 7 : 30 }
        : { sensor_id: parseInt(sensorId) };

    const btn = document.getElementById('btnRunPrediction');
    if (btn) btn.innerText = 'Calculating Autoregressive Vectors...';

    try {
        const res = await fetch(endpoint, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${AppState.token}`
            },
            body: JSON.stringify(payload)
        });

        const data = await res.json();
        if (!res.ok) throw new Error(data.error || data.msg || 'Calculation error');

        renderPredictionChart(data, horizon);

        const badge = document.getElementById('forecastEngineBadge');
        if (badge) badge.innerText = data.model_used || 'RandomForest';

        const title = document.getElementById('forecastChartTitle');
        if (title) title.innerText = `${horizon.toUpperCase()} Projected Concentration Trajectory`;

        showToast(`Trajectory generated for Station #${sensorId}`);
    } catch (err) {
        showToast(err.message, 'error');
    } finally {
        if (btn) btn.innerText = 'Generate Forecast Trajectory';
    }
}

function renderPredictionChart(data, horizon) {
    if (!AppState.charts.prediction) initPredictionChart();
    const chart = AppState.charts.prediction;

    const count = data.predictions.length;
    chart.data.labels = Array.from({ length: count }, (_, i) => {
        if (horizon === '24h') return `+${i + 1}h`;
        const day = Math.floor(i / 24) + 1;
        const hour = i % 24;
        return hour === 0 ? `D${day}` : `+${i}h`;
    });

    chart.data.datasets[0].data = data.predictions;
    chart.data.datasets[1].data = data.confidence_high;
    chart.data.datasets[2].data = data.confidence_low;
    chart.update();
}

async function fetchZoneClassification() {
    try {
        const res = await fetch(`${API_BASE}/predict/classify/zones`, { method: 'POST' });
        const data = await res.json();
        const container = document.getElementById('zoneSeverityLabels');
        if (!container || !data.zones) return;

        container.innerHTML = '';
        data.zones.forEach(z => {
            let tagClass = 'tag-normal';
            if (z.severity_class === 3) tagClass = 'tag-critical';
            else if (z.severity_class === 2) tagClass = 'tag-elevated';
            else if (z.severity_class === 1) tagClass = 'tag-moderate';

            container.innerHTML += `
                <div style="display: flex; justify-content: space-between; align-items: center; padding: 4px 0; border-bottom: 1px solid #141418; font-size: 0.76rem;">
                    <span>Station Node #${z.sensor_id}</span>
                    <span class="tag-status ${tagClass}">${z.severity_label}</span>
                </div>
            `;
        });
    } catch (e) {
        console.warn('Zone classification error:', e);
    }
}

async function fetchModelMetrics() {
    try {
        const res = await fetch(`${API_BASE}/predict/metrics`);
        const data = await res.json();
        const r2 = document.getElementById('modelR2Score');
        const mae = document.getElementById('modelMaeScore');
        if (r2 && data.r2_score) r2.innerText = data.r2_score.toFixed(2);
        if (mae && data.mae) mae.innerText = `${data.mae.toFixed(2)} ppm`;
    } catch (e) {
        console.warn('Metrics error:', e);
    }
}

// ==========================================
// 7. SCENARIO MODELING (DIGITAL TWIN)
// ==========================================

function updateSliderVal(type, val, suffix) {
    const el = document.getElementById(`${type}ValBadge`);
    if (el) el.innerText = `${val}${suffix}`;
}

function initSimulationChart() {
    const canvas = document.getElementById('simulationChartCanvas');
    if (!canvas) return;
    const ctx = canvas.getContext('2d');

    AppState.charts.simulation = new Chart(ctx, {
        type: 'line',
        data: {
            labels: [],
            datasets: [
                {
                    label: 'Unmitigated Baseline',
                    data: [],
                    borderColor: '#71717a',
                    borderWidth: 1.5,
                    borderDash: [3, 3],
                    pointRadius: 0,
                    fill: false
                },
                {
                    label: 'Projected Abatement (Mitigated)',
                    data: [],
                    borderColor: '#ffffff',
                    borderWidth: 1.5,
                    fill: false,
                    tension: 0.2,
                    pointRadius: 1.5
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { labels: { color: '#a1a1aa', font: { family: 'Inter', size: 10 } } }
            },
            scales: {
                x: {
                    grid: { color: '#141418' },
                    ticks: { color: '#52525b', font: { family: 'JetBrains Mono', size: 9 } }
                },
                y: {
                    grid: { color: '#141418' },
                    ticks: { color: '#52525b', font: { family: 'JetBrains Mono', size: 9 } }
                }
            }
        }
    });
}

async function executeDigitalTwinSimulation() {
    const traffic = document.getElementById('simTrafficSlider')?.value || 25;
    const green = document.getElementById('simGreenSlider')?.value || 8;
    const dac = document.getElementById('simDacSlider')?.value || 4;
    const scenarioName = document.getElementById('simScenarioName')?.value || 'Intervention Model';

    const industrialShutdown = [];
    if (document.getElementById('indZone1')?.checked) industrialShutdown.push('Zone 1');
    if (document.getElementById('indZone2')?.checked) industrialShutdown.push('Zone 2');

    try {
        const res = await fetch(`${API_BASE}/twin/simulate`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                traffic_reduction_pct: parseFloat(traffic),
                green_area_increase_km2: parseFloat(green),
                dac_units: parseInt(dac),
                industrial_shutdown: industrialShutdown,
                duration_hours: 24,
                scenario_name: scenarioName
            })
        });

        const data = await res.json();
        if (!res.ok) throw new Error(data.error || 'Simulation failed');

        const bEl = document.getElementById('simBaselinePpm');
        const pEl = document.getElementById('simProjectedPpm');
        const rEl = document.getElementById('simReductionPct');
        if (bEl) bEl.innerText = `${data.baseline_co2} ppm`;
        if (pEl) pEl.innerText = `${data.projected_co2} ppm`;
        if (rEl) rEl.innerText = `-${data.reduction_pct}%`;

        if (!AppState.charts.simulation) initSimulationChart();
        const chart = AppState.charts.simulation;
        chart.data.labels = Array.from({ length: data.hourly_forecast.length }, (_, i) => `+${i + 1}h`);
        chart.data.datasets[0].data = Array(data.hourly_forecast.length).fill(data.baseline_co2);
        chart.data.datasets[1].data = data.hourly_forecast;
        chart.update();

        const breakdownGrid = document.getElementById('simBreakdownGrid');
        if (breakdownGrid && data.breakdown) {
            breakdownGrid.innerHTML = `
                <div style="background: var(--bg-card); padding: 8px; border: 1px solid var(--border-dim);">
                    <div style="color: var(--text-tertiary); font-size: 0.65rem;">Traffic Curtailment</div>
                    <div style="font-family: var(--font-mono); font-weight: 600; color: #fff;">-${data.breakdown.traffic_reduction_ppm} ppm</div>
                </div>
                <div style="background: var(--bg-card); padding: 8px; border: 1px solid var(--border-dim);">
                    <div style="color: var(--text-tertiary); font-size: 0.65rem;">Urban Forestry</div>
                    <div style="font-family: var(--font-mono); font-weight: 600; color: #fff;">-${data.breakdown.green_canopy_ppm} ppm</div>
                </div>
                <div style="background: var(--bg-card); padding: 8px; border: 1px solid var(--border-dim);">
                    <div style="color: var(--text-tertiary); font-size: 0.65rem;">Industrial Curtailment</div>
                    <div style="font-family: var(--font-mono); font-weight: 600; color: #fff;">-${data.breakdown.industrial_curtailment_ppm} ppm</div>
                </div>
                <div style="background: var(--bg-card); padding: 8px; border: 1px solid var(--border-dim);">
                    <div style="color: var(--text-tertiary); font-size: 0.65rem;">Direct Air Capture</div>
                    <div style="font-family: var(--font-mono); font-weight: 600; color: #fff;">-${data.breakdown.dac_capture_ppm} ppm</div>
                </div>
            `;
        }

        showToast(`Model calculated: -${data.reduction_pct}% net concentration abatement`);
    } catch (err) {
        showToast(err.message, 'error');
    }
}

// ==========================================
// 8. CAPTURE SITE PRIORITIZATION
// ==========================================

async function fetchOptimizer() {
    try {
        const res = await fetch(`${API_BASE}/twin/optimizer`);
        const data = await res.json();
        const tbody = document.getElementById('optimizerTableBody');
        if (!tbody || !data.recommendations) return;

        tbody.innerHTML = '';
        data.recommendations.forEach((rec, idx) => {
            tbody.innerHTML += `
                <tr onclick="openCityDetailModal(${rec.sensor_id})" style="cursor: pointer;" title="Inspect Station Telemetry & DAC Profile">
                    <td style="font-family: var(--font-mono); font-weight: 600; color: var(--text-tertiary);">0${idx + 1}</td>
                    <td style="font-weight: 600; color: #ffffff;">${rec.location}</td>
                    <td><span class="tag-status tag-normal">${rec.category}</span></td>
                    <td style="font-family: var(--font-mono);">${rec.co2_ppm.toFixed(1)} ppm</td>
                    <td style="font-family: var(--font-mono);">${rec.population_density.toLocaleString()} /km²</td>
                    <td style="font-family: var(--font-mono);">${(rec.accessibility_score * 100).toFixed(0)}%</td>
                    <td style="font-family: var(--font-mono); font-weight: 700; color: #ffffff;">${rec.priority_score}</td>
                    <td><span style="font-family: var(--font-mono); color: var(--text-tertiary);">${rec.capex_tier}</span></td>
                    <td style="font-size: 0.74rem; color: var(--text-secondary);">${rec.recommended_action}</td>
                </tr>
            `;
        });
    } catch (e) {
        console.warn('Optimizer error:', e);
    }
}

// ==========================================
// 9. INCIDENT REGISTRY
// ==========================================

async function fetchAlerts(isBackground = false) {
    try {
        const res = await fetch(`${API_BASE}/alerts/active`);
        const alerts = await res.json();
        AppState.activeAlerts = alerts;

        const countEl = document.getElementById('kpi-alerts-val');
        const pillEl = document.getElementById('kpi-alerts-pill');
        if (countEl) countEl.innerText = alerts.length;
        if (pillEl) {
            if (alerts.length > 0) {
                pillEl.className = 'tag-status tag-critical';
                pillEl.innerText = `${alerts.length} Breaches`;
            } else {
                pillEl.className = 'tag-status tag-normal';
                pillEl.innerText = 'All Clear';
            }
        }
    } catch (e) {
        console.warn('Alerts error:', e);
    }
}

async function fetchAlertsTable(filter = 'Active') {
    const endpoint = filter === 'Active' ? `${API_BASE}/alerts/active` : `${API_BASE}/alerts/history`;
    try {
        const res = await fetch(endpoint);
        const alerts = await res.json();
        const tbody = document.getElementById('alertsTableBody');
        if (!tbody) return;

        tbody.innerHTML = '';
        if (alerts.length === 0) {
            tbody.innerHTML = `<tr><td colspan="8" style="text-align: center; color: var(--text-muted); padding: 24px;">No active environmental incidents on record.</td></tr>`;
            return;
        }

        alerts.forEach(a => {
            const isCrit = a.type === 'Critical' || a.co2 > 500;
            const statusTag = a.status === 'Active' ? 'tag-critical' : 'tag-normal';

            tbody.innerHTML += `
                <tr>
                    <td style="font-family: var(--font-mono);">#${a.id}</td>
                    <td><span class="tag-status ${statusTag}">${a.status}</span></td>
                    <td><span class="tag-status ${isCrit ? 'tag-critical' : 'tag-moderate'}">${a.type}</span></td>
                    <td style="font-weight: 600; color: #fff;">${a.location}</td>
                    <td style="font-family: var(--font-mono); font-weight: 600;">${a.co2.toFixed(1)} ppm</td>
                    <td style="font-family: var(--font-mono); font-size: 0.72rem; color: var(--text-tertiary);">${new Date(a.time).toLocaleString('en-IN', { timeZone: 'Asia/Kolkata' })}</td>
                    <td>${a.message}</td>
                    <td>
                        ${a.status === 'Active' ? `
                            <button class="btn-minimal" onclick="acknowledgeAlert(${a.id})">
                                Acknowledge
                            </button>
                        ` : `<span style="font-size: 0.72rem; color: var(--text-muted);">Processed</span>`}
                    </td>
                </tr>
            `;
        });
    } catch (e) {
        console.error('Alerts table fetch error:', e);
    }
}

function filterAlerts(type) {
    document.querySelectorAll('#page-alerts .range-toggle-btn').forEach(btn => {
        btn.classList.toggle('active', btn.innerText.includes(type));
    });
    fetchAlertsTable(type);
}

async function acknowledgeAlert(alertId) {
    if (!AppState.token) {
        await ensureDemoAuth();
    }

    try {
        const res = await fetch(`${API_BASE}/alerts/${alertId}/acknowledge`, {
            method: 'PUT',
            headers: {
                'Authorization': `Bearer ${AppState.token}`,
                'Content-Type': 'application/json'
            }
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.msg || 'Unauthorized');

        showToast(`Incident #${alertId} verified and acknowledged`);
        fetchAlertsTable('Active');
        fetchAlerts();
    } catch (err) {
        showToast(err.message, 'error');
    }
}

// ==========================================
// 10. COMPLIANCE PDF REPORT & CSV INGESTION
// ==========================================

async function generateAndDownloadReport() {
    if (!AppState.token) {
        await ensureDemoAuth();
    }

    const start = document.getElementById('reportStartDate')?.value || '2025-01-01';
    const end = document.getElementById('reportEndDate')?.value || '2026-10-13';
    const zones = document.getElementById('reportZonesSelect')?.value || 'All National Monitoring Stations';

    const btn = document.getElementById('btnDownloadReport');
    if (btn) btn.innerText = 'Compiling PDF Compliance Audit...';

    try {
        const res = await fetch(`${API_BASE}/reports/generate`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${AppState.token}`
            },
            body: JSON.stringify({
                start_date: start,
                end_date: end,
                zones: zones
            })
        });

        const data = await res.json();
        if (!res.ok) throw new Error(data.msg || data.error || 'Report generation error');

        const downloadUrl = data.download_url;
        const link = document.createElement('a');
        link.href = downloadUrl;
        link.download = `DTCM_CPCB_Compliance_${data.report_id}.pdf`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);

        const area = document.getElementById('reportDownloadArea');
        if (area) {
            area.innerHTML = `
                <div style="background: var(--bg-surface); border: 1px solid var(--border-strong); padding: 10px; border-radius: 3px; font-size: 0.76rem; color: #fff;">
                    Official audit report compiled. <a href="${downloadUrl}" target="_blank" style="color: #fff; text-decoration: underline; margin-left: 4px;">Direct link</a>
                </div>
            `;
        }

        showToast('PDF Compliance Report compiled and downloaded.');
    } catch (err) {
        showToast(err.message, 'error');
    } finally {
        if (btn) btn.innerText = 'Compile & Download PDF';
    }
}

function handleFileSelected(e) {
    const file = e.target.files[0];
    const info = document.getElementById('fileSelectedInfo');
    if (file && info) {
        info.style.display = 'block';
        info.innerText = `Selected File: ${file.name} (${(file.size / 1024).toFixed(1)} KB)`;
    }
}

window.downloadCsvTemplate = function() {
    window.open(`${API_BASE}/data/template/csv`, '_blank');
    showToast('Downloading DTCM compliant CSV template...');
};

async function uploadCsvFile() {
    const input = document.getElementById('csvFileInput');
    if (!input || !input.files || input.files.length === 0) {
        showToast('Please select a CSV file first.', 'error');
        return;
    }

    if (!AppState.token) {
        await ensureDemoAuth();
    }

    const formData = new FormData();
    formData.append('file', input.files[0]);

    try {
        showToast('Parsing and validating schema...');
        const res = await fetch(`${API_BASE}/data/import/csv`, {
            method: 'POST',
            headers: {
                ...(AppState.token ? { 'Authorization': `Bearer ${AppState.token}` } : {})
            },
            body: formData
        });

        const data = await res.json();
        if (!res.ok) throw new Error(data.error || data.msg || 'CSV upload error');

        showToast(data.msg || 'Dataset ingested into database successfully.', 'success');
        fetchLiveData();
        fetchHotspots();
        if (typeof fetchOptimizer === 'function') fetchOptimizer();

        // Clear input
        input.value = '';
        const info = document.getElementById('fileSelectedInfo');
        if (info) info.style.display = 'none';
    } catch (err) {
        showToast(err.message, 'error');
    }
}

// ==========================================
// 11. HELPERS & TOASTS
// ==========================================

async function ensureDemoAuth() {
    await quickLoginAs('admin@dtcm.com', 'admin123', 'Administrator');
}

function manualRefreshData() {
    fetchLiveData();
    fetchAlerts();
    fetchHotspots();
    showToast('Telemetry stream refreshed');
}

function showToast(msg, type = 'info') {
    const container = document.getElementById('toastContainer');
    if (!container) return;

    const toast = document.createElement('div');
    toast.className = 'toast-item';
    if (type === 'error') {
        toast.style.borderColor = 'var(--status-critical)';
        toast.style.color = 'var(--status-critical)';
    }

    toast.innerText = msg;
    container.appendChild(toast);

    setTimeout(() => {
        toast.style.opacity = '0';
        setTimeout(() => toast.remove(), 250);
    }, 3200);
}
