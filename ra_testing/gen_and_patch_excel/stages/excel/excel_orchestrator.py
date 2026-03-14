# """
# excel_orchestrator.py

# Central Excel stage orchestrator.
# Calls:
#     - excel2.run()
#     - excel3.run()
#     - excel4.run()
#     - excel5.run()

# No CLI.
# No input().
# Designed for master_pipeline control.
# """

# from __future__ import annotations
# import logging
# import os
# from typing import List, Optional, Dict, Any

# # Import run functions directly
# from excel2 import run as excel2_run
# from excel3 import run as excel3_run   # adjust name if file is excel31
# from excel4 import run as excel4_run
# from excel5 import run as excel5_run

# # road_id: Optional[List[int]]


# def fetch_road_data(road_id: int, logger: logging.Logger) -> Optional[Dict[str, Any]]:
#     api_url = f"https://ndd.roadathena.com/api/surveys/roads/{road_id}"

#     password = os.getenv("ROAD_API_PASSWORD", "admin@123")
#     if not password:
#         logger.error("ROAD_API_PASSWORD environment variable not set")
#         return None

#     try:
#         response = requests.get(
#             api_url,
#             headers={"Security-Password": password},
#             timeout=30
#         )

#         if response.status_code == 200:
#             logger.info("Road API fetch success | road_id=%s", road_id)
#             return response.json()

#         logger.error(
#             "Road API failed | road_id=%s | status=%s",
#             road_id,
#             response.status_code
#         )
#         return None

#     except Exception as e:
#         logger.exception("Road API exception | road_id=%s", road_id)
#         return None


# def run(
#     road_ids: Optional[List[int]],
#     json_dir: str,
#     gpx_dir: str,
#     output_folder: str,
#     logger: Optional[logging.Logger] = None,
# ) -> Dict[str, Any]:

#     logger = logger or logging.getLogger(__name__)

#     # -------------------------------------------------
#     # Normalize input (support single int)
#     # -------------------------------------------------
#     if isinstance(road_ids, int):
#         road_ids = [road_ids]

#     if not road_ids:
#         logger.warning("No road IDs provided to excel_orchestrator.")
#         return {
#             "processed": [],
#             "failed": [],
#             "total": 0,
#         }

#     processed = []
#     failed = []

#     total_roads = len(road_ids)

#     for index, road_id in enumerate(road_ids, start=1):

#         logger.info(
#             "Excel Stage | Road %s (%s/%s)",
#             road_id,
#             index,
#             total_roads,
#         )

#         road_json_path = os.path.join(json_dir, f"road_{road_id}.json")
#         gpx_json_path = os.path.join(gpx_dir, f"road_{road_id}.json")
#         road_data = fetch_road_data(road_id, logger)
#         try:
#             # 1️⃣ Assets + Anomalies
#             result2 = excel2_run(
#                 road_json_path,
#                 output_folder,
#                 road_id
#             )

#             # 2️⃣ Furniture Chainage

#             result3 = excel3_run(
#                 road_json_path,
#                 gpx_json_path,
#                 output_folder,
#                 road_id,
#                 road_data,
#                 logger=logger
#             )

#             # 3️⃣ Encroachment Signs
#             result4 = excel4_run(
#                 road_json_path,
#                 output_folder,
#                 road_id
#             )

#             # 4️⃣ Damaged Signs
#             result5 = excel5_run(
#                 road_json_path,
#                 output_folder,
#                 road_id
#             )
#             logger.info("excel5 result: %s", result5)

#             processed.append({
#                 "road_id": road_id,
#                 "excel2": result2,
#                 "excel3": result3,
#                 "excel4": result4,
#                 "excel5": result5,
#             })

#         except Exception as exc:
#             logger.exception(
#                 "Excel stage failed | road_id=%s | error=%s",
#                 road_id,
#                 exc,
#             )
#             failed.append(road_id)

#     summary = {
#         "processed": processed,
#         "failed": failed,
#         "total": total_roads,
#     }

#     logger.info("Excel Orchestrator Completed | Summary=%s", summary)

#     return summary
"""
excel_orchestrator.py

Central Excel stage orchestrator.
Calls:
    - excel2.run()
    - excel3.run()
    - excel4.run()
    - excel5.run()

No CLI.
No input().
Designed for master_pipeline control.
"""

