import logging
import os
import json
import uuid
import shutil
from datetime import datetime
from logging.handlers import RotatingFileHandler
from typing import Dict, Any


class JsonFormatter(logging.Formatter):
    """
    Structured JSON logger for RAG ingestion
    """

    def format(self, record):
        # base record
        log_record = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "message": record.getMessage(),
            "logger": record.name,
            "module": record.module if hasattr(record, "module") else None,
            "filename": record.filename if hasattr(record, "filename") else None,
            "lineno": record.lineno if hasattr(record, "lineno") else None,
        }

        # include exception information if present
        if record.exc_info:
            log_record["exc_info"] = self.formatException(record.exc_info)

        # include any extra data attached by callers
        if hasattr(record, "extra_data"):
            log_record["extra"] = record.extra_data

        return json.dumps(log_record, ensure_ascii=False)


class LoggingManager:

    def __init__(self, base_log_dir="logs"):
        self.base_log_dir = base_log_dir
        os.makedirs(self.base_log_dir, exist_ok=True)

    def create_run(self, survey_id: int) -> Dict[str, Any]:

        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        run_uuid = str(uuid.uuid4())[:8]

        run_id = f"{timestamp}_{run_uuid}_run"

        run_folder = os.path.join(self.base_log_dir, run_id)
        survey_folder = os.path.join(run_folder, f"survey_{survey_id}")

        # Ensure folders exist before creating handlers
        os.makedirs(survey_folder, exist_ok=True)

        logger = self._create_logger(run_id, run_folder)
        
        # Keep only the last 30 runs, deleting everything else besides the 2 main log files in older runs
        self._cleanup_old_runs()

        return {
            "run_id": run_id,
            "run_folder": run_folder,
            "survey_folder": survey_folder,
            "logger": logger
        }

    def _cleanup_old_runs(self, max_runs: int = 30):
        """Clean up old run folders after a specified number of runs, keeping only essential log files."""
        try:
            if not os.path.exists(self.base_log_dir):
                return
                
            run_folders = []
            for item in os.listdir(self.base_log_dir):
                item_path = os.path.join(self.base_log_dir, item)
                if os.path.isdir(item_path) and item.endswith("_run"):
                    run_folders.append(item_path)
            
            # Sort by name (which starts with timestamp) in descending order to keep the newest first
            run_folders.sort(reverse=True)
            
            # If we have more than max_runs, clean up the older ones
            if len(run_folders) > max_runs:
                old_runs = run_folders[max_runs:]
                for old_run in old_runs:
                    for item in os.listdir(old_run):
                        if item not in ["pipeline.log", "structured_log.jsonl"]:
                            item_path = os.path.join(old_run, item)
                            try:
                                if os.path.isdir(item_path):
                                    shutil.rmtree(item_path)
                                else:
                                    os.remove(item_path)
                            except Exception:
                                pass
        except Exception:
            pass

    def _create_logger(self, run_id: str, run_folder: str):

        # Use run_id as logger name for clarity
        logger = logging.getLogger(run_id)
        logger.setLevel(logging.INFO)
        logger.propagate = True

        # Avoid adding handlers multiple times
        if logger.handlers:
            return logger

        log_file = os.path.join(run_folder, "pipeline.log")
        json_log = os.path.join(run_folder, "structured_log.jsonl")

        # human readable formatter
        formatter = logging.Formatter(
            "%(asctime)s - %(levelname)s - %(name)s - %(message)s"
        )

        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=5 * 1024 * 1024,
            backupCount=5,
            encoding="utf-8"
        )
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(formatter)

        # structured JSON handler
        json_handler = RotatingFileHandler(
            json_log,
            maxBytes=5 * 1024 * 1024,
            backupCount=5,
            encoding="utf-8"
        )
        json_handler.setLevel(logging.DEBUG)
        json_handler.setFormatter(JsonFormatter())

        # optional console output for interactive runs
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(formatter)

        logger.addHandler(file_handler)
        logger.addHandler(json_handler)
        logger.addHandler(console_handler)

        return logger

    def close_logger(self, logger_obj: logging.Logger):
        """Flush and close handlers for a logger created by this manager."""
        handlers = list(logger_obj.handlers)
        for h in handlers:
            try:
                h.flush()
                h.close()
            except Exception:
                pass
            logger_obj.removeHandler(h)
