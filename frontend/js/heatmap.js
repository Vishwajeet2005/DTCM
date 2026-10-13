window.map = null;
let markers = [];

function initMap() {
    window.map = L.map('map').setView([40.7128, -74.0060], 12); // Default to NYC roughly
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; OpenStreetMap contributors'
    }).addTo(window.map);
}

function updateMap(data) {
    if (!window.map) initMap();
    
    // Clear old markers
    markers.forEach(m => window.map.removeLayer(m));
    markers = [];
    
    // Mock coordinates based on index since synthetic data doesn't have lat/lon
    const baseLat = 40.7128;
    const baseLon = -74.0060;
    
    data.forEach((d, i) => {
        const lat = baseLat + (i * 0.02);
        const lon = baseLon + (i * 0.02);
        
        let color = 'green';
        if (d.co2 > 500) color = 'red';
        else if (d.co2 > 450) color = 'orange';
        
        const marker = L.circleMarker([lat, lon], {
            color: color,
            radius: 10,
            fillOpacity: 0.7
        }).addTo(window.map)
        .bindPopup(`<b>${d.location}</b><br>CO₂: ${d.co2.toFixed(1)} ppm`);
        
        markers.push(marker);
    });
}
