/**
 * DTCM Heatmap module - India Edition
 */

const SENSOR_LOCATIONS = {
    "Connaught Place, New Delhi": { lat: 28.6315, lng: 77.2167 },
    "Bandra Kurla Complex, Mumbai": { lat: 19.0596, lng: 72.8656 },
    "Electronic City, Bengaluru": { lat: 12.8452, lng: 77.6602 },
    "T. Nagar, Chennai": { lat: 13.0418, lng: 80.2341 },
    "Salt Lake Sector V, Kolkata": { lat: 22.5804, lng: 88.4332 }
};

let map = null;
let markers = [];

async function initHeatmap() {
    const mapElement = document.getElementById('map');
    if (!mapElement) return;

    if (!map) {
        // Center on India
        map = L.map('map').setView([20.5937, 78.9629], 5);
        
        // Dark theme tiles
        L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
            attribution: '&copy; OpenStreetMap contributors &copy; CARTO'
        }).addTo(map);
    }
    
    // Clear old markers
    markers.forEach(m => map.removeLayer(m));
    markers = [];

    try {
        const token = localStorage.getItem('dtcm_token');
        if (!token) return;

        const response = await fetch('http://127.0.0.1:5000/api/data/live', {
            headers: { 'Authorization': 'Bearer ' + token }
        });
        
        if (!response.ok) throw new Error('Failed to fetch live data for heatmap');
        const data = await response.json();
        
        data.forEach(sensor => {
            const coords = SENSOR_LOCATIONS[sensor.sensor_name];
            if (coords) {
                const isCritical = sensor.co2_level > 500;
                const color = isCritical ? '#ff4444' : (sensor.co2_level > 450 ? '#ffaa00' : '#00cc66');
                
                const circle = L.circle([coords.lat, coords.lng], {
                    color: color,
                    fillColor: color,
                    fillOpacity: 0.6,
                    radius: sensor.co2_level * 50 // Scale radius by CO2
                }).addTo(map);
                
                circle.bindPopup(`<b>${sensor.sensor_name}</b><br>CO₂ Level: ${sensor.co2_level.toFixed(1)} ppm<br>Status: ${sensor.severity_label}`);
                markers.push(circle);
            }
        });
        
    } catch (error) {
        console.error('Error updating heatmap:', error);
    }
}
