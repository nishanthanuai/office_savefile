import logging
import os
from datetime import datetime
import uuid


BASE_RUN_DIR = "runs"


def setup_master_logger():
    """
    Creates a unique run directory and master logger.
    Fully safe for parallel execution and repeated runs.
    """

    # -------------------------------------------------
    # Ensure base directory exists
    # -------------------------------------------------
    os.makedirs(BASE_RUN_DIR, exist_ok=True)

    # -------------------------------------------------
    # Unique run directory (timestamp + uuid)
    # -------------------------------------------------
    timestamp = datetime.now().strftime("%Y_%m_%d_%H_%M_%S")
    unique_id = uuid.uuid4().hex[:8]

    run_name = f"run_{timestamp}_{unique_id}"
    run_dir = os.path.join(BASE_RUN_DIR, run_name)

    os.makedirs(run_dir, exist_ok=False)  # hard fail if collision

    # -------------------------------------------------
    # Create isolated logger
    # -------------------------------------------------
    logger = logging.getLogger(run_name)
    logger.setLevel(logging.INFO)
    logger.propagate = False  # prevent root logger duplication

    # IMPORTANT: Clear old handlers if reused in same process
    if logger.hasHandlers():
        logger.handlers.clear()

    log_file = os.path.join(run_dir, "master.log")

    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(message)s"
    )
    file_handler.setFormatter(formatter)

    logger.addHandler(file_handler)

    logger.info("Master logger initialized")

    return logger, run_dir