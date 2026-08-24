"""
Reports API Blueprint for DTCM.
Provides routes for generating and downloading PDF reports using ReportLab.
"""
import os
import uuid
from typing import Tuple, Union
from datetime import datetime
from flask import Blueprint, jsonify, send_file, Response
from flask_jwt_extended import jwt_required, get_jwt_identity
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from db.models import db, User

reports_bp = Blueprint('reports_bp', __name__)

# Ensure the reports directory exists for saving generated PDFs
REPORTS_DIR = os.path.join(os.path.dirname(__file__), '..', 'reports')
os.makedirs(REPORTS_DIR, exist_ok=True)

def role_at_least(required_role: str):
    """
    Decorator to enforce role-based access control.
    """
    def decorator(f):
        from functools import wraps
        @wraps(f)
        def decorated_function(*args, **kwargs) -> Tuple[Response, int]:
            current_user_id = get_jwt_identity()
            user = User.query.get(current_user_id)
            if not user:
                return jsonify({"error": "User not found"}), 404
            
            roles = ['general', 'researcher', 'administrator', 'environmental_authority']
            try:
                user_rank = roles.index(user.role)
                required_rank = roles.index(required_role)
            except ValueError:
                return jsonify({"error": "Invalid role configured"}), 500
                
            if user_rank < required_rank:
                return jsonify({"error": "Insufficient privileges"}), 403
            return f(*args, **kwargs)
        return decorated_function
    return decorator

@reports_bp.route('/generate', methods=['POST'])
@jwt_required()
@role_at_least('administrator')
def generate_report() -> Tuple[Response, int]:
    """
    Generate a new PDF report of the system's status.
    
    Returns:
        JSON response with report details and download URL.
    """
    report_id = str(uuid.uuid4())
    filename = f"report_{report_id}.pdf"
    filepath = os.path.join(REPORTS_DIR, filename)
    
    try:
        # Create a PDF document using ReportLab
        c = canvas.Canvas(filepath, pagesize=letter)
        c.setFont("Helvetica-Bold", 16)
        c.drawString(100, 750, "Digital Twin CO2 Monitor (DTCM) System Report")
        
        c.setFont("Helvetica", 12)
        c.drawString(100, 730, f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        c.drawString(100, 710, f"Report ID: {report_id}")
        
        c.drawString(100, 680, "System Summary:")
        c.drawString(120, 660, "- Overview of recent environmental data")
        c.drawString(120, 640, "- Active Alert and recent acknowledgments")
        c.drawString(120, 620, "- Simulation and prediction summaries")
        
        # Save the constructed PDF to the filesystem
        c.save()
        
        return jsonify({
            "message": "Report generated successfully.",
            "report_id": report_id,
            "download_url": f"/api/reports/{report_id}/download"
        }), 201
        
    except Exception as e:
        return jsonify({"error": f"Failed to generate report: {str(e)}"}), 500

@reports_bp.route('/<report_id>/download', methods=['GET'])
@jwt_required()
@role_at_least('administrator')
def download_report(report_id: str) -> Union[Response, Tuple[Response, int]]:
    """
    Download a previously generated PDF report.
    
    Args:
        report_id (str): The UUID of the report to download.
        
    Returns:
        Response: The generated PDF file as an attachment or an error JSON response.
    """
    filename = f"report_{report_id}.pdf"
    filepath = os.path.join(REPORTS_DIR, filename)
    
    if not os.path.exists(filepath):
        return jsonify({"error": "Report not found"}), 404
        
    # Return the PDF file as a downloadable attachment
    return send_file(
        filepath,
        as_attachment=True,
        download_name=filename,
        mimetype='application/pdf'
    )


