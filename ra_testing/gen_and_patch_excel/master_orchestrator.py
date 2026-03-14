from __future__ import annotations

import os
import sys
import logging
from typing import List, Optional, Dict, Any, Union

# --- Fix Python Path for module imports ---
# This allows Django (running from the project root) to import internal modules
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)
# ------------------------------------------

# import ingest_all_logs
from stages.fetch import fetch_json, fetch_gpx
from stages.process import (
    json_cleaner,
    category,
    side_check,
    gpx_converter,
    json_patch4,
)
from stages.excel import excel_orchestrator, Excel_patch
# from ingest_all_logs import ingest_run
from stages import count_validator

from core.logging_manager import (
    setup_master_logger,
    setup_road_logger,
    write_stage_summary,
    write_run_summary,
)
import requests
import shutil

BASE_URL = "https://ndd.roadathena.com/api"


def cleanup_road_artifacts(road_dir: str):
    """
    Delete fetch/, process/, excel/ folders.
    Keep logs and run_summary.
    """
    for item in os.listdir(road_dir):
        item_path = os.path.join(road_dir, item)

        # Keep logs only
        if item in ("logs", "excel", "fetch", "process"):
            continue

        if os.path.isdir(item_path):
            shutil.rmtree(item_path, ignore_errors=True)
        else:
            try:
                os.remove(item_path)
            except Exception:
                pass


def cleanup_old_runs(base_runs_dir: str, max_runs: int = 100):
    """
    Keep only the latest `max_runs` run folders.
    For older runs:
        - Keep master.log
        - Keep run_summary.json
        - Delete everything else
    """
    try:
        if not os.path.exists(base_runs_dir):
            return

        # Get only run directories
        all_runs = [
            os.path.join(base_runs_dir, d)
            for d in os.listdir(base_runs_dir)
            if os.path.isdir(os.path.join(base_runs_dir, d))
        ]

        # Sort by modification time (newest last)
        all_runs.sort(key=lambda x: os.path.getmtime(x))

        if len(all_runs) <= max_runs:
            return  # Nothing to clean

        runs_to_trim = all_runs[:-max_runs]

        for run_path in runs_to_trim:
            for item in os.listdir(run_path):
                item_path = os.path.join(run_path, item)

                # Keep only master.log and run_summary.json
                if item in ("master.log", "run_summary.json"):
                    continue

                if os.path.isdir(item_path):
                    shutil.rmtree(item_path, ignore_errors=True)
                else:
                    try:
                        os.remove(item_path)
                    except Exception:
                        pass

    except Exception as e:
        print(f"[WARNING] Old run cleanup failed: {e}")


def fetch_road_ids_from_survey(survey_id: int, security_password: str):
    url = f"{BASE_URL}/surveys/{survey_id}"
    response = requests.get(
        url, headers={"Security-Password": security_password}, timeout=30)
    response.raise_for_status()

    data = response.json()
    roads = data.get("roads", [])

    # Fetch detailed road info for classification
    detailed_roads = []
    for r in roads:
        road_id = r.get("id")
        if not road_id:
            continue

        # Fetch full road details
        road_detail = requests.get(
            f"{BASE_URL}/surveys/roads/{road_id}",
            headers={"Security-Password": security_password},
            timeout=30
        ).json().get("road", {})

        # Use road_type for classification (more reliable than name)
        road_type = road_detail.get("road_type", "").upper()
        detailed_roads.append(
            {"id": road_id, "road_type": road_type, "name": road_detail.get("name", "")})

    return detailed_roads


SERVICE_KEYWORDS = {
    "SRR", "SRL",
    "IRR", "IRL",
    "LRR", "LRL",
    "TR", "TL"
}


def classify_roads_by_name(roads: List[Dict[str, Any]]):
    mcw_roads, service_roads, unknown_roads = [], [], []
    SERVICE_TYPES = {"SRR", "SRL", "IRR", "IRL", "LRR", "LRL", "TR", "TL"}

    for road in roads:
        road_id = road["id"]
        road_type = road.get("road_type", "").upper().strip()

        if not road_type:
            unknown_roads.append(
                {"road_id": road_id, "name": road.get("name", "")})
            continue

        if "MCW" in road_type:
            mcw_roads.append(road_id)
        elif any(road_type.startswith(s) for s in SERVICE_TYPES):
            service_roads.append(road_id)
        else:
            unknown_roads.append(
                {"road_id": road_id, "road_type": road_type, "name": road.get("name", "")})

    return mcw_roads, service_roads, unknown_roads


