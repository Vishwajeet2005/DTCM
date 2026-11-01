import os
import sys
import subprocess
import time
import shutil

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
SCREENSHOTS_DIR = os.path.join(BASE_DIR, 'docs', 'screenshots')
os.makedirs(SCREENSHOTS_DIR, exist_ok=True)

CHROME_BIN = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
if not os.path.exists(CHROME_BIN):
    CHROME_BIN = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"

TEMP_DIR = os.path.join(os.environ.get('TEMP', 'C:\\Temp'), 'dtcm_shots')
os.makedirs(TEMP_DIR, exist_ok=True)

FEATURES = [
    {
        "name": "dashboard_main.png",
        "url": "http://localhost:5000/dashboard?tab=overview",
        "title": "Continuous CO2 Stream & Real-Time Edge Nodes"
    },
    {
        "name": "feature_city_modal.png",
        "url": "http://localhost:5000/dashboard?modal=city&sensor_id=1",
        "title": "Station Deep-Dive & Demographics Modal with 24h Trend"
    },
    {
        "name": "feature_geospatial_map.png",
        "url": "http://localhost:5000/dashboard?tab=gis-map",
        "title": "Geospatial Sensor Grid & Municipal Hotspots"
    },
    {
        "name": "feature_ai_forecasting.png",
        "url": "http://localhost:5000/dashboard?tab=predictions",
        "title": "Autoregressive Forecasting & Uncertainty Envelopes"
    },
    {
        "name": "feature_digital_twin_sandbox.png",
        "url": "http://localhost:5000/dashboard?tab=sandbox",
        "title": "Digital Twin Intervention Simulation & Abatement Curves"
    },
    {
        "name": "feature_capture_optimizer.png",
        "url": "http://localhost:5000/dashboard?tab=optimizer",
        "title": "Carbon Capture Prioritization Matrix & Green Infrastructure"
    },
    {
        "name": "feature_csv_ingestion_and_reports.png",
        "url": "http://localhost:5000/dashboard?tab=reports-hub",
        "title": "Compliance Center, Template Download & CSV Ingestion"
    },
    {
        "name": "landing_page.png",
        "url": "http://localhost:5000/",
        "title": "Public Climate Mission & Environmental Transparency Portal"
    },
    {
        "name": "login_portal.png",
        "url": "http://localhost:5000/login",
        "title": "Role-Based Access Control (RBAC) Authentication"
    }
]

def capture_features():
    print(f"Browser Binary: {CHROME_BIN}")
    print(f"Target Output Directory: {SCREENSHOTS_DIR}")
    success_count = 0

    for item in FEATURES:
        filename = item["name"]
        url = item["url"]
        title = item["title"]
        temp_file = os.path.join(TEMP_DIR, filename)
        final_file = os.path.join(SCREENSHOTS_DIR, filename)

        if os.path.exists(temp_file):
            os.remove(temp_file)

        print(f"\n[Capturing] {title} ({filename})...")
        cmd = [
            CHROME_BIN,
            "--headless=new",
            "--disable-gpu",
            "--no-sandbox",
            "--disable-background-networking",
            "--disable-sync",
            "--disable-default-apps",
            "--no-first-run",
            "--hide-scrollbars",
            "--window-size=1920,1080",
            f"--screenshot={temp_file}",
            url
        ]

        try:
            subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=25)
            # Give short moment for file flush
            time.sleep(1.0)
            if os.path.exists(temp_file) and os.path.getsize(temp_file) > 1000:
                shutil.copyfile(temp_file, final_file)
                print(f"  OK: {final_file} ({os.path.getsize(final_file)} bytes)")
                success_count += 1
            else:
                print(f"  FAILED: {filename} was not generated.")
        except Exception as e:
            print(f"  ERROR capturing {filename}: {e}")

    # Copy to artifacts directory
    artifact_dir = r"C:\Users\vishw\.gemini\antigravity\brain\94557eef-0bb6-4d8a-a6d8-71476c4c0bb2"
    if os.path.exists(artifact_dir):
        for item in FEATURES:
            src = os.path.join(SCREENSHOTS_DIR, item["name"])
            if os.path.exists(src):
                shutil.copyfile(src, os.path.join(artifact_dir, item["name"]))
        print("\nAll screenshots synchronized to artifacts directory.")

    print(f"\nCapture completed: {success_count}/{len(FEATURES)} screenshots captured successfully.")

if __name__ == '__main__':
    capture_features()
