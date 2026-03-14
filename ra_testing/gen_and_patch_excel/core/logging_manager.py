import logging
import os
import json
import uuid 
from datetime import datetime
from logging.handlers import RotatingFileHandler
from typing import Tuple, Dict, Any



# ============================================================
# Utility: Create run directory
# ============================================================

def _create_run_directory(base_dir: str = "logs") -> str:
    os.makedirs(base_dir, exist_ok=True)

    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    unique_id = uuid.uuid4().hex[:8]

    run_dir = os.path.join(base_dir, f"{timestamp}_{unique_id}_run")

    # Fail if collision (extremely unlikely)
    os.makedirs(run_dir, exist_ok=False)
    return run_dir


# ============================================================
# Utility: Standard formatter
# ============================================================

def _get_formatter() -> logging.Formatter:
    return logging.Formatter(
        "%(asctime)s | %(name)s | %(levelname)s | %(message)s"
    )


# ============================================================
# Master Logger (Per Run)
# ============================================================

def setup_master_logger() -> Tuple[logging.Logger, str]:
    """
    Creates:
        logs/<timestamp>_run/
            master.log

    Returns:
        (master_logger, run_dir)
    """

    run_dir = _create_run_directory()

    logger = logging.getLogger(os.path.basename(run_dir))
    logger.setLevel(logging.INFO)
    logger.propagate = False

    # Avoid duplicate handlers if re-run in same process
    if logger.handlers:
        logger.handlers.clear()

    formatter = _get_formatter()

    # File handler (rotating)
    file_handler = RotatingFileHandler(
        os.path.join(run_dir, "master.log"),
        maxBytes=5_000_000,
        backupCount=3
    )
    file_handler.setFormatter(formatter)

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    logger.info("Master logger initialized | run_dir=%s", run_dir)

    return logger, run_dir


# ============================================================
# Road Logger (Per Road Inside Run)
# ============================================================

def setup_road_logger(run_dir: str, road_id: int):
    """
    Creates isolated logger + folder for each road inside a run.
    Safe for parallel processing.
    """

    # -------------------------------------------------
    # Create road directory
    # -------------------------------------------------
    road_dir = os.path.join(run_dir, f"road_{road_id}")
    os.makedirs(road_dir, exist_ok=True)

    # -------------------------------------------------
    # Unique logger name (avoid collisions)
    # -------------------------------------------------
    run_name = os.path.basename(run_dir)
    logger_name = f"{run_name}_road_{road_id}"

    logger = logging.getLogger(logger_name)
    logger.setLevel(logging.INFO)
    logger.propagate = False

    # IMPORTANT: Clear handlers to avoid duplication
    if logger.hasHandlers():
        logger.handlers.clear()

    log_file = os.path.join(road_dir, "road.log")

    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    formatter = _get_formatter()
    file_handler.setFormatter(formatter)

    logger.addHandler(file_handler)

    logger.info(f"Road logger initialized for road_id={road_id}")

    return logger, road_dir

# ============================================================
# Structured JSON Logging (For RAG)
# ============================================================

def write_structured_log(
    road_dir: str,
    data: Dict[str, Any]
) -> None:
    """
    Appends structured machine-readable log for RAG.
    File:
        structured_log.jsonl
    """

    structured_file = os.path.join(road_dir, "structured_log.jsonl")

    entry = {
        "timestamp": datetime.utcnow().isoformat(),
        **data
    }

    with open(structured_file, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")


# ============================================================
# Stage Summary Writer
# ============================================================

def write_stage_summary(
    road_dir: str,
    stage_name: str,
    status: str,
    metadata: Dict[str, Any] = None
) -> None:
    """
    Writes structured stage summary for RAG analytics.
    """

    payload = {
        "stage": stage_name,
        "status": status,
        "metadata": metadata or {}
    }

    write_structured_log(road_dir, payload)


# ============================================================
# Run Summary Writer
# ============================================================

def write_run_summary(
    run_dir: str,
    summary: Dict[str, Any]
) -> None:
    """
    Saves overall run summary to:
        logs/<run>/run_summary.json
    """

    path = os.path.join(run_dir, "run_summary.json")

    with open(path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=4)
