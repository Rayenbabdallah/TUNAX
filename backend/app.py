"""
Main Flask Application
Tunisian Municipal Tax Management System
Based on Code de la Fiscalité Locale 2025
"""
import os
import logging
from logging.handlers import RotatingFileHandler
import secrets
from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from flask_migrate import Migrate
from flask_limiter.util import get_remote_address
from datetime import timedelta
from werkzeug.exceptions import HTTPException
from sqlalchemy.exc import SQLAlchemyError

from extensions.db import db
from extensions.jwt import jwt, is_token_blacklisted
from extensions.api import api
from extensions.limiter import limiter

def create_app(config_name='development'):
    """Application factory"""
    app = Flask(__name__)
    
    # Configuration
    # Default to SQLite database in backend directory
    default_db_path = os.path.join(os.path.dirname(__file__), 'tunax.db')
    default_db_uri = f'sqlite:///{default_db_path}'
    
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv(
        'DATABASE_URL',
        default_db_uri
    )
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    # JWT Configuration - Use environment variable, warn if using default
    jwt_secret = os.getenv('JWT_SECRET_KEY')
    if not jwt_secret:
        jwt_secret = secrets.token_urlsafe(64)
        app.logger.warning('⚠️  JWT_SECRET_KEY not set in environment. Using random key. SET THIS IN PRODUCTION!')
    app.config['JWT_SECRET_KEY'] = jwt_secret
    app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(hours=1)
    app.config['JWT_REFRESH_TOKEN_EXPIRES'] = timedelta(days=30)
    
    # Rate Limiting Configuration (use persistent Redis in production)
    # Flask-Limiter expects RATELIMIT_STORAGE_URI
    app.config['RATELIMIT_STORAGE_URI'] = os.getenv('REDIS_URL', 'memory://')
    app.config['RATELIMIT_STRATEGY'] = 'fixed-window'
    
    # API Documentation
    app.config['API_TITLE'] = 'Tunisian Municipal Tax Management System'
    app.config['API_VERSION'] = 'v1'
    app.config['OPENAPI_VERSION'] = '3.0.2'
    app.config['OPENAPI_URL_PREFIX'] = '/api/v1/docs'
    # Enable Swagger UI under the docs prefix
    app.config['OPENAPI_SWAGGER_UI_PATH'] = 'swagger-ui'
    app.config['OPENAPI_SWAGGER_UI_URL'] = 'https://unpkg.com/swagger-ui-dist/'
    
    # Enable CORS with origin restrictions (avoid wildcard in production)
    cors_origins = os.getenv('CORS_ORIGINS', 'http://localhost:3000,http://localhost').split(',')
    CORS(app, origins=cors_origins, allow_headers=['Content-Type', 'Authorization'])
    
    # Initialize extensions
    db.init_app(app)
    jwt.init_app(app)
    api.init_app(app)
    
    # Initialize Flask-Migrate
    migrate = Migrate(app, db, directory='migrations')
    
    # Initialize shared rate limiter
    # Uses defaults from extensions/limiter.py; storage defaults to memory
    # Configure via RATELIMIT_STORAGE_URI if using Redis in production
    limiter.init_app(app)
    
    # JWT callbacks
    @jwt.token_in_blocklist_loader
    def check_if_token_revoked(jwt_header, jwt_payload):
        jti = jwt_payload['jti']
        return is_token_blacklisted(jti)
    
    # Health check endpoint for Docker container health monitoring
    @app.route('/health', methods=['GET'])
    def health_check():
        """Health check endpoint for Docker/Kubernetes liveness probes.
    
        Returns 200 if backend is responsive and database is accessible.
        Returns 503 if database connection fails.
        """
        try:
            # Quick database connectivity check
            db.session.execute(db.text('SELECT 1'))
            return jsonify({
                'status': 'healthy',
                'service': 'TUNAX Backend',
                'version': 'v2.0.0'
            }), 200
        except Exception as e:
            app.logger.error(f'Health check failed: {e}')
            return jsonify({
                'status': 'unhealthy',
                'error': 'Database connection failed',
                'details': str(e)
            }), 503
    
    # Register blueprints via flask-smorest Api
    from resources.auth import blp as auth_blp
    api.register_blueprint(auth_blp)

    # Ministry and Municipal Admin blueprints (new two-tier architecture)
    try:
        from resources.ministry import ministry_bp as ministry_bp
        api.register_blueprint(ministry_bp)
    except Exception as e:
        app.logger.warning(f"Skipping Ministry module registration: {e}")

    try:
        from resources.municipal import municipal_bp as municipal_bp
        api.register_blueprint(municipal_bp)
    except Exception as e:
        app.logger.warning(f"Skipping Municipal module registration: {e}")

    # Best-effort registration of remaining modules to avoid startup failures
    try:
        from resources.tib import blp as tib_blp
        api.register_blueprint(tib_blp)
    except Exception as e:
        app.logger.warning(f"Skipping TIB module registration: {e}")

    try:
        from resources.ttnb import blp as ttnb_blp
        api.register_blueprint(ttnb_blp)
    except Exception as e:
        app.logger.warning(f"Skipping TTNB module registration: {e}")

    try:
        from resources.payment import blp as payment_blp
        api.register_blueprint(payment_blp)
    except Exception as e:
        app.logger.warning(f"Skipping Payment module registration: {e}")

    try:
        from resources.permits import blp as permits_blp
        api.register_blueprint(permits_blp)
    except Exception as e:
        app.logger.warning(f"Skipping Permits module registration: {e}")

    try:
        from resources.reclamations import blp as reclamations_blp
        api.register_blueprint(reclamations_blp)
    except Exception as e:
        app.logger.warning(f"Skipping Reclamations module registration: {e}")

    try:
        from resources.agent import blp as agent_blp
        api.register_blueprint(agent_blp)
    except Exception as e:
        app.logger.warning(f"Skipping Agent module registration: {e}")

    try:
        from resources.dispute import blp as dispute_blp
        api.register_blueprint(dispute_blp)
    except Exception as e:
        app.logger.warning(f"Skipping Dispute module registration: {e}")

    try:
        from resources.public import blp as public_blp
        api.register_blueprint(public_blp)
    except Exception as e:
        app.logger.warning(f"Skipping Public module registration: {e}")

    try:
        from resources.external_integrations import blp as external_integrations_blp
        api.register_blueprint(external_integrations_blp)
    except Exception as e:
        app.logger.warning(f"Skipping External Integrations module registration: {e}")

    try:
        from resources.exemptions import exemptions_bp
        api.register_blueprint(exemptions_bp)
    except Exception as e:
        app.logger.warning(f"Skipping Exemptions module registration: {e}")

    try:
        from resources.payment_plans import payment_plans_bp
        api.register_blueprint(payment_plans_bp)
    except Exception as e:
        app.logger.warning(f"Skipping Payment Plans module registration: {e}")

    try:
        from resources.audit import audit_bp
        api.register_blueprint(audit_bp)
    except Exception as e:
        app.logger.warning(f"Skipping Audit module registration: {e}")

    try:
        from resources.reports import blp as reports_blp, admin_bulk_bp
        api.register_blueprint(reports_blp)
        api.register_blueprint(admin_bulk_bp)
    except Exception as e:
        app.logger.warning(f"Skipping Reports module registration: {e}")

    try:
        from resources.documents import documents_bp
        api.register_blueprint(documents_bp)
    except Exception as e:
        app.logger.warning(f"Skipping Documents module registration: {e}")

    # Flask-smorest blueprints (converted)
    try:
        from resources.admin import blp as admin_blp
        api.register_blueprint(admin_blp)
    except Exception as e:
        app.logger.warning(f"Skipping Admin module registration: {e}")
    
    try:
        from resources.inspector import blp as inspector_blp
        api.register_blueprint(inspector_blp)
    except Exception as e:
        app.logger.warning(f"Skipping Inspector module registration: {e}")
    
    try:
        from resources.amendments import blp as amendments_blp
        api.register_blueprint(amendments_blp)
    except Exception as e:
        app.logger.warning(f"Skipping Amendments module registration: {e}")
    
    try:
        from resources.search import blp as search_blp
        api.register_blueprint(search_blp)
    except Exception as e:
        app.logger.warning(f"Skipping Search module registration: {e}")
    
    try:
        from resources.test_cadastral import test_bp
        app.register_blueprint(test_bp)
    except Exception as e:
        app.logger.warning(f"Skipping test_cadastral module registration: {e}")
    
    try:
        from resources.two_factor import blp as two_factor_blp
        api.register_blueprint(two_factor_blp)
    except Exception as e:
        app.logger.warning(f"Skipping Two-Factor module registration: {e}")
    
    try:
        from resources.renewal import blp as renewal_blp
        api.register_blueprint(renewal_blp)
    except Exception as e:
        app.logger.warning(f"Skipping Renewal module registration: {e}")

    # Legacy blueprints (standard Flask blueprints, not flask-smorest)
    for mod_name, bp_name in [
        ("resources.finance", "finance_bp"),
        ("resources.budget_voting", "budget_bp"),
        ("resources.dashboard", "dashboard_bp"),
        ("resources.document_types", "document_types_bp"),
        ("resources.notifications", "notifications_bp"),
    ]:
        try:
            mod = __import__(mod_name, fromlist=[bp_name])
            app.register_blueprint(getattr(mod, bp_name))
        except Exception as e:
            app.logger.warning(f"Skipping {mod_name} registration: {e}")
    
    # Global Error Handlers with Logging
    @app.errorhandler(400)
    def bad_request(error):
        app.logger.warning(f'Bad Request: {error} - {request.url}')
        return jsonify({
            'error': 'Bad Request',
            'message': str(error) if app.debug else 'Invalid request parameters'
        }), 400
    
    @app.errorhandler(401)
    def unauthorized(error):
        app.logger.warning(f'Unauthorized access attempt: {request.url} from {get_remote_address()}')
        return jsonify({'error': 'Unauthorized', 'message': 'Authentication required'}), 401
    
    @app.errorhandler(403)
    def forbidden(error):
        app.logger.warning(f'Forbidden access: {request.url} from {get_remote_address()}')
        return jsonify({'error': 'Forbidden', 'message': 'Insufficient permissions'}), 403
    
    @app.errorhandler(404)
    def not_found(error):
        return jsonify({'error': 'Not found', 'message': 'Resource not found'}), 404
    
    @app.errorhandler(429)
    def ratelimit_handler(error):
        app.logger.warning(f'Rate limit exceeded: {request.url} from {get_remote_address()}')
        return jsonify({'error': 'Too Many Requests', 'message': 'Rate limit exceeded. Please try again later.'}), 429
    
    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        app.logger.error(f'Internal Server Error: {error}', exc_info=True)
        return jsonify({
            'error': 'Internal server error',
            'message': str(error) if app.debug else 'An unexpected error occurred'
        }), 500
    
    @app.errorhandler(SQLAlchemyError)
    def handle_db_error(error):
        db.session.rollback()
        app.logger.error(f'Database Error: {error}', exc_info=True)
        return jsonify({
            'error': 'Database error',
            'message': 'A database error occurred'
        }), 500
    
    @app.errorhandler(HTTPException)
    def handle_http_exception(error):
        app.logger.warning(f'HTTP Exception: {error.code} - {error.description}')
        return jsonify({
            'error': error.name,
            'message': error.description
        }), error.code
    
    @app.errorhandler(Exception)
    def handle_unexpected_error(error):
        db.session.rollback()
        app.logger.critical(f'Unexpected Error: {error}', exc_info=True)
        return jsonify({
            'error': 'Unexpected error',
            'message': 'An unexpected error occurred'
        }), 500
    
    # Logging Configuration
    if not app.debug:
        # Create logs directory if it doesn't exist
        logs_dir = os.path.join(os.path.dirname(__file__), 'logs')
        os.makedirs(logs_dir, exist_ok=True)
        
        # File handler for errors
        error_handler = RotatingFileHandler(
            os.path.join(logs_dir, 'tunax_error.log'),
            maxBytes=10485760,  # 10MB
            backupCount=10
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
        ))
        
        # File handler for general logs
        info_handler = RotatingFileHandler(
            os.path.join(logs_dir, 'tunax_info.log'),
            maxBytes=10485760,  # 10MB
            backupCount=10
        )
        info_handler.setLevel(logging.INFO)
        info_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s'
        ))
        
        app.logger.addHandler(error_handler)
        app.logger.addHandler(info_handler)
        app.logger.setLevel(logging.INFO)
        app.logger.info('TUNAX application startup')
    
    # Database initialization (migrations should be run separately with alembic)
    # Uncomment the following block if you need auto-migrations on app startup
    # with app.app_context():
    #     try:
    #         migrations_dir = os.path.join(os.path.dirname(__file__), 'migrations')
    #         versions_dir = os.path.join(migrations_dir, 'versions')
    #         os.makedirs(versions_dir, exist_ok=True)
    #         alembic_cfg = AlembicConfig(os.path.join(migrations_dir, 'alembic.ini'))
    #         import models  # noqa: F401
    #         if not any(name.endswith('.py') for name in os.listdir(versions_dir)):
    #             alembic_command.revision(alembic_cfg, message="initial", autogenerate=True)
    #         alembic_command.upgrade(alembic_cfg, 'head')
    #     except Exception:
    #         db.create_all()
    
    return app

if __name__ == '__main__':
    app = create_app()
    app.run(debug=False, host='0.0.0.0', port=5000)
