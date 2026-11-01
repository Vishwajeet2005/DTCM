import os
import subprocess
import time
import shutil

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
SCREENSHOTS_DIR = os.path.join(BASE_DIR, 'docs', 'screenshots')
os.makedirs(SCREENSHOTS_DIR, exist_ok=True)

CHROME_BIN = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
if not os.path.exists(CHROME_BIN):
    CHROME_BIN = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"

PAGES = [
    {
        "name": "dashboard_main.png",
        "url": "http://localhost:5000/dashboard",
        "desc": "Main Digital Twin Telemetry & Anomaly Dashboard"
    },
    {
        "name": "landing_page.png",
        "url": "http://localhost:5000/",
        "desc": "Public Environmental Monitoring & Mission Landing Page"
    },
    {
        "name": "login_portal.png",
        "url": "http://localhost:5000/login",
        "desc": "Role-Based RBAC Access Control Login Portal"
    }
]

def capture_all():
    print(f"Using browser binary: {CHROME_BIN}")
    print(f"Saving screenshots to: {SCREENSHOTS_DIR}")
    
    for page in PAGES:
        out_path = os.path.join(SCREENSHOTS_DIR, page["name"])
        print(f"\nCapturing {page['desc']} -> {page['name']}...")
        cmd = [
            CHROME_BIN,
            "--headless",
            "--disable-gpu",
            "--no-sandbox",
            "--disable-background-networking",
            "--disable-sync",
            "--disable-default-apps",
            "--no-first-run",
            "--hide-scrollbars",
            "--window-size=1920,1080",
            "--virtual-time-budget=6000",
            f"--screenshot={out_path}",
            page["url"]
        ]
        
        try:
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=20)
            if os.path.exists(out_path) and os.path.getsize(out_path) > 0:
                print(f"  Captured successfully: {out_path} ({os.path.getsize(out_path)} bytes)")
            else:
                print(f"  Warning: File not created. Error: {res.stderr}")
        except Exception as e:
            print(f"  Failed to capture {page['name']}: {e}")

if __name__ == '__main__':
    capture_all()
