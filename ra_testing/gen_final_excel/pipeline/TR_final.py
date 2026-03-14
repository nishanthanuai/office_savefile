import pandas as pd
import json
import os
import re
import math
import logging

logger = logging.getLogger(__name__)


def generate_json_from_folder(folder_path, output_json_path="TR_final.json", logger=None):
    if logger is None:
        logger = logging.getLogger(__name__)
    logger.info(f"[TR_JSON] Generating JSON from folder: {folder_path}")
    furniture_chainage_report = {}

    lhs_service_counter = 1
    rhs_service_counter = 1
    IR_END = {}

    logger.info(f"Processing TR folder: {folder_path}")

    if not os.path.exists(folder_path):
        logger.warning(f"TR folder not found: {folder_path}")
        return None

    for file_name in os.listdir(folder_path):
        if file_name.endswith(".xlsx"):
            file_path = os.path.join(folder_path, file_name)
            logger.info(f"[TR_JSON] Processing file: {file_name}")
            logger.debug(f"Full path: {file_path}")

            if "MCW LHS" in file_name:
                road_name = "Main Carriage Way LHS"

            elif "MCW RHS" in file_name:
                road_name = "Main Carriage Way RHS"

            elif "SR" in file_name:
                match = re.search(r'SR(\d*)\s*(LHS|RHS)', file_name)
                if match:
                    side = match.group(2)

                    if side == "LHS":
                        road_name = f"Service Road LHS {lhs_service_counter} (SRL{lhs_service_counter})"
                        logger.debug(
                            f"Service road detected LHS -> {road_name}")
                    else:
                        road_name = f"Service Road RHS {rhs_service_counter} (SRR{rhs_service_counter})"
                        logger.debug(
                            f"Service road detected RHS -> {road_name}")
                else:
                    logger.warning(
                        f"Skipping file due to format issue: {file_name}")
                    continue

            elif "T" in file_name or "C" in file_name:

                match = re.search(r'(T|C)(\d*)\s*(LHS|RHS)', file_name)

                if match:

                    side = match.group(3)

                    if side == "LHS":
                        is_lhs = True
                        road_name = f"Intersection (Right below structure) (I1)"

                    else:

                        is_lhs = False
                        road_name = f"Intersection (Right below structure) (I2)"

                else:
                    logger.warning(
                        f"Skipping file due to format issue: {file_name}")
                    continue

                df = pd.read_excel(file_path, sheet_name="Assets", skiprows=2)
                df2 = pd.read_excel(file_path, sheet_name="Assets", skiprows=5)
                logger.debug(
                    f"Loaded asset sheets shapes: {df.shape}, {df2.shape}")

                start_chainage_value = df.iloc[0, 1]
                logger.debug(
                    f"Raw start_chainage_value: {start_chainage_value}")

                if isinstance(start_chainage_value, str):
                    start_chainage_value = start_chainage_value.replace(
                        '\n', '').replace(',', '').strip()

                elif pd.notna(start_chainage_value):
                    start_chainage_value = str(
                        int(start_chainage_value)).strip()

                if start_chainage_value.isdigit() and start_chainage_value != "":
                    from_value = int(start_chainage_value)

                    if is_lhs:
                        to_value = (from_value // 500 + 1) * 500
                    else:
                        to_value = (from_value // 500) * 500
                    logger.debug(
                        f"Calculated range from {from_value} to {to_value} (is_lhs={is_lhs})")

                else:
                    logger.warning(
                        f"Invalid start chainage in file: {file_name}")
                    continue

                if str(to_value) in IR_END.keys():
                    IR_END[str(to_value)] = (IR_END[str(to_value)] - 1)

                else:
                    IR_END[str(to_value)] = 2

                logger.debug(f"Updated IR_END: {IR_END}")

                road_name = f"Intersection (Right below structure) (I{IR_END[str(to_value)]})"

                if road_name not in furniture_chainage_report:
                    furniture_chainage_report[road_name] = {}

                asset_counts = {
                    "CHEVRON": {"Avenue/Left": 0, "Median/Right": 0},
                    "CAUTIONARY_WARNING_SIGNS": {"Avenue/Left": 0, "Median/Right": 0},
                    "HAZARD": {"Avenue/Left": 0, "Median/Right": 0},
                    "PROHIBITORY_MANDATORY_SIGNS": {"Avenue/Left": 0, "Median/Right": 0},
                    "INFORMATORY_SIGNS": {"Avenue/Left": 0, "Median/Right": 0, "Overhead Signs": 0}
                }

                for _, row in df2.iterrows():

                    asset_type = row.get("Asset type")
                    side = row.get("Side")
                    count = row.get("Assets Number", 0)

                    if isinstance(count, str):
                        count = count.replace(
                            '\n', '').replace(',', '').strip()
                        count = int(count) if count.isdigit() else 0

                    elif isinstance(count, (float, int)) and not math.isnan(count):
                        count = int(count)

                    else:
                        count = 0

                    logger.debug(
                        f"Asset Type: {asset_type}, Side: {side}, Count: {count}")

                    if asset_type in asset_counts:

                        if side in ["Avenue", "Left"]:
                            asset_counts[asset_type]["Avenue/Left"] += 1

                        elif side in ["Median", "Right", "Center"]:
                            asset_counts[asset_type]["Median/Right"] += 1

                        elif side in ["Overhead", "Center"]:
                            asset_counts[asset_type]["Overhead Signs"] += 1

                range_key = f"{from_value} - {to_value}"

                entry = {
                    "Road Section": road_name,
                    "from": from_value,
                    "to": to_value,
                    "CHEVRON": asset_counts["CHEVRON"],
                    "CAUTIONARY_WARNING_SIGNS": asset_counts["CAUTIONARY_WARNING_SIGNS"],
                    "HAZARD": asset_counts["HAZARD"],
                    "PROHIBITORY_MANDATORY_SIGNS": asset_counts["PROHIBITORY_MANDATORY_SIGNS"],
                    "INFORMATORY_SIGNS": asset_counts["INFORMATORY_SIGNS"]
                }

                furniture_chainage_report[road_name][range_key] = entry
                logger.info(
                    f"[TR_JSON] Added entry for {road_name} range {range_key}")

    logger.debug(
        f"Final report sections count: {len(furniture_chainage_report)}")
    with open(output_json_path, "w") as json_file:
        json.dump(furniture_chainage_report, json_file, indent=4)

    logger.info(f"TR JSON created successfully: {output_json_path}")
    logger.debug(f"Report keys: {list(furniture_chainage_report.keys())}")

    return output_json_path


def run(downloaded_excels_root, output_dir, logger=None):
    if logger is None:
        logger = logging.getLogger(__name__)
    logger.info("Running TR_final module")

    tr_folder = os.path.join(downloaded_excels_root, "TR")

    if not os.path.exists(tr_folder):
        logger.warning(f"TR folder not found: {tr_folder}")
        return None

    os.makedirs(output_dir, exist_ok=True)

    output_json = os.path.join(output_dir, "TR_final.json")

    result = generate_json_from_folder(tr_folder, output_json, logger)

    logger.info("TR_final run completed")

    return result