def run_from_survey(
    survey_id: int,
    security_password: str,
    run_stages: Optional[List[str]] = None, progress_callback: Optional[callable] = None,
):
    logging.getLogger(__name__).info(
        "Fetching roads for Survey %s",
        survey_id
    )

    road_ids = fetch_road_ids_from_survey(
        survey_id,
        security_password
    )
    print(f"[DEBUG] Fetched road IDs for survey {survey_id}: {road_ids}")
    logging.getLogger(__name__).info(f"[DEBUG] Fetched road IDs: {road_ids}")

    logging.getLogger(__name__).info(
        "Fetching roads for Survey %s",
        survey_id
    )

    mcw_roads, service_roads, unknown_roads = classify_roads_by_name(
        road_ids,
    )
    # --- DEBUG PRINT ---
    print(f"[DEBUG] MCW Roads: {mcw_roads}")
    print(f"[DEBUG] Service Roads: {service_roads}")
    print(f"[DEBUG] Unknown Roads: {unknown_roads}")

    logging.getLogger(__name__).info(f"[DEBUG] MCW Roads: {mcw_roads}")
    logging.getLogger(__name__).info(f"[DEBUG] Service Roads: {service_roads}")
    logging.getLogger(__name__).info(f"[DEBUG] Unknown Roads: {unknown_roads}")

    logging.getLogger(__name__).info(
        "========= AUTO CLASSIFICATION ========="
    )
    logging.getLogger(__name__).info(
        "MCW Roads (%s): %s",
        len(mcw_roads),
        mcw_roads
    )
    logging.getLogger(__name__).info(
        "Service Roads (%s): %s",
        len(service_roads),
        service_roads
    )

    full_summary = {}

    # Run MCW batch
    if mcw_roads:
        print(f"[DEBUG] Running MCW batch for roads: {mcw_roads}")
        logging.getLogger(__name__).info(
            "Running MCW Roads Pipeline"
        )
        full_summary["mcw"] = run(
            road_ids=mcw_roads,
            road_type="mcw",
            security_password=security_password,
            run_stages=run_stages, progress_callback=progress_callback,
        )

    # Run Service batch
    if service_roads:
        print(f"[DEBUG] Running Service batch for roads: {service_roads}")
        logging.getLogger(__name__).info(
            "Running Service Roads Pipeline"
        )
        full_summary["service"] = run(
            road_ids=service_roads,
            road_type="service",
            security_password=security_password,
            run_stages=run_stages, progress_callback=progress_callback,
        )

    return full_summary
# ---------------------------------------------------------
# Validate Road Type
# ---------------------------------------------------------


def _parse_ids(value: Union[str, int, List[int]]) -> Union[int, List[int]]:
    """Utility: turn a string/number into int or list of ints.

    - Comma-separated strings become ``List[int]``
    - A single numeric string or int is returned as ``int``
    """
    if isinstance(value, list):
        return value
    if isinstance(value, int):
        return value
    text = str(value).strip()
    if "," in text:
        parts = [p.strip() for p in text.split(",") if p.strip()]
        return [int(p) for p in parts]
    return int(text)


def _run_for_road_list(
    road_ids: List[int],
    security_password: str,
    run_stages: Optional[List[str]] = None,
    progress_callback: Optional[callable] = None,
) -> Dict[str, Any]:
    """Process a list of road IDs (no survey).

    This helper will classify each road by type using the API and then dispatch
    to ``run`` in batches by type (mcw/service).  The behaviour mirrors the
    survey-based classification used in ``run_from_survey``.
    """
    if not road_ids:
        return {"error": "No road IDs provided"}

    logger = logging.getLogger(__name__)
    logger.info("Received %s road ids for direct execution", road_ids)

    mcw_roads: List[int] = []
    service_roads: List[int] = []
    unknown: List[int] = []

    for rid in road_ids:
        url = f"{BASE_URL}/surveys/roads/{rid}"
        resp = requests.get(
            url,
            headers={"Security-Password": security_password},
            timeout=10,
        )
        if resp.status_code != 200:
            unknown.append(rid)
            continue
        rd = resp.json().get("road", {})
        rtype = rd.get("road_type", "").upper()
        if "MCW" in rtype:
            mcw_roads.append(rid)
        else:
            service_roads.append(rid)

    summary: Dict[str, Any] = {}
    if mcw_roads:
        summary["mcw"] = run(
            road_ids=mcw_roads,
            road_type="mcw",
            security_password=security_password,
            run_stages=run_stages,
            progress_callback=progress_callback,
        )
    if service_roads:
        summary["service"] = run(
            road_ids=service_roads,
            road_type="service",
            security_password=security_password,
            run_stages=run_stages,
            progress_callback=progress_callback,
        )
    if unknown:
        logger.warning(
            "The following road ids could not be fetched: %s", unknown)
        summary["unknown"] = unknown

    return summary


