import os
import requests
from urllib.parse import urljoin
from typing import Optional, List, Dict
import logging
logger = logging.getLogger(__name__)

BASE_URL = "https://ndd.roadathena.com"
REPORT_API = f"{BASE_URL}/api/surveys/reports"
ROAD_API = f"{BASE_URL}/api/surveys/roads/{{}}"

ROAD_API_PASSWORD = os.getenv("ROAD_API_PASSWORD")

if not ROAD_API_PASSWORD:
    raise RuntimeError(
        "Environment variable 'ROAD_API_PASSWORD' not set"
    )

HEADERS = {"Security-Password": ROAD_API_PASSWORD}

ROADTYPE_FOLDER_MAP = {
    "IRR": "CR",
    "LRR": "CR",
    "IRL": "CL",
    "LRL": "CL",
    "TR": "TR",
    "TL": "TL",
    "SRR": "SR",
    "SRL": "SL",
    "MCW LHS": "MCW",
    "MCW RHS": "MCW",
}
# logger.info("Starting SR JSON generation")

# =========================
# FETCH ROADS
# =========================


def fetch_roads_from_survey(survey_id: int, logger) -> Dict:

    logger.info(f"[DOWNLOAD] Fetching reports for survey_id={survey_id}")
    logger.debug(f"[DOWNLOAD] REPORT_API={REPORT_API}")

    try:
        response = requests.get(REPORT_API, headers=HEADERS, timeout=30)
        response.raise_for_status()
        data = response.json()

        roads = {}

        logger.debug(f"[DOWNLOAD] Response contains {len(data)} items")
        for item in data:
            if item.get("survey_request") == survey_id:
                surveyroad = str(item.get("surveyroad"))
                logger.debug(f"[DOWNLOAD] Adding road {surveyroad}")

                roads[surveyroad] = {
                    "report_id": item.get("id"),
                    "excel_url": urljoin(BASE_URL, item.get("excelreport")),
                }

        logger.info(f"[DOWNLOAD] Found {len(roads)} roads")
        return roads

    except Exception:
        logger.exception("[DOWNLOAD] Failed fetching survey reports")
        raise


# =========================
# FETCH ROAD TYPE
# =========================
def fetch_road_type(road_id: str, survey_id: int, logger) -> Optional[str]:

    logger.debug(f"[DOWNLOAD] Fetching road type for {road_id}")
    try:
        url = ROAD_API.format(road_id)
        logger.debug(f"[DOWNLOAD] Road API URL: {url}")
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        data = resp.json()

        if data.get("survey_request", {}).get("id") != survey_id:
            logger.warning(
                f"[DOWNLOAD] Road {road_id} does not belong to survey {survey_id}"
            )
            return None

        return data.get("road", {}).get("road_type")

    except Exception:
        logger.exception(f"[DOWNLOAD] Failed fetching road type for {road_id}")
        return None


# =========================
# DOWNLOAD & ARRANGE
# =========================
def download_and_arrange(
    roads_dict: Dict,
    survey_id: int,
    survey_root: str,
    logger
) -> Dict:

    logger.info(
        f"[DOWNLOAD] Starting download_and_arrange for {len(roads_dict)} roads")
    download_root = os.path.join(survey_root, "Downloaded_Excels")
    os.makedirs(download_root, exist_ok=True)
    logger.debug(f"[DOWNLOAD] download_root set to {download_root}")

    folder_paths: Dict[str, str] = {}
    folder_files: Dict[str, List[str]] = {}

    success_count = 0
    failed_count = 0

    for road_id, details in roads_dict.items():

        logger.info(f"[DOWNLOAD] Processing road {road_id}")
        logger.debug(f"[DOWNLOAD] details={details}")

        road_type = fetch_road_type(road_id, survey_id, logger)

        if not road_type:
            logger.warning(f"[DOWNLOAD] Skipping {road_id} — no road type")
            failed_count += 1
            continue

        folder_name = ROADTYPE_FOLDER_MAP.get(road_type)

        if not folder_name:
            logger.warning(
                f"[DOWNLOAD] Unknown road type '{road_type}' for road {road_id}'"
            )
            failed_count += 1
            continue

        target_folder = os.path.join(download_root, folder_name)
        os.makedirs(target_folder, exist_ok=True)

        folder_paths[folder_name] = target_folder
        folder_files.setdefault(folder_name, [])

        file_name = f"{road_id}_formatted.xlsx"
        file_path = os.path.join(target_folder, file_name)

        try:
            logger.debug(
                f"[DOWNLOAD] Downloading from {details['excel_url']} to {file_path}")
            response = requests.get(
                details["excel_url"], stream=True, timeout=60
            )
            response.raise_for_status()

            with open(file_path, "wb") as f:
                for chunk in response.iter_content(8192):
                    f.write(chunk)

            folder_files[folder_name].append(file_path)

            logger.info(
                f"[DOWNLOAD] Downloaded {file_name} - {folder_name}"
            )

            success_count += 1

        except Exception:
            logger.exception(f"[DOWNLOAD] Failed download for road {road_id}")
            failed_count += 1

    return {
        "status": "completed",
        "total": len(roads_dict),
        "success": success_count,
        "failed": failed_count,
        "download_root": download_root,
        "folders": folder_paths,
        "files": folder_files,
    }


