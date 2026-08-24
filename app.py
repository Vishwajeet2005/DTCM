"""
Main application file for Digital Twin CO--- Monitor (DTCM).
Provides the Flask application factory.
"""
import time
import queue
import json
import logging
import threading
from typing import Dict, Any, Generator
from flask import Flask, request, jsonify, Response
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from flask_bcrypt import Bcrypt

# Assuming existence of these modules based on the project structure
from config import Config
from db.models import db
from api.auth import auth_bp
from api.data import data_bp
from api.predictions import predictions_bp
from api.twin import twin_bp
from api.alerts import alerts_bp
from api.reports import reports_bp
from ingestion.collector import DataCollector
from twin.engine import DigitalTwinEngine

# Global SSE subscribers queue list
sse_subscribers = []

def push_sse_event(event_type: str, data: Dict[str, Any]) -> None:
    """
    Push an SSE event to all connected subscribers.
    
    Args:
        event_type (str): The type of the event (e.g., 'alert', 'update').
        data (Dict[str, Any]): The JSON-serializable data payload.
    """
    message = f"event: {event_type}\ndata: {json.dumps(data)}\n\n"
    dead_subscribers = []
    
    # Iterate and send message to all active queues
    for subscriber in sse_subscribers:
        try:
            subscriber.put_nowait(message)
        except queue.Full:
            # If the queue is full, assume the subscriber is disconnected or stuck
            dead_subscribers.append(subscriber)
            
    # Clean up dead subscribers
    for subscriber in dead_subscribers:
        sse_subscribers.remove(subscriber)

def create_app(config_name: str = 'development') -> Flask:
    """
    Creates and configures the Flask application.
    
    Args:
        config_name (str): Configuration environment to use.
        
    Returns:
        Flask: The configured Flask application instance.
    """
    app = Flask(__name__, static_folder='frontend', static_url_path='/static')
    
    # Load configuration from config object
    app.config.from_object(Config)
    Config.configure_logging()
    
    # Enforce bcrypt cost factor of 12
    app.config['BCRYPT_LOG_ROUNDS'] = 12
    
    # Initialize SQLAlchemy, JWT, CORS, and Bcrypt extensions
    db.init_app(app)
    JWTManager(app)
    CORS(app)
    bcrypt = Bcrypt(app)
    
    # Register blueprints with appropriate prefixes
    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(data_bp, url_prefix='/api/data')
    app.register_blueprint(predictions_bp, url_prefix='/api')
    app.register_blueprint(twin_bp, url_prefix='/api/twin')
    app.register_blueprint(alerts_bp, url_prefix='/api/alerts')
    app.register_blueprint(reports_bp, url_prefix='/api/reports')
    
    logger = logging.getLogger(__name__)

    @app.before_request
    def before_request() -> None:
        """Middleware to record the start time of the request."""
        request.start_time = time.time()

    @app.after_request
    def after_request(response: Response) -> Response:
        """
        Middleware to log the method, path, status, and duration of the request.
        
        Args:
            response (Response): The Flask response object.
            
        Returns:
            Response: The unmodified Flask response object.
        """
        if hasattr(request, 'start_time'):
            duration = time.time() - request.start_time
            logger.info(
                f"Method: {request.method} Path: {request.path} "
                f"Status: {response.status_code} Duration: {duration:.4f}s"
            )
            
        # Ensure API responses are JSON except static assets and SSE
        if not request.path.startswith('/static') and not request.path == '/' and not request.path.endswith('download'):
            if response.content_type == 'text/html; charset=utf-8' and request.path != '/api/stream':
                response.content_type = 'application/json'
        return response

    @app.route('/')
    def index() -> Response:
        """Serve the frontend index.html."""
        return app.send_static_file('index.html')

    @app.route('/api/stream')
    def stream() -> Response:
        """
        Server-Sent Events (SSE) endpoint for real-time updates.
        
        Returns:
            Response: A streaming response with 'text/event-stream' content type.
        """
        def event_stream(subscriber_queue: queue.Queue) -> Generator[str, None, None]:
            """Generator function to yield events from the subscriber queue."""
            try:
                while True:
                    # Block until a message is available
                    message = subscriber_queue.get()
                    yield message
            except GeneratorExit:
                # Cleanup when client disconnects
                if subscriber_queue in sse_subscribers:
                    sse_subscribers.remove(subscriber_queue)

        # Create a new queue for this connection with a reasonable max size
        subscriber_queue = queue.Queue(maxsize=100)
        sse_subscribers.append(subscriber_queue)
        
        return Response(event_stream(subscriber_queue), mimetype="text/event-stream")

    # Start background threads for data collection and digital twin engine
    with app.app_context():
        try:
            collector = DataCollector()
            collector_thread = threading.Thread(target=collector.start, daemon=True)
            collector_thread.start()
            logger.info("DataCollector background thread started.")
        except Exception as e:
            logger.error(f"Failed to start DataCollector: {e}")

        try:
            twin_engine = DigitalTwinEngine()
            twin_thread = threading.Thread(target=twin_engine.start, daemon=True)
            twin_thread.start()
            logger.info("DigitalTwinEngine background thread started.")
        except Exception as e:
            logger.error(f"Failed to start DigitalTwinEngine: {e}")

    return app

if __name__ == '__main__':
    dtcm_app = create_app()
    dtcm_app.run(debug=True, port=5000)

