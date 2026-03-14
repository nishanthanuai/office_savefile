# import requests
# import json
# from collections import defaultdict

# # ============================================
# # CONFIG
# # ============================================

# point = "ndd"
# SURVEY_ID = int(input("Enter Survey ID: "))

# BASE_SURVEY_URL = f"https://{point}.roadathena.com/api/surveys/"
# BASE_ROAD_URL = f"https://{point}.roadathena.com/api/surveys/roads/"

# HEADERS = {
#     "Security-Password": "admin@123",
#     "Content-Type": "application/json",
#     "Accept": "application/json"
# }

# TARGET_ASSETS = [
#     "CHEVRON",
#     "CAUTIONARY_WARNING_SIGNS",
#     "HAZARD",
#     "PROHIBITORY_MANDATORY_SIGNS",
#     "INFORMATORY_SIGNS"
# ]


# # ============================================
# # FETCH SURVEY
# # ============================================

# def fetch_survey_roads(survey_id):
#     url = f"{BASE_SURVEY_URL}{survey_id}"

#     response = requests.get(url, headers=HEADERS)

#     if response.status_code != 200:
#         print("Failed to fetch survey")
#         return []

#     data = response.json()

#     roads = data.get("roads", [])

#     road_ids = [road["id"] for road in roads]

#     return road_ids


# # ============================================
# # FETCH ROAD JSON
# # ============================================

# def fetch_furniture_json(road_id):

#     road_url = f"{BASE_ROAD_URL}{road_id}"

#     response = requests.get(road_url, headers=HEADERS)

#     if response.status_code != 200:
#         print(f"Failed to fetch road {road_id}")
#         return None

#     road_data = response.json()

#     furniture_path = road_data.get("furniture_json")

#     if not furniture_path:
#         print(f"No furniture JSON for road {road_id}")
#         return None

#     json_url = f"https://{point}.roadathena.com/{furniture_path}"

#     json_response = requests.get(json_url)

#     if json_response.status_code != 200:
#         print(f"Failed to download JSON for road {road_id}")
#         return None

#     return json_response.json()


# # ============================================
# # COUNT TARGET ASSETS
# # ============================================

# def count_assets(data):

#     counts = defaultdict(int)

#     assets = data.get("assets", [])

#     for asset in assets:

#         asset_type = asset.get("Asset type")

#         if asset_type in TARGET_ASSETS:
#             counts[asset_type] += 1

#     return counts


# # ============================================
# # MAIN
# # ============================================

# def main():

#     print("\nFetching roads from survey...\n")

#     road_ids = fetch_survey_roads(SURVEY_ID)

#     print(f"Total Roads Found: {len(road_ids)}\n")

#     final_counts = defaultdict(int)

#     for road_id in road_ids:

#         print(f"Processing road {road_id}")

#         data = fetch_furniture_json(road_id)

#         if not data:
#             continue

#         road_counts = count_assets(data)

#         for asset in TARGET_ASSETS:
#             final_counts[asset] += road_counts.get(asset, 0)

#     # ====================================
#     # FINAL OUTPUT
#     # ====================================

#         # ====================================
#     # FINAL OUTPUT
#     # ====================================

#     print("\n==============================\n")

#     total = 0

#     for asset in TARGET_ASSETS:
#         count = final_counts.get(asset, 0)
#         print(f"{asset} = {count}")
#         total += count

#     print("\n==============================")

#     print(f"Total Counts = {total}\n")


# # ============================================
# if __name__ == "__main__":
#     main()
import requests
from collections import defaultdict

point = "ndd"

BASE_SURVEY_URL = f"https://{point}.roadathena.com/api/surveys/"
BASE_ROAD_URL = f"https://{point}.roadathena.com/api/surveys/roads/"

HEADERS = {
    "Security-Password": "admin@123",
    "Content-Type": "application/json",
    "Accept": "application/json"
}

TARGET_ASSETS = [
    "CHEVRON",
    "CAUTIONARY_WARNING_SIGNS",
    "HAZARD",
    "PROHIBITORY_MANDATORY_SIGNS",
    "INFORMATORY_SIGNS"
]


def fetch_survey_roads(survey_id):

    url = f"{BASE_SURVEY_URL}{survey_id}"

    response = requests.get(url, headers=HEADERS)

    if response.status_code != 200:
        return []

    data = response.json()

    roads = data.get("roads", [])

    return [road["id"] for road in roads]


def fetch_furniture_json(road_id):

    road_url = f"{BASE_ROAD_URL}{road_id}"

    response = requests.get(road_url, headers=HEADERS)

    if response.status_code != 200:
        return None

    road_data = response.json()

    furniture_path = road_data.get("furniture_json")

    if not furniture_path:
        return None

    json_url = f"https://{point}.roadathena.com/{furniture_path}"

    json_response = requests.get(json_url)

    if json_response.status_code != 200:
        return None

    return json_response.json()


def count_assets(data):

    counts = defaultdict(int)

    assets = data.get("assets", [])

    for asset in assets:

        asset_type = asset.get("Asset type")

        if asset_type in TARGET_ASSETS:
            counts[asset_type] += 1

    return counts


def run(survey_id, logger):

    logger.info("VALIDATOR STARTED")

    road_ids = fetch_survey_roads(survey_id)

    logger.info(f"Total Roads Found: {len(road_ids)}")

    final_counts = defaultdict(int)

    for road_id in road_ids:

        logger.info(f"Processing road {road_id}")

        data = fetch_furniture_json(road_id)

        if not data:
            logger.warning(f"No JSON for road {road_id}")
            continue

        road_counts = count_assets(data)

        for asset in TARGET_ASSETS:
            final_counts[asset] += road_counts.get(asset, 0)

    total = sum(final_counts.values())

    logger.info("========== VALIDATOR RESULT ==========")

    for asset in TARGET_ASSETS:
        logger.info(f"{asset} = {final_counts.get(asset, 0)}")

    logger.info(f"TOTAL ASSETS = {total}")

    logger.info("======================================")

    return {
        "categories": dict(final_counts),
        "total_assets": total
    }
