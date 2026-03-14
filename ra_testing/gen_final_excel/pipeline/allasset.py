import requests
import json
import time

point = "ndd"

BASE_URL = f"https://{point}.roadathena.com/api/surveys/roads/"
HEADERS = {
    "Security-Password": "admin@123",
    "Content-Type": "application/json",
    "Connection": "keep-alive",
    "Accept": "application/json"
}


def final_count_update(SURVEY_IDS, logger):

    RETRY_COUNT = 3
    DELAY_BETWEEN_REQUESTS = 1

    session = requests.Session()
    session.headers.update(HEADERS)

    def fetch_with_retries(url, retries=RETRY_COUNT, delay=DELAY_BETWEEN_REQUESTS):
        """Fetches data from a given URL with retries in case of failures."""
        for attempt in range(1, retries + 1):
            try:
                response = session.get(url, timeout=10)
                if response.status_code == 200:
                    return response.json()
                elif response.status_code == 404:
                    logger.warning(f"Survey ID not found: {url}")
                    return None
                else:
                    logger.warning(
                        f"[Attempt {attempt}] Failed to fetch {url}: {response.status_code}")
            except requests.exceptions.ConnectionError:
                logger.warning(
                    f"[Attempt {attempt}] Connection error, retrying in {delay} sec...")
            except requests.exceptions.JSONDecodeError:
                logger.warning(
                    f"[Attempt {attempt}] Invalid JSON response from {url}")

            time.sleep(delay)
        return None

    for survey_id in SURVEY_IDS:
        survey_url = f"{BASE_URL}{survey_id}"
        logger.info(f"Processing Survey ID: {survey_id}")

        survey_data = fetch_with_retries(survey_url)
        if not survey_data:
            logger.warning(f"Skipping Survey ID {survey_id} (No Data)")
            continue

        furniture_json_path = survey_data.get("furniture_json")
        if not furniture_json_path:
            logger.warning(
                f"No furniture JSON found for Survey ID {survey_id}")
            continue

        furniture_json_url = f"https://{point}.roadathena.com/{furniture_json_path}"
        furniture_data = fetch_with_retries(furniture_json_url)
        if not furniture_data:
            logger.warning(
                f"Skipping furniture data for Survey ID {survey_id}")
            continue

        combined_counts = {}

        valid_assets = [
            asset for asset in furniture_data.get("assets", [])
            if asset.get("Latitude") not in (None, 0) and asset.get("Longitude") not in (None, 0)
        ]

        for asset in valid_assets:
            asset_type = asset.get("Asset type")
            if asset_type:
                combined_counts[asset_type] = combined_counts.get(
                    asset_type, 0) + 1

        valid_anomalies = [
            anomaly for anomaly in furniture_data.get("anomalies", [])
            if anomaly.get("Latitude") not in (None, 0) and anomaly.get("Longitude") not in (None, 0)
        ]

        for anomaly in valid_anomalies:
            anomaly_type = anomaly.get("Anomaly type")
            if anomaly_type:
                combined_counts[anomaly_type] = combined_counts.get(
                    anomaly_type, 0) + 1

        update_payload = combined_counts

        approaches = [
            {"anomaly_data": combined_counts},
            {"anomaly_data": json.dumps(combined_counts)},
            combined_counts
        ]

        success = False

        for i, approach in enumerate(approaches, 1):
            try:
                logger.info(f"Trying approach #{i}")
                json_data = json.dumps(approach)
                logger.info(f"Sending payload: {json_data}")

                patch_response = session.patch(
                    survey_url,
                    headers=HEADERS,
                    data=json_data,
                    timeout=10
                )

                logger.info(f"Response Status: {patch_response.status_code}")

                if patch_response.status_code == 200:
                    verify_response = session.get(survey_url, headers=HEADERS)
                    if verify_response.status_code == 200:
                        updated_data = verify_response.json()
                        logger.info(
                            f"Anomaly data after update: {updated_data.get('anomaly_data', {})}")

                        if updated_data.get('anomaly_data') and updated_data.get('anomaly_data') != {}:
                            logger.info(
                                f"Approach #{i} WORKED! Data was successfully saved.")
                            success = True
                            break
                        else:
                            logger.warning(
                                f"Approach #{i} returned 200 but data wasn't saved.")
                else:
                    logger.warning(
                        f"Approach #{i} failed: Status {patch_response.status_code}")

                time.sleep(1)

            except Exception as e:
                logger.error(f"Error with approach #{i}: {e}")

        if not success:
            logger.error(
                f"All update approaches failed for Survey ID {survey_id}")
        else:
            logger.info(f"Successfully updated Survey ID {survey_id}")
            logger.info(f"Total items: {sum(combined_counts.values())}")

        time.sleep(DELAY_BETWEEN_REQUESTS)

    logger.info("Process Completed!")


# ----------------------------------------
# PIPELINE ENTRY FUNCTION
# ----------------------------------------
def run(road_ids, logger):

    logger.info("Starting allasset module")

    success = final_count_update(road_ids, logger)

    logger.info("Finished allasset module")
    return success
