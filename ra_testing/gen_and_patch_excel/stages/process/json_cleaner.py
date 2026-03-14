# # json_cleaner.py

# import json
# import os
# import copy
# import logging
# from typing import List, Tuple, Dict

# logger = logging.getLogger(__name__)

# INPUT_BASE = "jsons"
# OUTPUT_BASE = "jsons_cleaned"
# FLAGS_BASE = "jsons_flags"


# class JSONCleanerError(Exception):
#     """Custom exception for JSON cleaning failures."""
#     pass


# def norm(val):
#     if isinstance(val, str):
#         return val.strip().lower()
#     return val


# # ---------------- RULE ENGINE ---------------- #

# def apply_rules(data: Dict) -> Tuple[Dict, Dict]:
#     assets = data.get("assets", [])
#     anomalies = data.get("anomalies", [])

#     cleaned_assets = []
#     cleaned_anomalies = copy.deepcopy(anomalies)
#     flagged_assets = []

#     for asset in assets:
#         asset_type = norm(asset.get("Asset type"))
#         side = norm(asset.get("Side"))

#         # RULE 1: DAMAGED SIGN → ANOMALIES
#         if asset_type == "damaged_sign":
#             cleaned_anomalies.append(asset)
#             continue

#         # RULE 2: FLAG UNKNOWN SIDE
#         if side == "unknown":
#             flagged = copy.deepcopy(asset)
#             flagged["__flags__"] = ["UNKNOWN_SIDE"]
#             flagged_assets.append(flagged)

#         cleaned_assets.append(asset)

#     cleaned_data = {
#         "assets": cleaned_assets,
#         "anomalies": cleaned_anomalies
#     }

#     flags_data = {
#         "assets": flagged_assets,
#         "anomalies": []
#     }

#     return cleaned_data, flags_data


# # ---------------- CORE CLEANER ---------------- #

# def clean_single_json(road_id: int, road_type: str) -> Tuple[str, str]:
#     """
#     Cleans a single JSON file.

#     Returns:
#         (cleaned_json_path, flags_json_path)
#     """

#     input_file = os.path.join(INPUT_BASE, road_type, f"road_{road_id}.json")

#     logger.info(f"Cleaning JSON | road_id={road_id} | type={road_type}")

#     if not os.path.exists(input_file):
#         logger.error(f"Input JSON not found: {input_file}")
#         raise JSONCleanerError(f"JSON not found for road {road_id}")

#     try:
#         with open(input_file, "r", encoding="utf-8") as f:
#             data = json.load(f)

#         cleaned_data, flags_data = apply_rules(data)

#         out_clean_dir = os.path.join(OUTPUT_BASE, road_type)
#         out_flag_dir = os.path.join(FLAGS_BASE, road_type)

#         os.makedirs(out_clean_dir, exist_ok=True)
#         os.makedirs(out_flag_dir, exist_ok=True)

#         output_json = os.path.join(out_clean_dir, f"road_{road_id}.json")
#         output_flags = os.path.join(out_flag_dir, f"road_{road_id}_flags.json")

#         with open(output_json, "w", encoding="utf-8") as f:
#             json.dump(cleaned_data, f, indent=4, ensure_ascii=False)

#         with open(output_flags, "w", encoding="utf-8") as f:
#             json.dump(flags_data, f, indent=4, ensure_ascii=False)

#         logger.info(
#             f"JSON cleaned successfully | road_id={road_id} "
#             f"| assets={len(cleaned_data['assets'])} "
#             f"| anomalies={len(cleaned_data['anomalies'])} "
#             f"| flags={len(flags_data['assets'])}"
#         )

#         return output_json, output_flags

#     except Exception as e:
#         logger.exception(f"Failed cleaning JSON for road_id={road_id}")
#         raise JSONCleanerError(
#             f"JSON cleaning failed for road {road_id}"
#         ) from e


# def run(road_ids: List[int], road_type: str) -> List[Tuple[str, str]]:
#     """
#     Master entry function.

#     Returns:
#         List of tuples:
#         [(cleaned_json_path, flags_json_path), ...]
#     """

#     logger.info(f"Starting JSON cleaning | road_type={road_type}")

#     results = []

#     for rid in road_ids:
#         try:
#             paths = clean_single_json(rid, road_type)
#             results.append(paths)
#         except JSONCleanerError as e:
#             logger.error(str(e))
#             continue

#     logger.info(f"Completed JSON cleaning | total_success={len(results)}")

#     return results

# json_cleaner.py

import json
import os
import copy
import logging
import re
from typing import List, Tuple, Dict, Optional


logger = logging.getLogger(__name__)

# INPUT_BASE = "jsons"
# OUTPUT_BASE = "jsons_cleaned"
# FLAGS_BASE = "jsons_flags"


class JSONCleanerError(Exception):
    """Custom exception for JSON cleaning failures."""
    pass


def norm(val):
    if isinstance(val, str):
        return val.strip().lower()
    return val


# ---------------- RULE ENGINE ---------------- #

# ---------------- CATEGORY FIX ENGINE ---------------- #


def _normalize(text):
    return str(text).replace(" ", "").replace("_", "").upper()


