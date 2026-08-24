/**
 * DTCM Dashboard module
 */

let liveChart = null;
let autoRefreshInterval = null;

function initDashboard() {
    updateDashboardData();
    startAutoRefresh();
}

async function updateDashboardData() {
    try {
        const token = localStorage.getItem('dtcm_token');
        if (!token) return;

        // Fetch live data
        const response = await fetch('http://127.0.0.1:5000/api/data/live', {
            headers: { 'Authorization': 'Bearer ' + token }
        });
        
        if (response.status === 401 || response.status === 422) { clearAuth(); showLogin(); return; }
        if (!response.ok) throw new Error('Failed to fetch live data');
        const data = await response.json();
        
        if (!data || data.length === 0) return;
        
        let totalCo2 = 0;
        data.forEach(d => totalCo2 += d.co2_level);
        let avgCo2 = totalCo2 / data.length;
        
        const co2El = document.querySelector('#kpi-co2 .kpi-value');
        if(co2El) co2El.textContent = avgCo2.toFixed(1);
        
        const tempEl = document.querySelector('#kpi-temp .kpi-value');
        if(tempEl) tempEl.textContent = (22 + Math.random()*2).toFixed(1);
        
        const humEl = document.querySelector('#kpi-hum .kpi-value');
        if(humEl) humEl.textContent = (45 + Math.random()*10).toFixed(1);
        
        const pmEl = document.querySelector('#kpi-pm25 .kpi-value');
        if(pmEl) pmEl.textContent = (12 + Math.random()*5).toFixed(1);
        
        const zoneGrid = document.getElementById('zone-grid');
        if (zoneGrid) {
            zoneGrid.innerHTML = '';
            data.forEach(sensor => {
                const isCritical = sensor.co2_level > 500;
                const color = isCritical ? '#ff4444' : (sensor.co2_level > 450 ? '#ffaa00' : '#00cc66');
                
                const html = [
                    '<div style="padding: 1rem; border-bottom: 1px solid rgba(255,255,255,0.1); display: flex; justify-content: space-between; align-items: center;">',
                    '  <div>',
                    '    <div style="font-weight: 500;">' + sensor.sensor_name + '</div>',
                    '    <div style="font-size: 0.8rem; color: #888;">' + sensor.severity_label + '</div>',
                    '  </div>',
                    '  <div style="font-size: 1.2rem; font-weight: 600; color: ' + color + ';">' + sensor.co2_level.toFixed(0) + '</div>',
                    '</div>'
                ].join('');
                
                zoneGrid.innerHTML += html;
            });
        }
        
        if (typeof updateLiveChart === 'function') {
            updateLiveChart(data);
        }

    } catch (error) {
        console.error('Error updating dashboard:', error);
    }
}

function startAutoRefresh() {
    if (autoRefreshInterval) clearInterval(autoRefreshInterval);
    autoRefreshInterval = setInterval(() => {
        if(document.getElementById('page-dashboard') && !document.getElementById('page-dashboard').classList.contains('hidden')) {
            updateDashboardData();
        }
    }, 10000);
}

function stopAutoRefresh() {
    if (autoRefreshInterval) {
        clearInterval(autoRefreshInterval);
        autoRefreshInterval = null;
    }
}