def execute(
    input_id: Union[str, int, List[int]],
    security_password: str,
    run_stages: Optional[List[str]] = None,
    progress_callback: Optional[callable] = None,
):
    """
    Smart entrypoint:

    * Accepts **either** a survey id (single) **or** one/multiple road ids.
    * Surveys must be a single numeric value; road ids can be comma-separated.
    * When a comma-separated string or list is provided we treat it as
      one or more roads and **do not** attempt survey lookup.
    """

    logger = logging.getLogger(__name__)

    # normalize to int or list of ints
    parsed = _parse_ids(input_id)

    # if we ended up with a list, treat as roads directly
    if isinstance(parsed, list):
        return _run_for_road_list(
            road_ids=parsed,
            security_password=security_password,
            run_stages=run_stages,
            progress_callback=progress_callback,
        )

    # otherwise `parsed` is a single id
    input_id = parsed

    # ---- Try Survey ----
    survey_url = f"{BASE_URL}/surveys/{input_id}"
    survey_resp = requests.get(
        survey_url,
        headers={"Security-Password": security_password},
        timeout=10
    )

    if survey_resp.status_code == 200:
        logger.info("Detected input %s as SURVEY", input_id)
        return run_from_survey(
            survey_id=input_id,
            security_password=security_password,
            run_stages=run_stages,
            progress_callback=progress_callback,
        )

    # ---- Try Road ----
    road_url = f"{BASE_URL}/surveys/roads/{input_id}"
    road_resp = requests.get(
        road_url,
        headers={"Security-Password": security_password},
        timeout=10
    )

    if road_resp.status_code == 200:
        logger.info("Detected input %s as ROAD", input_id)

        road_data = road_resp.json().get("road", {})
        road_type_raw = road_data.get("road_type", "").upper()

        if "MCW" in road_type_raw:
            road_type = "mcw"
        else:
            road_type = "service"

        return run(
            road_ids=input_id,
            road_type=road_type,
            security_password=security_password,
            run_stages=run_stages,
            progress_callback=progress_callback,
        )

    raise ValueError(f"Input ID {input_id} is neither valid survey nor road")


