let simChart = null;

function initSimulation() {
    const btn = document.getElementById('btn-run-sim');
    if (btn) btn.addEventListener('click', runSimulation);
    // Draw initial empty/demo chart
    const ctx = document.getElementById('sim-chart');
    if (ctx && !simChart) {
        simChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: ['+1h', '+2h', '+3h', '+4h', '+5h', '+6h'],
                datasets: [
                    { label: 'Baseline', data: [420, 425, 430, 440, 435, 420], borderColor: '#888', borderDash: [5,5] },
                    { label: 'Simulated', data: [420, 420, 415, 410, 405, 400], borderColor: '#00cc66', backgroundColor: 'rgba(0, 204, 102, 0.1)', fill: true }
                ]
            },
            options: { responsive: true, maintainAspectRatio: false }
        });
    }
}

async function runSimulation() {
    const ctx = document.getElementById('sim-chart');
    if (!ctx) return;
    
    const traffic = parseInt(document.getElementById('sim-traffic')?.value || 20);
    const ventilation = parseInt(document.getElementById('sim-ventilation')?.value || 15);
    
    // Animate to loading state
    simChart.data.datasets[1].data = [420, 420, 420, 420, 420, 420];
    simChart.update();

    setTimeout(() => {
        // Mocking the simulation processing time and result
        const baseline = [420, 425, 430, 440, 435, 420];
        const simulated = baseline.map((v, i) => v - (traffic*0.5 + ventilation*0.8) * (i/5));
        
        simChart.data.datasets[0].data = baseline;
        simChart.data.datasets[1].data = simulated;
        simChart.update();
        
        alert(`Simulation Complete! Peak reduction: ${((1 - simulated[3]/baseline[3])*100).toFixed(1)}%`);
    }, 1500);
}

function initAlerts() {
    loadAlerts();
    setInterval(loadAlerts, 10000);
}

async function loadAlerts() {
    const container = document.getElementById('alerts-container');
    if (!container) return;
    
    const token = localStorage.getItem('dtcm_token');
    if (!token) return;

    try {
        const response = await fetch('http://127.0.0.1:5000/api/alerts/active', {
            headers: { 'Authorization': 'Bearer ' + token }
        });
        
        if (!response.ok) throw new Error('Failed to fetch alerts');
        const data = await response.json();
        
        container.innerHTML = '';
        if (data.length === 0) {
            container.innerHTML = '<div style="padding: 2rem; text-align: center; color: #888;">No active alerts. System is nominal.</div>';
            return;
        }
        
        data.forEach(alert => {
            const color = alert.alert_type === 'CRITICAL' ? '#ff4444' : '#ffaa00';
            const html = [
                '<div style="padding: 1.5rem; border: 1px solid rgba(255,255,255,0.1); border-radius: 8px; margin-bottom: 1rem; border-left: 4px solid ' + color + ';">',
                '  <div style="display: flex; justify-content: space-between; margin-bottom: 0.5rem;">',
                '    <strong style="color: ' + color + ';">' + alert.alert_type + ' ALERT</strong>',
                '    <span style="color: #888; font-size: 0.8rem;">' + new Date(alert.alert_time).toLocaleString() + '</span>',
                '  </div>',
                '  <div>' + alert.message + '</div>',
                '</div>'
            ].join('');
            container.innerHTML += html;
        });
        
    } catch (e) {
        console.error(e);
        if (container.innerHTML === '') {
            container.innerHTML = '<div style="padding: 2rem; text-align: center; color: #888;">Failed to load alerts from server.</div>';
        }
    }
}
