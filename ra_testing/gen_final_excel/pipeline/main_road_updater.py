import requests
import time
import logging
import os

logger = logging.getLogger(__name__)

POINT = "ndd"
ROAD_API_PASSWORD = os.getenv("ROAD_API_PASSWORD")


def run(survey_id, logger):

    logger.info("Starting road segment update")

    try:
        api_url = f"https://{POINT}.roadathena.com/api/surveys/{survey_id}"

        response = requests.get(
            api_url,
            headers={"Security-Password": ROAD_API_PASSWORD},
            timeout=20
        )

        if response.status_code != 200:
            logger.error("Failed to fetch survey data")
            return False

        data = response.json()

        roads = data.get("roads", [])
        road_ids = [road.get("id") for road in roads if "id" in road]

        logger.info(f"Found {len(road_ids)} road segments")

        for road_id in road_ids:

            url = f"https://{POINT}.roadathena.com/api/surveys/roads/{road_id}"

            payload = {
                "final_report_status": True
            }

            try:

                response = requests.patch(
                    url,
                    headers={"Security-Password": ROAD_API_PASSWORD},
                    json=payload,
                    timeout=20
                )

                if response.status_code == 200:
                    logger.info(f"Updated road_id {road_id}")

                else:
                    logger.warning(
                        f"Failed updating road_id {road_id} : {response.text}"
                    )

            except Exception as e:
                logger.error(f"Error updating road_id {road_id} : {e}")

            time.sleep(0.2)

        logger.info("Road segment update completed")

        return True

    except Exception as e:

        logger.exception("Road update failed")
        return False
