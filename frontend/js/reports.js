function initReports() {
    const btnGen = document.getElementById('btn-generate-report');
    if (btnGen) {
        btnGen.addEventListener('click', async () => {
            const token = localStorage.getItem('dtcm_token');
            const start = document.getElementById('report-start').value;
            const end = document.getElementById('report-end').value;
            if(!start || !end) { alert('Please select dates'); return; }
            btnGen.textContent = 'Generating...';
            try {
                const res = await fetch('http://127.0.0.1:5000/api/reports/generate', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json', 'Authorization': 'Bearer ' + token },
                    body: JSON.stringify({ start_date: start, end_date: end, sensor_ids: [1,2,3,4,5], include_predictions: true, include_alerts: true })
                });
                if(!res.ok) throw new Error('Generation failed (Admin role required)');
                const data = await res.json();
                
                // Download
                const downloadRes = await fetch('http://127.0.0.1:5000/api/reports/' + data.report_id + '/download', {
                    headers: { 'Authorization': 'Bearer ' + token }
                });
                if(!downloadRes.ok) throw new Error('Download failed');
                const blob = await downloadRes.blob();
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = data.report_id + '.pdf';
                a.click();
                alert('Report downloaded successfully!');
            } catch(e) {
                alert(e.message);
            }
            btnGen.textContent = 'Generate & Download';
        });
    }

    const btnUpload = document.getElementById('btn-upload-csv');
    if (btnUpload) {
        btnUpload.addEventListener('click', async () => {
            const token = localStorage.getItem('dtcm_token');
            const fileInput = document.getElementById('csv-file-upload');
            if(!fileInput.files.length) { alert('Select a file'); return; }
            const formData = new FormData();
            formData.append('file', fileInput.files[0]);
            
            const statusEl = document.getElementById('upload-status');
            statusEl.textContent = 'Uploading...';
            statusEl.style.color = '#fff';
            
            try {
                const res = await fetch('http://127.0.0.1:5000/api/data/import/csv', {
                    method: 'POST',
                    headers: { 'Authorization': 'Bearer ' + token },
                    body: formData
                });
                const data = await res.json();
                if(!res.ok) throw new Error(data.error || 'Upload failed');
                statusEl.textContent = 'Success: Inserted ' + data.inserted + ' rows.';
                statusEl.style.color = '#00cc66';
            } catch(e) {
                statusEl.textContent = 'Error: ' + e.message;
                statusEl.style.color = '#ff4444';
            }
        });
    }
}
// Init immediately if called
initReports();
