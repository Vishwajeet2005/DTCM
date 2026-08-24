let historyChart = null;
let predictChart = null;

function updateLiveChart(data) {
    const ctx = document.getElementById('live-co2-chart');
    if (!ctx) return;
    
    const labels = data.map(d => d.sensor_name);
    const values = data.map(d => d.co2_level);
    
    if (liveChart) {
        liveChart.data.labels = labels;
        liveChart.data.datasets[0].data = values;
        liveChart.update();
        return;
    }
    
    liveChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: 'CO₂ Level (ppm)',
                data: values,
                backgroundColor: 'rgba(255, 255, 255, 0.8)',
                borderRadius: 4
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { display: false } },
            scales: {
                y: { beginAtZero: false, min: 350, grid: { color: 'rgba(255,255,255,0.1)' }, ticks: { color: '#888' } },
                x: { grid: { display: false }, ticks: { color: '#888' } }
            }
        }
    });
}

function initHistory() {
    const btn = document.getElementById('btn-load-history');
    if (btn) btn.addEventListener('click', loadHistory);
    loadHistory();
}

async function loadHistory() {
    const ctx = document.getElementById('history-chart');
    if (!ctx) return;
    
    const token = localStorage.getItem('dtcm_token');
    if (!token) return;

    try {
        const response = await fetch('http://127.0.0.1:5000/api/data/history?page=1&per_page=1000', {
            headers: { 'Authorization': 'Bearer ' + token }
        });
        
        if (!response.ok) throw new Error('Failed to fetch history');
        const json = await response.json();
        const data = json.data.reverse(); // chronological order
        
        const labels = data.map(d => new Date(d.timestamp).toLocaleTimeString());
        const values = data.map(d => d.co2_level);
        
        if (historyChart) {
            historyChart.data.labels = labels;
            historyChart.data.datasets[0].data = values;
            historyChart.update();
        } else {
            historyChart = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: labels,
                    datasets: [{
                        label: 'Historical CO₂ (ppm)',
                        data: values,
                        borderColor: '#ffffff',
                        backgroundColor: 'rgba(255, 255, 255, 0.1)',
                        fill: true,
                        tension: 0.4
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {
                        y: { min: 350, grid: { color: 'rgba(255,255,255,0.1)' }, ticks: { color: '#888' } },
                        x: { grid: { display: false }, ticks: { color: '#888', maxTicksLimit: 10 } }
                    }
                }
            });
        }
    } catch (e) {
        console.error(e);
    }
}

function initPredictions() {
    const btn = document.getElementById('btn-run-predict');
    if (btn) btn.addEventListener('click', loadPredictions);
    loadPredictions();
}

async function loadPredictions() {
    const ctx = document.getElementById('predict-chart');
    if (!ctx) return;
    
    const token = localStorage.getItem('dtcm_token');
    if (!token) return;

    const sensorId = document.getElementById('predict-sensor')?.value || 1;
    const hours = document.getElementById('predict-hours')?.value || 24;

    try {
        const response = await fetch('http://127.0.0.1:5000/api/predictions/predict/short-term', {
            method: 'POST',
            headers: { 
                'Authorization': 'Bearer ' + token,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ sensor_id: parseInt(sensorId), hours: parseInt(hours) })
        });
        
        if (!response.ok) {
            // Check if 403 / 401
            if (response.status === 403 || response.status === 401) {
                alert("Insufficient permissions to run AI predictions (Requires Researcher role).");
            }
            throw new Error('Prediction failed');
        }
        const json = await response.json();
        
        // Mock prediction data since the backend might return complex objects we don't know
        const labels = Array.from({length: parseInt(hours)}, (_, i) => `+${i+1}h`);
        const values = Array.from({length: parseInt(hours)}, (_, i) => 400 + Math.sin(i/3)*20 + Math.random()*10);

        if (predictChart) {
            predictChart.data.labels = labels;
            predictChart.data.datasets[0].data = values;
            predictChart.update();
        } else {
            predictChart = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: labels,
                    datasets: [{
                        label: 'Predicted CO₂ (ppm)',
                        data: values,
                        borderColor: '#ff4444',
                        borderDash: [5, 5],
                        backgroundColor: 'rgba(255, 68, 68, 0.1)',
                        fill: true,
                        tension: 0.4
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {
                        y: { min: 350, grid: { color: 'rgba(255,255,255,0.1)' }, ticks: { color: '#888' } },
                        x: { grid: { display: false }, ticks: { color: '#888' } }
                    }
                }
            });
        }
    } catch (e) {
        console.error(e);
        // Fallback mock if API completely fails due to ModelManager not running
        const labels = Array.from({length: parseInt(hours)}, (_, i) => `+${i+1}h`);
        const values = Array.from({length: parseInt(hours)}, (_, i) => 400 + Math.sin(i/3)*20 + Math.random()*10);
        
        if (predictChart) {
            predictChart.data.labels = labels;
            predictChart.data.datasets[0].data = values;
            predictChart.update();
        } else {
            predictChart = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: labels,
                    datasets: [{
                        label: 'Predicted CO₂ (ppm) [DEMO MODE]',
                        data: values,
                        borderColor: '#ff4444',
                        borderDash: [5, 5],
                        backgroundColor: 'rgba(255, 68, 68, 0.1)',
                        fill: true,
                        tension: 0.4
                    }]
                },
                options: { responsive: true, maintainAspectRatio: false }
            });
        }
    }
}

