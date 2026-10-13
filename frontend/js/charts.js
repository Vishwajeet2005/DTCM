let liveChart, historyChart, predChart;

function initCharts() {
    const liveCtx = document.getElementById('liveChart').getContext('2d');
    liveChart = new Chart(liveCtx, {
        type: 'line',
        data: {
            labels: [],
            datasets: [{
                label: 'Avg CO₂ (ppm)',
                data: [],
                borderColor: '#3498db',
                tension: 0.1
            }]
        }
    });
}

async function loadHistoryChart() {
    // Just mockup data for the chart layout
    const ctx = document.getElementById('historyChart').getContext('2d');
    if (historyChart) historyChart.destroy();
    
    historyChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: Array.from({length: 24}, (_, i) => `${i}:00`),
            datasets: [{
                label: 'Historical CO₂',
                data: Array.from({length: 24}, () => 400 + Math.random() * 50),
                borderColor: '#2ecc71',
                tension: 0.1
            }]
        }
    });
}

// Call init on load
window.addEventListener('load', () => {
    initCharts();
    loadHistoryChart();
});
