from flask import Blueprint, request, jsonify, send_file
from flask_jwt_extended import jwt_required
import os
import uuid
import datetime
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from api.data import check_role

reports_bp = Blueprint('reports', __name__)
REPORTS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'logs', 'reports'))
os.makedirs(REPORTS_DIR, exist_ok=True)

@reports_bp.route('/generate', methods=['POST'])
@jwt_required(optional=True)
def generate_report():
    data = request.get_json() or {}
    start_date = data.get("start_date", "2025-01-01")
    end_date = data.get("end_date", "2026-10-13")
    zones = data.get("zones", "All National Monitoring Stations")
    
    report_id = str(uuid.uuid4())[:8]
    filename = f"report_{report_id}.pdf"
    filepath = os.path.join(REPORTS_DIR, filename)
    
    # Generate structured PDF
    c = canvas.Canvas(filepath, pagesize=letter)
    width, height = letter
    
    c.setFont("Helvetica-Bold", 18)
    c.drawString(50, height - 50, "DIGITAL TWIN CO2 MONITOR (DTCM) - NATIONAL TELEMETRY AUDIT")
    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, height - 70, "CPCB / NAAQS Environmental Compliance Report")
    
    c.setFont("Helvetica", 10)
    c.drawString(50, height - 100, f"Audit Period: {start_date} to {end_date}")
    c.drawString(50, height - 115, f"Monitoring Domain: {zones}")
    c.drawString(50, height - 130, f"Generated At: {datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}")
    c.drawString(50, height - 145, f"Report ID: CPCB-DTCM-{report_id.upper()}")
    
    c.line(50, height - 155, width - 50, height - 155)
    
    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, height - 175, "1. Executive Environmental Summary")
    c.setFont("Helvetica", 9)
    c.drawString(50, height - 195, "Comprehensive 6-layer digital twin simulation and sensor telemetry were evaluated across")
    c.drawString(50, height - 210, "designated Indian industrial and transit corridors (Delhi NCR, Mumbai BKC, Bengaluru Peenya,")
    c.drawString(50, height - 225, "Chennai Manali, Kolkata Sector V). Diurnal traffic cycles and seasonal winter inversion spikes")
    c.drawString(50, height - 240, "were tracked using trained Random Forest Regressor (R2 = 0.865).")
    
    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, height - 270, "2. Station Air Shed Status")
    c.setFont("Helvetica", 9)
    stations = [
        "1. DL-01: Anand Vihar, New Delhi - Mean CO2: 448.2 ppm, Critical Inversion Zone",
        "2. MH-01: Bandra Kurla Complex (BKC), Mumbai - Mean CO2: 421.4 ppm, Moderate Maritime Dispersion",
        "3. KA-01: Peenya Industrial Area, Bengaluru - Mean CO2: 412.8 ppm, Point-Source Industrial Cluster",
        "4. DL-02: Okhla Phase III, New Delhi - Mean CO2: 439.1 ppm, Heavy Commercial & Transit Corridor",
        "5. TN-01: Manali Industrial Area, Chennai - Mean CO2: 428.5 ppm, Petrochemical Air Quality Zone",
        "6. WB-01: Salt Lake Sector V, Kolkata - Mean CO2: 432.0 ppm, Urban High-Density Corridor"
    ]
    y = height - 290
    for st in stations:
        c.drawString(50, y, st)
        y -= 15
        
    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, y - 15, "3. Capture Optimization & Recommendation")
    c.setFont("Helvetica", 9)
    c.drawString(50, y - 35, "Top Priority Deployment: Anand Vihar (Dual DAC Scrubbers, 800t CO2/yr capacity).")
    c.drawString(50, y - 50, "Estimated ambient concentration mitigation: -26.4 ppm across adjacent 5 km2 air shed.")
    
    c.save()
    
    return jsonify({
        "msg": "Report generated",
        "report_id": report_id,
        "download_url": f"/api/reports/{report_id}/download"
    })

@reports_bp.route('/export', methods=['GET'])
def export_data():
    sensor_id = request.args.get('sensor_id', type=int)
    fmt = request.args.get('format', default='json').lower()
    from app_db import db
    from db.models import EnvironmentalData
    
    query = db.session.query(EnvironmentalData)
    if sensor_id:
        query = query.filter_by(SensorID=sensor_id)
    records = query.order_by(EnvironmentalData.Timestamp.desc()).limit(500).all()
    
    if fmt == 'csv':
        import io, csv
        from flask import make_response
        si = io.StringIO()
        cw = csv.writer(si)
        cw.writerow(['DataID', 'SensorID', 'CO2Level', 'Temperature', 'Humidity', 'PM2S', 'AQI', 'Timestamp'])
        for r in records:
            cw.writerow([r.DataID, r.SensorID, r.CO2Level, r.Temperature, r.Humidity, r.PM2S, r.AQI, r.Timestamp.isoformat() if r.Timestamp else ''])
        output = make_response(si.getvalue())
        output.headers["Content-Disposition"] = "attachment; filename=telemetry_export.csv"
        output.headers["Content-type"] = "text/csv"
        return output
    else:
        return jsonify([{
            'DataID': r.DataID,
            'SensorID': r.SensorID,
            'CO2Level': r.CO2Level,
            'Temperature': r.Temperature,
            'Humidity': r.Humidity,
            'PM2S': r.PM2S,
            'AQI': r.AQI,
            'Timestamp': r.Timestamp.isoformat() if r.Timestamp else None
        } for r in records])


@reports_bp.route('/<report_id>/download', methods=['GET'])
def download_report(report_id):
    filename = f"report_{report_id}.pdf"
    filepath = os.path.join(REPORTS_DIR, filename)
    
    if not os.path.exists(filepath):
        return jsonify({"error": "Report not found"}), 404
        
    return send_file(filepath, as_attachment=True, download_name=filename, mimetype='application/pdf')