from __future__ import annotations

import logging
import os
import requests
from typing import List, Optional, Dict, Any

from .excel2 import run as excel2_run
from .excel6 import run as excel3_run
from .excel4 import run as excel4_run
from .excel5 import run as excel5_run


# ============================================================
# Road API Fetch (Moved from excel3 → centralized here)
# ============================================================


def fetch_road_data(road_id: int, logger: logging.Logger) -> Optional[Dict[str, Any]]:
    """
    Fetch road metadata from API.
    """

    api_url = f"https://ndd.roadathena.com/api/surveys/roads/{road_id}"
    password = os.getenv("ROAD_API_PASSWORD")

    if not password:
        logger.error("ROAD_API_PASSWORD environment variable not set")
        return None

    try:
        response = requests.get(
            api_url,
            headers={"Security-Password": password},
            timeout=30,
        )
        response.raise_for_status()

        if response.status_code == 200:
            logger.info("Road API fetch success | road_id=%s", road_id)
            return response.json()

        logger.error(
            "Road API failed | road_id=%s | status=%s",
            road_id,
            response.status_code,
        )
        return None

    except Exception:
        logger.exception("Road API exception | road_id=%s", road_id)
        return None


# ============================================================
# Main Orchestrator
# ============================================================


def run(
    road_ids: Optional[List[int]],
    json_dir: str,
    gpx_dir: str,
    output_folder: str,
    logger: Optional[logging.Logger] = None,
) -> Dict[str, Any]:
    """
    Execute full Excel pipeline for given road IDs.
    """

    logger = logger or logging.getLogger(__name__)

    # Normalize input (support single int)
    if isinstance(road_ids, int):
        road_ids = [road_ids]

    if not road_ids:
        logger.warning("No road IDs provided to excel_orchestrator.")
        return {
            "processed": [],
            "failed": [],
            "total": 0,
        }

    processed = []
    failed = []
    total_roads = len(road_ids)

    for index, road_id in enumerate(road_ids, start=1):

        logger.info(
            "Excel Stage | Road %s (%s/%s)",
            road_id,
            index,
            total_roads,
        )

        road_json_path = os.path.join(json_dir, f"road_{road_id}.json")
        gpx_json_path = os.path.join(gpx_dir, f"road_{road_id}.json")

        try:
            # -------------------------------------------------
            # Fetch Road Data (Required for excel3)
            # -------------------------------------------------
            road_data = fetch_road_data(road_id, logger)

            if not road_data:
                logger.error(
                    "Skipping road %s due to missing road_data.",
                    road_id,
                )
                failed.append(road_id)
                continue

            # -------------------------------------------------
            # 1️⃣ Assets + Anomalies
            # -------------------------------------------------
            logger.info("Calling excel2...")
            result2 = excel2_run(road_json_path, output_folder, road_id, road_data)
            logger.info("Excel2 completed successfully.")

            # -------------------------------------------------
            # 2️⃣ Furniture Chainage (Uses GPX + road_data)
            # -------------------------------------------------
            logger.info("Calling excel3...")
            result3 = excel3_run(
                road_json_path,
                gpx_json_path,
                output_folder,
                road_id,
                road_data,
                logger=logger,
            )
            logger.info("Excel3 completed successfully.")

            # -------------------------------------------------
            # 3️⃣ Encroachment Signs
            # -------------------------------------------------
            logger.info("Calling excel4...")
            result4 = excel4_run(road_json_path, output_folder, road_id, road_data)
            logger.info("Excel4 completed successfully.")

            # -------------------------------------------------
            # 4️⃣ Damaged Signs
            # -------------------------------------------------
            logger.info("Calling excel5...")
            result5 = excel5_run(road_json_path, output_folder, road_id, road_data)
            logger.info("Excel5 completed successfully.")

            processed.append(
                {
                    "road_id": road_id,
                    "excel2": result2,
                    "excel3": result3,
                    "excel4": result4,
                    "excel5": result5,
                }
            )

        except Exception as exc:
            logger.exception(
                "Excel stage failed | road_id=%s | error=%s",
                road_id,
                exc,
            )
            failed.append(road_id)

    summary = {
        "processed": processed,
        "failed": failed,
        "total": total_roads,
    }

    logger.info("Excel Orchestrator Completed | Summary=%s", summary)

    return summary
