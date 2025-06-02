import logging

logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s - %(message)s'
)

from app import app  # noqa: F401

if __name__ == "__main__":
    logging.info("Starting FreightPace application")
    app.run(host="0.0.0.0", port=5000, debug=True)
