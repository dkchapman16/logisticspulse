import os
import logging

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from werkzeug.middleware.proxy_fix import ProxyFix


# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class Base(DeclarativeBase):
    pass

# Initialize SQLAlchemy with the Base class
db = SQLAlchemy(model_class=Base)

# Create the Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET")
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)  # needed for url_for to generate with https

# Configure the database
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Initialize the database
db.init_app(app)

# Removed login manager - no authentication needed

# Set up API keys from environment
app.config["GOOGLE_MAPS_API_KEY"] = os.environ.get("GOOGLE_MAPS_API_KEY", "")
app.config["MOTIVE_API_KEY"] = os.environ.get("MOTIVE_API_KEY", "")

# Safe Mode configuration - disable API calls for testing
app.config["SAFE_MODE"] = os.environ.get("SAFE_MODE", "false").lower() == "true"

with app.app_context():
    # Import models
    import models  # noqa: F401
    
    # Removed user loader - no authentication needed
    
    # Create database tables
    db.create_all()
    
    # Register blueprints (removed auth blueprint)
    from routes.dashboard import dashboard_bp
    from routes.loads import loads_bp
    from routes.drivers import drivers_bp
    from routes.geofencing import geofencing_bp
    from routes.notifications import notifications_bp
    
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(loads_bp)
    app.register_blueprint(drivers_bp)
    app.register_blueprint(geofencing_bp)
    app.register_blueprint(notifications_bp)
    
    # Add root route redirect
    @app.route('/')
    def index():
        from flask import redirect, url_for
        return redirect(url_for('dashboard.index'))
    
    logger.info("Application initialized successfully")
