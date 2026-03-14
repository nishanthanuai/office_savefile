# fetch_json.py

import os
import requests
import logging
from typing import Optional
from typing import List, Dict

logger = logging.getLogger(__name__)

API_BASE_URL = "https://ndd.roadathena.com/api/surveys/roads/"
FILE_BASE_URL = "https://ndd.roadathena.com"


class JSONFetchError(Exception):
    """Custom exception for furniture JSON fetching errors."""
    pass


def fetch_single_json(
    road_id: int,
    output_dir: str,
    headers: Dict[str, str]
) -> str:
    """
    Fetch a single furniture JSON file.
    Returns the saved file path.
    Raises JSONFetchError on failure.
    """

    logger.info(f"Fetching furniture JSON for road_id={road_id}")

    api_url = f"{API_BASE_URL}{road_id}"

    try:
        response = requests.get(api_url, headers=headers, timeout=30)
        response.raise_for_status()
        road_data = response.json()

        furniture_json_path = road_data.get("furniture_json")

        if not furniture_json_path:
            logger.warning(f"No furniture_json found for road_id={road_id}")
            raise JSONFetchError(f"No furniture_json for road {road_id}")

        json_url = f"{FILE_BASE_URL}{furniture_json_path}"
        output_file = os.path.join(output_dir, f"road_{road_id}.json")

        if os.path.exists(output_file):
            logger.info(f"JSON already exists for road_id={road_id}")
            return output_file

        json_response = requests.get(json_url, headers=headers, timeout=60)
        json_response.raise_for_status()

        with open(output_file, "wb") as f:
            f.write(json_response.content)

        logger.info(f"Furniture JSON saved: {output_file}")
        return output_file

    except requests.RequestException as e:
        logger.exception(
            f"Network error while fetching JSON for road_id={road_id}"
        )
        raise JSONFetchError(f"Failed fetching JSON for road {road_id}") from e


def run(
    road_ids: List[int],
    output_dir: str,
    security_password: str,
    logger: Optional[logging.Logger] = None,
) -> List[str]:
    if logger is None:
        logger = logging.getLogger(__name__)
    """
    Master entry function for this module.

    Args:
        road_ids: List of road IDs
        output_dir: Directory where JSON files should be stored
        security_password: API security password

    Returns:
        List of saved JSON file paths.
    """

    logger.info("Starting furniture JSON fetch")

    os.makedirs(output_dir, exist_ok=True)

    headers = {
        "Security-Password": security_password
    }

    saved_files = []

    for road_id in road_ids:
        try:
            path = fetch_single_json(road_id, output_dir, headers)
            saved_files.append(path)
        except JSONFetchError as e:
            logger.error(str(e))
            continue

    logger.info(
        f"Completed furniture JSON fetch | total_success={len(saved_files)}"
    )

    return saved_files
