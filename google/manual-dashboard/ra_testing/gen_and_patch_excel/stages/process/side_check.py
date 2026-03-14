# side_check.py

"""
Purpose:
- Normalize 'Side' field after categorization
- Apply road-type specific side mapping
- Idempotent (safe on reruns)
"""

import os
import json
import re
import logging
from typing import List, Optional

logger = logging.getLogger(__name__)

# ------------------------------------------------------------
# SIDE MAPPING RULES (UNCHANGED)
# ------------------------------------------------------------

SERVICE_ROAD_MAP = {
    "avenue": "Left",
    "median": "Right",
    "center": "Right",
    "overhead": "Left",
    "unknown": "Left",
}

MCW_MAP = {
    "overhead": "Avenue",
    "center": "Median",
    "left": "Avenue",
    "right": "Median",
}


class SideCheckError(Exception):
    """Raised when side correction fails."""


# ------------------------------------------------------------
# HELPERS
# ------------------------------------------------------------

def normalize(value):
    return value.strip().lower() if isinstance(value, str) else None


def is_valid_road_json(filename):
    return re.fullmatch(r"road_\d+\.json", filename) is not None


def get_side_mapping(road_type):
    if road_type == "service":
        return SERVICE_ROAD_MAP
    elif road_type == "mcw":
        return MCW_MAP
    else:
        raise SideCheckError(f"Invalid road type: {road_type}")


# ------------------------------------------------------------
# CORE PROCESSOR
# ------------------------------------------------------------

def process_json(input_path: str, output_path: str, side_map: dict) -> dict:

    try:
        with open(input_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        assets = data.get("assets", [])
        if not isinstance(assets, list):
            raise SideCheckError(f"Invalid assets structure in {input_path}")

        modified = 0
        total = len(assets)

        for asset in assets:
            original_side = asset.get("Side")
            norm_side = normalize(original_side)

            if norm_side in side_map:
                new_value = side_map[norm_side]
                if asset.get("Side") != new_value:
                    asset["Side"] = new_value
                    modified += 1

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)

        logger.info(
            f"Side check complete | file={os.path.basename(input_path)} "
            f"| total_assets={total} "
            f"| modified={modified}"
        )

        return {
            "file": os.path.basename(input_path),
            "total_assets": total,
            "modified": modified
        }

    except Exception as e:
        logger.exception(f"Side check failed | file={input_path}")
        raise SideCheckError(f"Side check failed for {input_path}") from e


# ------------------------------------------------------------
# PIPELINE ENTRY (MASTER CONTROLLED)
# ------------------------------------------------------------


def run(
    road_ids: List[int],
    road_type: str,
    input_dir: str,
    output_dir: str, logger: Optional[logging.Logger] = None
) -> List[str]:
    if logger is None:
        logger = logging.getLogger(__name__)

    logger.info("Starting side_check")

    os.makedirs(output_dir, exist_ok=True)

    side_map = get_side_mapping(road_type)

    processed_files = []

    for road_id in road_ids:

        filename = f"road_{road_id}.json"

        if not is_valid_road_json(filename):
            logger.warning(f"Invalid filename skipped → {filename}")
            continue

        input_path = os.path.join(input_dir, filename)

        if not os.path.exists(input_path):
            logger.error(f"Categorized JSON missing → {filename}")
            continue

        output_path = os.path.join(output_dir, filename)

        try:
            result = process_json(input_path, output_path, side_map)
            processed_files.append(result["file"])
        except SideCheckError as e:
            logger.error(str(e))
            continue

    logger.info(
        f"Completed side_check | total_success={len(processed_files)}"
    )

    return processed_files
