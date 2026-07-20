import logging
import os

def setup_logging(level=logging.INFO):
    """
    Setup logging configurations for HSTS.
    """
    os.makedirs("logs", exist_ok=True)
    
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler("logs/hsts.log", encoding="utf-8")
        ]
    )
    logger = logging.getLogger("hsts")
    logger.info("HSTS Log Engine initialized successfully.")