def rename_downloaded_excels(download_root: str, logger):

    logger.info("[RENAME] Starting rename process")
    logger.debug(f"[RENAME] download_root={download_root}")

    for folder in os.listdir(download_root):

        folder_path = os.path.join(download_root, folder)

        if not os.path.isdir(folder_path):
            continue

        files = [f for f in os.listdir(folder_path) if f.endswith(".xlsx")]

        # -------------------------
        # CL / CR / SR / SL / TR / TL
        # -------------------------
        for file in files:

            road_id = file.split("_")[0]
            old_path = os.path.join(folder_path, file)
            logger.debug(f"[RENAME] preparing rename for {old_path}")

            new_name = None

            if folder == "CL":
                new_name = f"C{road_id} LHS.xlsx"

            elif folder == "CR":
                new_name = f"C{road_id} RHS.xlsx"

            elif folder == "SR":
                new_name = f"SR{road_id} RHS.xlsx"

            elif folder == "SL":
                new_name = f"SL{road_id} LHS.xlsx"

            elif folder == "TR":
                new_name = f"T{road_id} RHS.xlsx"

            elif folder == "TL":
                new_name = f"T{road_id} LHS.xlsx"

            if new_name:
                new_path = os.path.join(folder_path, new_name)

                os.rename(old_path, new_path)

                logger.info(f"[RENAME] {file} - {new_name}")

        # -------------------------
        # MCW Special Logic
        # -------------------------
        if folder == "MCW":

            mcw_files = [f for f in os.listdir(
                folder_path) if f.endswith(".xlsx")]

            lhs = []
            rhs = []

            for file in mcw_files:

                road_id = file.split("_")[0]

                # Detect road side using API
                try:
                    url = ROAD_API.format(road_id)
                    resp = requests.get(url, headers=HEADERS, timeout=15)
                    resp.raise_for_status()
                    data = resp.json()

                    road_type = data.get("road", {}).get("road_type", "")

                    if "LHS" in road_type:
                        lhs.append(file)
                    elif "RHS" in road_type:
                        rhs.append(file)

                except Exception:
                    logger.exception(
                        f"[RENAME] Failed detecting MCW side {file}")

            # -------- rename LHS --------
            for i, file in enumerate(sorted(lhs), start=1):

                old_path = os.path.join(folder_path, file)

                if len(lhs) == 1:
                    new_name = "MCW LHS.xlsx"
                else:
                    new_name = f"MCW LHS Part {i}.xlsx"

                new_path = os.path.join(folder_path, new_name)
                os.rename(old_path, new_path)

                logger.info(f"[RENAME] {file} - {new_name}")

            # -------- rename RHS --------
            for i, file in enumerate(sorted(rhs), start=1):

                old_path = os.path.join(folder_path, file)

                if len(rhs) == 1:
                    new_name = "MCW RHS.xlsx"
                else:
                    new_name = f"MCW RHS Part {i}.xlsx"

                new_path = os.path.join(folder_path, new_name)
                os.rename(old_path, new_path)

                logger.info(f"[RENAME] {file} - {new_name}")

    logger.info("[RENAME] Rename process completed")


# =========================
# RUN ENTRY
# =========================
def run(
    survey_id: int,
    selected_road_ids: Optional[List[str]],
    survey_root: str,
    logger
) -> Dict:

    logger.info(f"[DOWNLOAD] Stage started for survey {survey_id}")
    logger.debug(
        f"[DOWNLOAD] survey_root={survey_root}, selected={selected_road_ids}")

    roads = fetch_roads_from_survey(survey_id, logger)

    if selected_road_ids:
        roads = {
            rid: roads[rid]
            for rid in selected_road_ids
            if rid in roads
        }

    if not roads:
        logger.error("[DOWNLOAD] No valid roads found")
        return {"status": "error", "message": "No roads found"}

    result = download_and_arrange(
        roads_dict=roads,
        survey_id=survey_id,
        survey_root=survey_root,
        logger=logger,
    )

    rename_downloaded_excels(
        download_root=result["download_root"],
        logger=logger
    )

    logger.info("[DOWNLOAD] Stage completed")

    return result
