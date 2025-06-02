import logging
from services.logger import setup_logger

# Set up main application logger
app_logger = setup_logger('freightpace.main')

from app import app  # noqa: F401

if __name__ == "__main__":
    app_logger.info("Starting FreightPace application server")
    app.run(host="0.0.0.0", port=5000, debug=True)