def run(
    road_ids: Union[int, List[int], str],
    road_type: str,
    security_password: str,
    run_stages: Optional[List[str]] = None, progress_callback: Optional[callable] = None,
) -> Dict[str, Any]:

    # ---------------------------------------------------------
    # Normalize Input
    # ---------------------------------------------------------
    # allow strings with commas to be passed directly
    road_ids = _parse_ids(road_ids)
    if isinstance(road_ids, int):
        road_ids = [road_ids]

    if not road_ids:
        return {"error": "No road IDs provided"}
    road_type = road_type.lower().strip()

    VALID_ROAD_TYPES = {"mcw", "service"}

    if road_type not in VALID_ROAD_TYPES:
        raise ValueError(
            f"Invalid road_type '{road_type}'. "
            f"Must be one of {VALID_ROAD_TYPES}"
        )

    run_stages = run_stages or ["fetch", "process", "excel"]

    # ---------------------------------------------------------
    # Setup Master Logging (ONLY HERE)
    # ---------------------------------------------------------
    master_logger, run_dir = setup_master_logger()

    master_logger.info(
        "Master Pipeline Started | road_type=%s | roads=%s",
        road_type,
        road_ids,
    )

    summary: Dict[str, Any] = {
        "road_type": road_type,
        "stages_run": run_stages,
        "results": {},
        "generated_excels": [],
    }

    # ==========================================================
    # PER ROAD LOOP (FULLY ISOLATED)
    # ==========================================================
    for road_id in road_ids:

        master_logger.info(
            "Processing road_id=%s, road_type=%s", road_id, road_type)
        if progress_callback:
            progress_callback(f"arambh hua {road_id}")

        road_logger, road_dir = setup_road_logger(run_dir, road_id)

        # -----------------------------------------------------
        # Create Stage Root Directories
        # -----------------------------------------------------
        road_fetch_dir = os.path.join(road_dir, "fetch")
        road_process_dir = os.path.join(road_dir, "process")
        road_excel_dir = os.path.join(road_dir, "excel")

        os.makedirs(road_fetch_dir, exist_ok=True)
        os.makedirs(road_process_dir, exist_ok=True)
        os.makedirs(road_excel_dir, exist_ok=True)

        road_summary: Dict[str, Any] = {}

        # =====================================================
        # FETCH STAGE
        # =====================================================
        if "fetch" in run_stages:

            json_raw_dir = os.path.join(road_fetch_dir, "json_raw")
            gpx_raw_dir = os.path.join(road_fetch_dir, "gpx_raw")

            os.makedirs(json_raw_dir, exist_ok=True)
            os.makedirs(gpx_raw_dir, exist_ok=True)

            fetch_result = {
                "gpx": fetch_gpx.run(
                    [road_id],
                    gpx_raw_dir,
                    security_password, logger=road_logger
                ),
                "json": fetch_json.run(
                    [road_id],
                    json_raw_dir,
                    security_password, logger=road_logger
                )
            }

            write_stage_summary(
                road_dir,
                "fetch",
                "completed",
                fetch_result
            )

            road_summary["fetch"] = fetch_result

        # =====================================================
        # PROCESS STAGE
        # =====================================================
        # =====================================================
# PROCESS STAGE
# =====================================================
        if "process" in run_stages:

            json_raw_dir = os.path.join(road_fetch_dir, "json_raw")
            gpx_raw_dir = os.path.join(road_fetch_dir, "gpx_raw")

            json_cleaned_dir = os.path.join(road_process_dir, "json_cleaned")
            json_flags_dir = os.path.join(road_process_dir, "json_flags")
            categorized_dir = os.path.join(
                road_process_dir, "json_categorized")
            gpx_converted_dir = os.path.join(road_process_dir, "gpx_converted")
            side_check_dir = os.path.join(road_process_dir, "side_checked")

            os.makedirs(json_cleaned_dir, exist_ok=True)
            os.makedirs(json_flags_dir, exist_ok=True)
            os.makedirs(categorized_dir, exist_ok=True)
            os.makedirs(gpx_converted_dir, exist_ok=True)
            os.makedirs(side_check_dir, exist_ok=True)

            # ---- Run Core Process Steps ----
            cleaner_result = json_cleaner.run(
                [road_id],
                json_raw_dir,
                json_cleaned_dir,
                json_flags_dir,
                logger=road_logger
            )

            gpx_result = gpx_converter.run(
                [road_id],
                gpx_raw_dir,
                gpx_converted_dir,
                logger=road_logger
            )

            category_result = category.run(
                [road_id],
                json_cleaned_dir,
                categorized_dir,
                logger=road_logger
            )

            side_result = side_check.run(
                [road_id],
                road_type,
                categorized_dir,
                side_check_dir,
                logger=road_logger
            )

            # ---- PATCH ONLY AFTER SIDE CHECK SUCCESS ----
            patch_result = json_patch4.run(
                road_ids=[road_id],
                road_type=road_type,
                json_root=side_check_dir,
                security_password=security_password,
                logger=road_logger
            )

            process_result = {
                "json_cleaner": cleaner_result,
                "gpx_converter": gpx_result,
                "category": category_result,
                "side_check": side_result,
                "json_patch": patch_result,
            }

            write_stage_summary(
                road_dir,
                "process",
                "completed",
                process_result
            )

            road_summary["process"] = process_result

        # =====================================================
        # EXCEL STAGE
        # =====================================================
        # =====================================================
