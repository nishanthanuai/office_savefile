# fetch_gpx.py

import os
import requests
import logging
import time
from typing import List, Dict
from typing import Optional

API_BASE_URL = "https://ndd.roadathena.com/api/surveys/roads/"
FILE_BASE_URL = "https://ndd.roadathena.com"

logger = logging.getLogger(__name__)


class GPXFetchError(Exception):
    """Custom exception for GPX fetching errors."""

    pass


def fetch_single_gpx(road_id: int, output_dir: str, headers: Dict[str, str]) -> str:
    """
    Fetch a single GPX file.
    Returns the saved file path.
    Raises GPXFetchError on failure.
    """

    logger.info(f"Fetching GPX for road_id={road_id}")

    api_url = f"{API_BASE_URL}{road_id}"

    max_retries = 3
    retry_delay = 5  # seconds

    for attempt in range(max_retries):
        try:
            response = requests.get(api_url, headers=headers, timeout=30)
            response.raise_for_status()
            road_data = response.json()

            gpx_path = road_data.get("gpx_file")

            if not gpx_path:
                logger.warning(f"No GPX file found for road_id={road_id}")
                raise GPXFetchError(f"No GPX file for road {road_id}")

            gpx_url = f"{FILE_BASE_URL}{gpx_path}"
            gpx_file_path = os.path.join(output_dir, f"road_{road_id}.gpx")

            if os.path.exists(gpx_file_path):
                logger.info(f"GPX already exists for road_id={road_id}")
                return gpx_file_path

            gpx_response = requests.get(gpx_url, headers=headers, timeout=60)
            gpx_response.raise_for_status()

            with open(gpx_file_path, "wb") as f:
                f.write(gpx_response.content)

            logger.info(f"GPX saved: {gpx_file_path}")
            return gpx_file_path

        except (requests.RequestException, ConnectionResetError) as e:
            if attempt < max_retries - 1:
                wait_time = retry_delay * (2 ** attempt)
                logger.warning(
                    f"Attempt {attempt + 1} failed for road_id={road_id}: {e}. "
                    f"Retrying in {wait_time}s..."
                )
                time.sleep(wait_time)
            else:
                logger.exception(
                    f"All {max_retries} attempts failed for road_id={road_id}"
                )
                raise GPXFetchError(f"Failed fetching GPX for road {road_id}") from e


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
        output_dir: Directory where GPX files should be stored
        security_password: API security password

    Returns:
        List of saved GPX file paths.
    """

    logger.info("Starting GPX fetch pipeline")

    os.makedirs(output_dir, exist_ok=True)

    headers = {"Security-Password": security_password}

    saved_files = []

    for road_id in road_ids:
        try:
            path = fetch_single_gpx(road_id, output_dir, headers)
            saved_files.append(path)
        except GPXFetchError as e:
            logger.error(str(e))
            continue

    logger.info(f"Completed GPX fetch | total_success={len(saved_files)}")

    return saved_files
