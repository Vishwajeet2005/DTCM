async function runSimulation() {
    const traffic = document.getElementById('sim-traffic').value;
    const green = document.getElementById('sim-green').value;
    
    try {
        const res = await fetch(`${API_BASE}/twin/simulate`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                traffic_reduction_pct: parseFloat(traffic),
                green_area_increase_km2: parseFloat(green),
                duration_hours: 24,
                scenario_name: 'Frontend Sim'
            })
        });
        const data = await res.json();
        
        document.getElementById('sim-results').innerHTML = `
            <h3>Simulation Results</h3>
            <p>Baseline CO₂: ${data.baseline_co2} ppm</p>
            <p>Projected CO₂: ${data.projected_co2} ppm</p>
            <p>Reduction: ${data.reduction_pct}%</p>
        `;
    } catch (e) {
        console.error('Simulation error', e);
    }
}

async function runPrediction() {
    const sensorId = document.getElementById('pred-sensor').value;
    if (!sensorId) return;
    
    if (!token) {
        const loginRes = await fetch(`${API_BASE}/auth/login`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({email: 'admin@dtcm.com', password: 'admin123'})
        });
        if (loginRes.ok) {
            const lData = await loginRes.json();
            token = lData.access_token;
        }
    }
    
    try {
        const res = await fetch(`${API_BASE}/predict/short-term`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify({sensor_id: parseInt(sensorId)})
        });
        const data = await res.json();
        
        if (data.predictions) {
            const ctx = document.getElementById('predChart').getContext('2d');
            if (predChart) predChart.destroy();
            
            predChart = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: Array.from({length: data.predictions.length}, (_, i) => `+${i}h`),
                    datasets: [{
                        label: 'Predicted CO₂',
                        data: data.predictions,
                        borderColor: '#9b59b6',
                        fill: false
                    },
                    {
                        label: 'Confidence High',
                        data: data.confidence_high,
                        borderColor: 'rgba(155, 89, 182, 0.2)',
                        backgroundColor: 'rgba(155, 89, 182, 0.2)',
                        fill: '+1'
                    },
                    {
                        label: 'Confidence Low',
                        data: data.confidence_low,
                        borderColor: 'rgba(155, 89, 182, 0.2)',
                        fill: false
                    }]
                }
            });
        }
    } catch (e) {
        console.error('Prediction error', e);
    }
}
