import pandas as pd
import json
import os
import logging
# import logging
logger = logging.getLogger(__name__)


def generate_json_from_folder(folder_path, output_json_path, logger):
    logger.info(f"[SL_JSON] Generating JSON from folder: {folder_path}")
    # Define the service roads
    service_roads = [
        "Service Road LHS 1 (SRL1)",
        "Service Road LHS 2 (SRL2)",
        "Service Road LHS 3 (SRL3)",
        "Service Road LHS 4 (SRL4)",
        "Service Road LHS 5 (SRL5)",
        "Service Road LHS 6 (SRL6)",
        "Service Road LHS 7 (SRL7)",
        "Service Road LHS 8 (SRL8)",
        "Service Road LHS 9 (SRL9)",
        "Service Road LHS 10 (SRL10)"
    ]

    furniture_chainage_report = {road: {} for road in service_roads}

    road_index = 0
    logger.debug(
        f"Initialized empty report for {len(service_roads)} service roads")

    for file_name in os.listdir(folder_path):
        if file_name.endswith(".xlsx"):

            file_path = os.path.join(folder_path, file_name)
            logger.info(f"Reading Excel file: {file_name}")
            df = pd.read_excel(
                file_path,
                sheet_name="Furniture Chainage report",
                skiprows=7
            )
            logger.debug(f"Loaded dataframe shape: {df.shape}")

            df.columns = df.columns.str.strip()

            for idx, row in df.iterrows():
                logger.debug(
                    f"Row {idx} values: From={row.get('From')}, To={row.get('To')}")
                if pd.notna(row['From']) and pd.notna(row['To']):

                    from_value = int(row['From'])
                    to_value = int(row['To'])

                    range_key = f"{from_value} - {to_value}"

                    road_name = service_roads[road_index]
                    logger.debug(
                        f"Assigning to road {road_name} with index {road_index}")

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
                    logger.info(
                        f"Added entry for {road_name} range {range_key}")
                    road_index = (road_index + 1) % len(service_roads)
                    logger.debug(f"Updated road_index to {road_index}")

    with open(output_json_path, "w") as json_file:
        json.dump(furniture_chainage_report, json_file, indent=4)
    logger.info(f"[SL_JSON] JSON written to {output_json_path}")
    logger.debug(f"Final keys: {list(furniture_chainage_report.keys())}")
    return output_json_path


# -----------------------------
# MODULE RUNNER
# -----------------------------
def run(downloaded_excels_root, output_dir, logger=None):

    if logger is None:
        logger = logging.getLogger(__name__)

    logger.info("Running SL_final module")
    logger.debug(
        f"downloaded_excels_root={downloaded_excels_root}, output_dir={output_dir}")

    sl_folder = os.path.join(downloaded_excels_root, "SL")

    if not os.path.exists(sl_folder):
        logger.warning(f"SL folder not found: {sl_folder}")
        return None

    os.makedirs(output_dir, exist_ok=True)

    output_json = os.path.join(output_dir, "SL_final.json")

    logger.info(f"Processing SL folder: {sl_folder}")

    result = generate_json_from_folder(sl_folder, output_json, logger)

    logger.info(f"SL JSON created: {output_json}")

    logger.info("SL_final run completed")
    return result