# EXCEL STAGE
# =====================================================
        if "excel" in run_stages:

            side_check_dir = os.path.join(road_process_dir, "side_checked")
            gpx_converted_dir = os.path.join(road_process_dir, "gpx_converted")

            # ---- Step 1: Generate Excel ----
            # ---- Step 1: Generate Excel ----
            excel_result = excel_orchestrator.run(
                road_ids=[road_id],
                json_dir=side_check_dir,
                gpx_dir=gpx_converted_dir,
                output_folder=road_excel_dir,
                logger=road_logger
            )

            excel_path = os.path.join(
                road_excel_dir,
                f"{road_id}_formatted.xlsx"
            )

            # -----------------------------
            # COUNT VALIDATION STAGE
            # -----------------------------
            side_checked_json_path = os.path.join(
                road_process_dir,
                "side_checked",
                f"road_{road_id}.json"
            )

            validation_result = count_validator.run(
                road_id=road_id,
                json_path=side_checked_json_path,
                excel_path=excel_path,
            )

            road_summary["validation"] = validation_result

            # ---------------------------------
            # PATCH ONLY IF VALIDATION MATCHES
            # ---------------------------------
            if validation_result["status"] == "MATCH":

                excel_patch_result = Excel_patch.run(
                    road_id=road_id,
                    excel_root=road_excel_dir,
                    security_password=security_password,
                    logger=road_logger
                )

                road_summary["excel"] = {
                    "generation": excel_result,
                    "validation": validation_result,
                    "patch": excel_patch_result
                }

                master_logger.info(
                    "Validation SUCCESS for road_id=%s",
                    road_id
                )
                if progress_callback:
                    progress_callback(
                        f" Congratulations! JSON count and Excel count matched for road {road_id}"
                    )

            else:

                road_summary["excel"] = {
                    "generation": excel_result,
                    "validation": validation_result,
                    "patch": {
                        "patched": False,
                        "reason": "Validation failed"
                    }
                }

                master_logger.warning(
                    "Validation FAILED for road_id=%s | Details=%s",
                    road_id,
                    validation_result
                )

            summary["generated_excels"].append({
                "road_id": road_id,
                "file_path": excel_path
            })
        if progress_callback:
            progress_callback(f"khatam ta ta bye bye")

            # if progress_callback:
            #     progress_callback(f"khatam ta ta bye bye")

# ------------------------------------------
# Safe Cleanup Logic
# ------------------------------------------
        json_patch_status = road_summary.get(
            "process", {}).get("json_patch", {})
        excel_patch_status = road_summary.get(
            "excel", {}).get("patch", {})

        json_success = (
            road_id in json_patch_status.get("patched", []) and
            road_id not in json_patch_status.get("failed", [])
        )

        excel_success = excel_patch_status.get("patched", False) is True
        validation_success = (
            road_summary.get("excel", {})
            .get("validation", {})
            .get("status") == "MATCH"
        )

        if json_success and excel_success and validation_success:
            try:
                cleanup_road_artifacts(road_dir)
                master_logger.info(
                    "Cleanup completed for road_id=%s", road_id
                )
            except Exception as e:
                master_logger.error(
                    "Cleanup failed for road_id=%s | error=%s",
                    road_id,
                    str(e)
                )
        else:
            master_logger.warning(
                "Skipping cleanup for road_id=%s | json_success=%s | excel_success=%s",
                road_id,
                json_success,
                excel_success
            )

        summary["results"][road_id] = road_summary

    # ==========================================================
    # FINAL RUN SUMMARY (CRITICAL FOR RAG)
    # ==========================================================
    write_run_summary(run_dir, summary)

    # try:
    #     ingest_run(run_dir)
    #     master_logger.info("RAG ingestion completed successfully.")
    # except Exception as e:
    #     master_logger.error("RAG ingestion failed: %s", str(e))

    # master_logger.info("Master Pipeline Completed")

    return summary


# ---------------------------------------------------------
# CLI TEST MODE
# ---------------------------------------------------------
if __name__ == "__main__":

    raw = input(
        "Enter SURVEY ID (single) or ROAD ID(s) (comma-separated): "
    ).strip()

    result = execute(
        input_id=raw,
        security_password=os.getenv("ROAD_API_PASSWORD")
    )

    print("\nFINAL SUMMARY:\n")
    print(result)
