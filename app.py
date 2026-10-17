from flask import Flask, jsonify
from flask_jwt_extended import JWTManager
from flask_cors import CORS
from config import config
from app_db import db

def create_app(config_class=None):
    app = Flask(__name__, static_folder='frontend', static_url_path='')
    CORS(app)
    
    if config_class:
        app.config.from_object(config_class)
    else:
        app.config['SQLALCHEMY_DATABASE_URI'] = config.SQLALCHEMY_DATABASE_URI
        app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = config.SQLALCHEMY_TRACK_MODIFICATIONS
        app.config['JWT_SECRET_KEY'] = config.JWT_SECRET_KEY
        app.config['JWT_ACCESS_TOKEN_EXPIRES'] = config.JWT_ACCESS_TOKEN_EXPIRES
    
    db.init_app(app)
    jwt = JWTManager(app)
    
    # Register blueprints
    from api.auth import auth_bp
    from api.data import data_bp
    from api.predictions import predictions_bp
    from api.twin import twin_bp
    from api.alerts import alerts_bp
    from api.reports import reports_bp
    
    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(data_bp, url_prefix='/api/data')
    app.register_blueprint(predictions_bp, url_prefix='/api/predict')
    app.register_blueprint(twin_bp, url_prefix='/api/twin')
    app.register_blueprint(alerts_bp, url_prefix='/api/alerts')
    app.register_blueprint(reports_bp, url_prefix='/api/reports')
    app.register_blueprint(reports_bp, url_prefix='/api/report', name='report_singular_bp')

    @app.route('/api/classify/zones', methods=['GET', 'POST'])
    def root_classify_zones():
        from api.predictions import classify_zones
        return classify_zones()

    @app.route('/api/import/csv', methods=['POST'])
    def root_import_csv():
        from api.data import import_csv
        return import_csv()

    @app.route('/')
    def index():
        return app.send_static_file('landing.html')

    @app.route('/landing')
    def landing():
        return app.send_static_file('landing.html')

    @app.route('/login')
    @app.route('/auth')
    def login_page():
        return app.send_static_file('login.html')

    @app.route('/dashboard')
    @app.route('/app')
    def dashboard_page():
        return app.send_static_file('index.html')

    @app.route('/favicon.ico')
    def favicon():
        return ('', 204)
        
    # Start digital twin sync thread if not testing
    if not app.config.get('TESTING', False):
        try:
            from twin.engine import twin_engine
            twin_engine.sync_state()
            twin_engine.start_sync_cycle()
        except Exception as e:
            app.logger.warning(f"Could not start twin engine sync cycle: {e}")
            
    return app

app = create_app()

if __name__ == '__main__':
    with app.app_context():
        # Ensure tables exist
        from db.models import Base, Users, SensorData
        import bcrypt
        Base.metadata.create_all(db.engine)
        
        # Seed standard demo accounts if absent
        seed_users = [
            ("Admin User", "admin@dtcm.com", "administrator", "admin123"),
            ("Authority Lead", "authority@dtcm.com", "environmental_authority", "authority123"),
            ("Dr. Researcher", "researcher@dtcm.com", "researcher", "researcher123"),
            ("Urban Citizen", "citizen@dtcm.com", "general", "citizen123"),
        ]
        for name, email, role, pwd in seed_users:
            if not db.session.query(Users).filter_by(Email=email).first():
                hashed = bcrypt.hashpw(pwd.encode('utf-8'), bcrypt.gensalt(12)).decode('utf-8')
                user_obj = Users(Email=email, PasswordHash=hashed, Role=role, Name=name)
                db.session.add(user_obj)
        db.session.commit()
    app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False)