def _get_category(asset_type: str):
    asset = _normalize(asset_type)

    if "SPEEDBREAKER" in asset:
        return "Cautionary Signs"

    if "VMS(VARIABLEMESSAGESIGN)" in asset:
        return "Informatory Signs"

    if "ADVERTISEMENTENCHROACHMENT" in asset:
        return "Enchroachment Signs"

    if "INFORMATORYSIGNS" in asset:
        return "Informatory Signs"

    if "CAUTIONARYWARNINGSIGNS" in asset:
        return "Cautionary Signs"

    if "PROHIBITORYMANDATORYSIGNS" in asset:
        return "Mandatory Signs"

    if "HAZARD" in asset or "CHEVRON" in asset:
        return "Cautionary Signs"

    if "NONSTANDARDINFOMATORYSIGNS" in asset:
        return "Informatory Signs"

    ROAD_FURNITURE = [
        "KMSTONE", "SOLARBLINKER", "GUARDPOST",
        "ROWPILLAR", "SOS", "CCTV",
        "SPEEDDISPLAY", "ARROWMARKING",
        "CHEVRONMARKING", "DIAGONALMARKING",
        "UNDERGROUNDGASPIPELINEMARKER"
    ]

    for rf in ROAD_FURNITURE:
        if rf in asset:
            return "Road Furniture"

    try:
        m = re.match(r"(\d+)_(\d+)", asset_type)
        if m:
            v = float(f"{int(m.group(1))}.{int(m.group(2)):02d}")

            if 14.01 <= v <= 14.59:
                return "Mandatory Signs"

            if 15.01 <= v <= 15.80:
                return "Cautionary Signs"

            if 16.01 <= v <= 25.03:
                return "Informatory Signs"
    except:
        pass

    return None


def _fix_null_or_unknown_category(asset: Dict) -> None:
    """
    Fix category if null / unknown / missing.
    Modifies asset in-place.
    """

    category = norm(asset.get("category") or asset.get("Category"))
    asset_type = asset.get("Asset type", "")

    if not category or category == "unknown":
        corrected = _get_category(asset_type)
        if corrected:
            asset["category"] = corrected


def apply_rules(data: Dict) -> Tuple[Dict, Dict]:
    """
    Apply cleaning + validation rules to JSON data.
    """

    assets = data.get("assets", [])
    anomalies = data.get("anomalies", [])

    cleaned_assets = []
    cleaned_anomalies = anomalies.copy()
    flagged_assets = []
    deleted_count = 0

    for asset in assets:

        # ------------------------------
        # RULE 0: DELETE IF DISTANCE IS NULL
        # ------------------------------
        if asset.get("Distance") is None:
            deleted_count += 1
            logger.info(f"Deleted {deleted_count} assets due to null Distance")
            continue  # Skip entire asset

        asset_type = norm(asset.get("Asset type"))
        side = norm(asset.get("Side"))

        # ------------------------------
        # FIX CATEGORY IF NULL/UNKNOWN
        # ------------------------------
        _fix_null_or_unknown_category(asset)

        # ------------------------------
        # RULE 1: DAMAGED SIGN → ANOMALIES
        # ------------------------------
        if asset_type == "damaged_sign":
            cleaned_anomalies.append(asset)
            continue

        # ------------------------------
        # RULE 2: FLAG UNKNOWN SIDE
        # ------------------------------
        if side == "unknown":
            flagged = copy.deepcopy(asset)
            flagged["__flags__"] = ["UNKNOWN_SIDE"]
            flagged_assets.append(flagged)

        cleaned_assets.append(asset)

    cleaned_data = {
        "assets": cleaned_assets,
        "anomalies": cleaned_anomalies
    }

    flags_data = {
        "assets": flagged_assets,
        "anomalies": []
    }

    return cleaned_data, flags_data


# ---------------- CORE CLEANER ---------------- #

 # ---------------- CORE CLEANER ---------------- #


def clean_single_json(
    road_id: int,
    input_dir: str,
    cleaned_dir: str,
    flags_dir: str
) -> Tuple[str, str]:
    """
    Cleans a single JSON file.

    Returns:
        (cleaned_json_path, flags_json_path)
    """

    input_file = os.path.join(input_dir, f"road_{road_id}.json")

    logger.info(f"Cleaning JSON | road_id={road_id}")

    if not os.path.exists(input_file):
        logger.error(f"Input JSON not found: {input_file}")
        raise JSONCleanerError(f"JSON not found for road {road_id}")

    try:
        with open(input_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        cleaned_data, flags_data = apply_rules(data)

        os.makedirs(cleaned_dir, exist_ok=True)
        os.makedirs(flags_dir, exist_ok=True)

        output_json = os.path.join(cleaned_dir, f"road_{road_id}.json")
        output_flags = os.path.join(flags_dir, f"road_{road_id}_flags.json")

        with open(output_json, "w", encoding="utf-8") as f:
            json.dump(cleaned_data, f, indent=4, ensure_ascii=False)

        with open(output_flags, "w", encoding="utf-8") as f:
            json.dump(flags_data, f, indent=4, ensure_ascii=False)

        logger.info(
            f"JSON cleaned successfully | road_id={road_id} "
            f"| assets={len(cleaned_data['assets'])} "
            f"| anomalies={len(cleaned_data['anomalies'])} "
            f"| flags={len(flags_data['assets'])}"
        )

        return output_json, output_flags

    except Exception as e:
        logger.exception(f"Failed cleaning JSON for road_id={road_id}")
        raise JSONCleanerError(
            f"JSON cleaning failed for road {road_id}"
        ) from e


def run(
    road_ids: List[int],
    input_dir: str,
    cleaned_dir: str,
    flags_dir: str, logger: Optional[logging.Logger] = None
) -> List[Tuple[str, str]]:
    """
    Master entry function.
    """
    if logger is None:
        logger = logging.getLogger(__name__)

    logger.info("Starting JSON cleaning")

    results = []

    for rid in road_ids:
        try:
            paths = clean_single_json(
                rid,
                input_dir,
                cleaned_dir,
                flags_dir
            )
            results.append(paths)
        except JSONCleanerError as e:
            logger.error(str(e))
            continue

    logger.info(f"Completed JSON cleaning | total_success={len(results)}")

    return results
