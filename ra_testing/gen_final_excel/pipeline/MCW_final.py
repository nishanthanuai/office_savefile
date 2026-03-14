import pandas as pd
import json
import os
import re
import math
import logging

logger = logging.getLogger(__name__)


def generate_json_from_folder(folder_path, output_json_path, logger):
    furniture_chainage_report = {}

    lhs_service_counter = 1
    rhs_service_counter = 1

    lhs_counter = 1
    rhs_counter = 1

    lhs_service = 1
    rhs_service = 1

    logger.info(f"Processing MCW folder: {folder_path}")
    logger.debug(
        f"Initial counters lhs_service={lhs_service_counter}, rhs_service={rhs_service_counter}, lhs={lhs_counter}, rhs={rhs_counter}")

    for file_name in os.listdir(folder_path):

        if file_name.endswith(".xlsx"):

            file_path = os.path.join(folder_path, file_name)

            logger.info(f"Reading file: {file_name}")
            logger.debug(f"Full path: {file_path}")

            if "MCW LHS" in file_name:
                road_name = "Main Carriage Way LHS"
                logger.debug(f"Determined road_name={road_name}")
            elif "MCW RHS" in file_name:
                road_name = "Main Carriage Way RHS"
                logger.debug(f"Determined road_name={road_name}")
            elif "SR" in file_name:
                logger.debug("Service road detected")

                match = re.search(r'SR(\d*)\s*(LHS|RHS)', file_name)

                if match:
                    side = match.group(2)
                    logger.debug(f"Service road side detected: {side}")

                    if side == "LHS":
                        road_name = f"Service Road LHS {lhs_service_counter} (SRL{lhs_service_counter})"
                        lhs_service_counter += 1

                    else:
                        road_name = f"Service Road RHS {rhs_service_counter} (SRR{rhs_service_counter})"
                        rhs_service_counter += 1
                else:
                    logger.warning(
                        f"Skipping file {file_name} due to unrecognized format.")
                    continue

            elif "T" in file_name or "C" in file_name:
                logger.debug("Intersecting or crossing road detected")

                match = re.search(r'(T|C)(\d*)\s*(LHS|RHS)', file_name)

                if match:

                    side = match.group(3)
                    logger.debug(
                        f"Intersecting/crossing side={side}, prefix={match.group(1)}")

                    if side == "LHS":
                        road_name = (
                            f"Intersecting road LHS  {lhs_counter} (IRL{lhs_counter})"
                            if match.group(1) == "T"
                            else f"Intersecting road LHS{lhs_service} (CRL{lhs_service})"
                        )

                        lhs_counter += 1 if match.group(1) == "T" else 0
                        lhs_service += 1 if match.group(1) == "C" else 0

                    else:

                        road_name = (
                            f"Intersecting road RHS {rhs_counter} (IRR{rhs_counter})"
                            if match.group(1) == "T"
                            else f"Intersecting road RHS{rhs_service} (CRR{rhs_service})"
                        )

                        rhs_counter += 1 if match.group(1) == "T" else 0
                        rhs_service += 1 if match.group(1) == "C" else 0

                else:
                    logger.warning(
                        f"Skipping file {file_name} due to unrecognized format.")
                    continue

                df = pd.read_excel(file_path, sheet_name="Assets", skiprows=2)
                df2 = pd.read_excel(file_path, sheet_name="Assets", skiprows=5)
                logger.debug(
                    f"Loaded asset sheets shapes {df.shape}, {df2.shape}")

                start_chainage_value = df.iloc[0, 1]
                logger.debug(
                    f"Raw start_chainage_value: {start_chainage_value}")

                if isinstance(start_chainage_value, str):
                    start_chainage_value = start_chainage_value.replace(
                        '\n', '').replace(',', '').strip()

                elif pd.notna(start_chainage_value):
                    start_chainage_value = str(
                        int(start_chainage_value)).strip()

                logger.debug(
                    f"Normalized start_chainage_value: {start_chainage_value}")

                if start_chainage_value.isdigit() and start_chainage_value != "":

                    start_chainage = int(start_chainage_value)

                    from_value = start_chainage
                    to_value = from_value + 500
                    logger.debug(f"Calculated range {from_value} - {to_value}")

                else:
                    logger.warning(
                        f"Skipping file {file_name} as Start Chainage is invalid.")
                    continue

                if road_name not in furniture_chainage_report:
                    furniture_chainage_report[road_name] = {}

                asset_counts = {
                    "CHEVRON": {"Avenue/Left": 0, "Median/Right": 0},
                    "CAUTIONARY_WARNING_SIGNS": {"Avenue/Left": 0, "Median/Right": 0},
                    "HAZARD": {"Avenue/Left": 0, "Median/Right": 0},
                    "PROHIBITORY_MANDATORY_SIGNS": {"Avenue/Left": 0, "Median/Right": 0},
                    "INFORMATORY_SIGNS": {"Avenue/Left": 0, "Median/Right": 0}
                }
                logger.debug(f"Initialized asset_counts for {road_name}")

                for idx, row in df2.iterrows():

                    asset_type = row.get("Asset type")
                    side = row.get("Side")
                    count = row.get("Assets Number", 0)
                    logger.debug(
                        f"Row {idx}: type={asset_type}, side={side}, count={count}")

                    if isinstance(count, str):
                        count = count.replace(
                            '\n', '').replace(',', '').strip()
                        count = int(count) if count.isdigit() else 0

                    elif isinstance(count, (float, int)) and not math.isnan(count):
                        count = int(count)

                    else:
                        count = 0

                    if asset_type in asset_counts:

                        if side in ["Avenue", "Left"]:
                            asset_counts[asset_type]["Avenue/Left"] += count

                        elif side in ["Median", "Right"]:
                            asset_counts[asset_type]["Median/Right"] += count

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
                continue

            df = pd.read_excel(
                file_path, sheet_name="Furniture Chainage report", skiprows=7)

            df.columns = df.columns.str.strip()

            if road_name not in furniture_chainage_report:
                furniture_chainage_report[road_name] = {}

            for _, row in df.iterrows():

                if pd.notna(row['From']) and pd.notna(row['To']):

                    from_value = int(row['From'])
                    to_value = int(row['To'])

                    range_key = f"{from_value} - {to_value}"

                    entry = {
                        "Road Section": road_name,
                        "from": from_value,
                        "to": to_value,
                        "CHEVRON": {
                            "Avenue/Left": row.get('CHEVRON', 0),
                            "Median/Right": row.get('Unnamed: 11', 0)
                        },
                        "CAUTIONARY_WARNING_SIGNS": {
                            "Avenue/Left": row.get('CAUTIONARY_WARNING_SIGNS', 0),
                            "Median/Right": row.get('Unnamed: 13', 0),
                            "Overhead Signs": "NONE"
                        },
                        "HAZARD": {
                            "Avenue/Left": row.get('HAZARD', 0),
                            "Median/Right": row.get('Unnamed: 15', 0)
                        },
                        "PROHIBITORY_MANDATORY_SIGNS": {
                            "Avenue/Left": row.get('PROHIBITORY_MANDATORY_SIGNS', 0),
                            "Median/Right": row.get('Unnamed: 17', 0),
                            "Overhead Signs": "NONE"
                        },
                        "INFORMATORY_SIGNS": {
                            "Avenue/Left": row.get('INFORMATORY_SIGNS', 0),
                            "Median/Right": row.get('Unnamed: 19', 0),
                            "Overhead Signs": "NONE"
                        }
                    }

                    furniture_chainage_report[road_name][range_key] = entry
                    continue

    with open(output_json_path, "w") as json_file:
        json.dump(furniture_chainage_report, json_file, indent=4)

    logger.info(f"MCW JSON created successfully at: {output_json_path}")
    logger.debug(
        f"Final report keys: {list(furniture_chainage_report.keys())}")

    return output_json_path


def run(downloaded_excels_root, output_dir, logger):
    """
    Pipeline entrypoint
    """

    mcw_folder = os.path.join(downloaded_excels_root, "MCW")

    logger.debug(f"MCW folder path: {mcw_folder}")

    os.makedirs(output_dir, exist_ok=True)

    output_json = os.path.join(output_dir, "MCW_final.json")

    logger.info("Running MCW_final module")

    result = generate_json_from_folder(mcw_folder, output_json, logger)

    logger.info("MCW_final module completed")

    return result
