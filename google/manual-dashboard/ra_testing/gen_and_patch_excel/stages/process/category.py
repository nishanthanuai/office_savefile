# category.py

"""
Purpose:
- Normalize RIS asset classes for dashboard + excel
- Preserve ML detected subclass forever
- Idempotent (safe on reruns)
"""

import os
import json
import re
import logging
from typing import List, Optional
from core.sign_maps import SIGN_CATEGORY_MAP

logger = logging.getLogger(__name__)

# --------------------------------------------------
# CANONICAL 5 CLASSES
# --------------------------------------------------

FINAL_CLASSES = {
    "CHEVRON",
    "CAUTIONARY_WARNING_SIGNS",
    "HAZARD",
    "PROHIBITORY_MANDATORY_SIGNS",
    "INFORMATORY_SIGNS",
}


class CategorizationError(Exception):
    """Raised when categorization fails."""


# --------------------------------------------------
# HELPERS
# --------------------------------------------------

def normalize(val):
    return val.strip().upper() if isinstance(val, str) else val


def is_valid_road_json(filename):
    return re.fullmatch(r"road_\d+\.json", filename) is not None


# =====================================================
# CORE NORMALIZER (IDEMPOTENT — LOGIC UNCHANGED)
# =====================================================

def normalize_asset(item: dict) -> bool:
    """
    Returns True if modified, False otherwise.
    """
    raw_type = item.get("Asset type") or item.get("Anomaly type")
    if not raw_type:
        return False

    raw_norm = normalize(raw_type)

    # Already final class → do nothing
    if raw_norm in FINAL_CLASSES:
        return False

    main_class = SIGN_CATEGORY_MAP.get(raw_norm)
    if not main_class:
        logger.debug(f"Unknown subclass encountered → {raw_norm}")
        return False

    # Preserve ML subclass ONCE
    if "sub_class" not in item:
        item["sub_class"] = raw_norm

    # Replace type safely
    if "Asset type" in item:
        item["Asset type"] = main_class
    if "Anomaly type" in item:
        item["Anomaly type"] = main_class

    return True


# =====================================================
# FILE PROCESSOR
# =====================================================

def process_json(input_file: str, output_file: str) -> dict:

    try:
        with open(input_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        modified_count = 0
        total_items = 0

        for section in ("assets", "anomalies"):
            for item in data.get(section, []):
                total_items += 1
                if normalize_asset(item):
                    modified_count += 1

        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)

        logger.info(
            f"Categorized file | file={os.path.basename(input_file)} "
            f"| total_items={total_items} "
            f"| modified={modified_count}"
        )

        return {
            "file": os.path.basename(input_file),
            "total_items": total_items,
            "modified": modified_count
        }

    except Exception as e:
        logger.exception(f"Failed processing JSON | file={input_file}")
        raise CategorizationError(
            f"Categorization failed for {input_file}"
        ) from e


# =====================================================
# PIPELINE ENTRY (MASTER CONTROLLED)
# =====================================================

def run(
    road_ids: List[int],
    input_dir: str,
    output_dir: str, logger: Optional[logging.Logger] = None
) -> List[str]:
    if logger is None:
        logger = logging.getLogger(__name__)

    logger.info("Starting categorization")

    os.makedirs(output_dir, exist_ok=True)

    processed_files = []

    for road_id in road_ids:

        filename = f"road_{road_id}.json"

        if not is_valid_road_json(filename):
            logger.warning(f"Invalid filename skipped → {filename}")
            raise

        input_path = os.path.join(input_dir, filename)
        output_path = os.path.join(output_dir, filename)

        if not os.path.exists(input_path):
            logger.error(f"Missing cleaned JSON → {filename}")
            raise

        try:
            result = process_json(input_path, output_path)
            processed_files.append(result["file"])
        except CategorizationError as e:
            logger.error(str(e))
            raise

    logger.info(
        f"Completed categorization | total_success={len(processed_files)}"
    )

    return processed_files
