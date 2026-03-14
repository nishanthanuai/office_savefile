import os
import sys

# --- Fix Python Path for module imports ---
# This allows Django and standalone execution to import internal pipeline modules consistently
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)



import requests
from pipeline.logging_manager import LoggingManager
from concurrent.futures import ThreadPoolExecutor, as_completed
import os
import re
# import shutil

from pipeline import (
    D_A,
    MCW_final,
    SL_final,
    SR_final,
    CL_final,
    CR_final,
    TL_final,
    TR_final,
    final_colur_format1,
    dp1,
    main_road_updater,
    allasset, validator, xlsx, finalvalidator
)

import logging
# from dp1 import get_project_name_from_roads

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(name)s | %(levelname)s | %(message)s"
)
logger = logging.getLogger("MASTER_RUNNER")


def get_project_name_from_roads(survey_id, logger):

    try:
        base = "https://ndd.roadathena.com/api"

        headers = {
            "security-Password": os.getenv("ROAD_API_PASSWORD")
        }

        # STEP 1 — get road ids
        survey_url = f"{base}/surveys/{survey_id}"

        r = requests.get(survey_url, headers=headers, timeout=15)
        r.raise_for_status()

        data = r.json()

        roads = data.get("roads", [])

        if not roads:
            logger.warning("No roads found in survey")
            return f"Survey_{survey_id}"

        # STEP 2 — take first road_id
        road_id = roads[0]["id"]

        # STEP 3 — fetch road info
        road_url = f"{base}/surveys/roads/{road_id}"

        r2 = requests.get(road_url, headers=headers, timeout=15)
        r2.raise_for_status()

        road_data = r2.json()

        project_name = road_data.get(
            "survey_request", {}).get("name", f"Survey_{survey_id}")

        # remove bad filename chars
        project_name = project_name.replace("/", "")

        # drop trailing code in parentheses (e.g. (N0900901002RJ)) but keep
        # descriptive parenthesized parts that contain spaces
        project_name = re.sub(r"\s*\([^\) ]+\)\s*$", "", project_name)

        logger.info(f"Project name detected: {project_name}")

        return project_name

    except Exception as e:
        logger.warning(f"Project name extraction failed: {e}")
        return f"Survey_{survey_id}"


def get_road_ids(survey_id, logger):

    try:
        base = "https://ndd.roadathena.com/api"

        headers = {
            "security-Password": os.getenv("ROAD_API_PASSWORD")
        }

        survey_url = f"{base}/surveys/{survey_id}"

        r = requests.get(survey_url, headers=headers, timeout=15)
        r.raise_for_status()

        data = r.json()

        roads = data.get("roads", [])

        road_ids = [r.get("id") for r in roads if r.get("id")]

        logger.info(f"Found {len(road_ids)} road ids for survey {survey_id}")

        return road_ids

    except Exception as e:
        logger.warning(f"Failed to fetch road ids: {e}")
        return []


# -----------------------------
# STEP EXECUTOR
# -----------------------------
def execute_step(name, func, logger, *args):

    try:
        logger.info(f"🚀 STARTING STEP : {name}")

        result = func(*args)

        logger.info(f"✅ COMPLETED STEP : {name}")
        logger.info(f"➡ Moving to next stage...")

        return result

    except Exception as e:

        logger.exception(f"❌ {name} FAILED")
        raise


# -----------------------------
# PARALLEL JSON GENERATION
# -----------------------------
def run_json_generators(downloaded_excels, json_output, survey_root, logger):

    logger.info("Running JSON generators in parallel")

    tasks = [
        ("MCW_final", MCW_final.run, downloaded_excels, json_output, logger),
        ("SR_final", SR_final.run, downloaded_excels, json_output, logger),
        ("SL_final", SL_final.run, downloaded_excels, json_output, logger),
        ("CR_final", CR_final.run, survey_root, json_output, logger),   # <-- added json_output
        ("CL_final", CL_final.run, survey_root, json_output, logger),   # <-- added json_output
        ("TR_final", TR_final.run, downloaded_excels, json_output, logger),
        ("TL_final", TL_final.run, downloaded_excels, json_output, logger)
    ]

    with ThreadPoolExecutor(max_workers=4) as executor:

        futures = {
            executor.submit(func, *args): name
            for name, func, *args in tasks
        }

        for future in as_completed(futures):

            name = futures[future]

            try:
                future.result()
                logger.info(f"{name} finished")

            except Exception as e:
                logger.exception(f"{name} crashed")
                raise


# -----------------------------
# MASTER PIPELINE
# -----------------------------
def run_pipeline(survey_id):

    log_manager = LoggingManager()
    run_context = log_manager.create_run(survey_id)

    logger = run_context["logger"]
    survey_root = run_context["survey_folder"]

    logger.info("=======================================")
    logger.info("STARTING FINAL EXCEL PIPELINE")
    logger.info(f"SURVEY ID : {survey_id}")
    logger.info("=======================================")

    try:

        # --------------------------------
        # STEP 1 : DOWNLOAD EXCELS
        # --------------------------------
        download_result = execute_step(
            "D_A Download",
            D_A.run,
            logger,
            survey_id,
            None,
            survey_root,
            logger
        )

        if not download_result:
            logger.error("Download stage failed")
            return None

        downloaded_excels = os.path.join(survey_root, "Downloaded_Excels")
        json_output = os.path.join(survey_root, "jsons")

        os.makedirs(json_output, exist_ok=True)

        # --------------------------------
        # STEP 2 : JSON GENERATION (PARALLEL)
        # --------------------------------
        run_json_generators(
            downloaded_excels,
            json_output,
            survey_root,
            logger
        )

        # --------------------------------
        # STEP 3 : CHAINAGE EXCEL CREATION
        # --------------------------------
        gen_final_excel_dir = os.path.dirname(os.path.abspath(__file__))  # gen_final_excel/
        execute_step(
            "final_colour_format",
            final_colur_format1.run, logger,
            survey_id, gen_final_excel_dir, logger
        )

        # --------------------------------
        # STEP 4 : POPULATE COUNTS
        # --------------------------------
        workbook = execute_step(
            "dp1 asset mapping",
            dp1.run,
            logger,
            survey_root,
            survey_id,
            logger
        )

        if not workbook:
            logger.error("dp1 failed to generate Excel")
            return None

        # --------------------------------
        # STEP 5 : UPDATE ROAD SEGMENTS
        # --------------------------------
        road_update_result = execute_step(
            "main_road_updater",
            main_road_updater.run,
            logger,
            survey_id,
            logger
        )

        if not road_update_result:
            logger.error("Road segment update failed")
            return None
        # --------------------------------
        # STEP 6 : UPDATE ASSET COUNTS (allasset)
        # --------------------------------
        road_ids = get_road_ids(survey_id, logger)

        if not road_ids:
            logger.error("No road IDs found for asset update")
            return None

        allasset_result = execute_step(
            "allasset update",
            allasset.run,
            logger,
            road_ids,
            logger
        )

        if not allasset_result:
            # success flag false or None -> warn but continue
            logger.warning("Allasset update did not report success")

        # --------------------------------
        # SAVE FINAL OUTPUT
        # --------------------------------
        final_output_dir = os.path.join(survey_root, "Final_Output")
        os.makedirs(final_output_dir, exist_ok=True)

        project_name = get_project_name_from_roads(survey_id, logger)

        safe_name = project_name.replace("_", " ").replace("/", "")

        final_output_excel = os.path.join(
            final_output_dir,
            f"Final Excel {safe_name} .xlsx"
        )
        # --------------------------------
        # STEP 7 : VALIDATE DASHBOARD COUNTS
        # --------------------------------
        # --------------------------------
# STEP 7 : VALIDATOR (API TRUTH)
# --------------------------------
        api_counts = execute_step(
            "validator api counts",
            validator.run,
            logger,
            survey_id,
            logger
        )

        if not api_counts:
            logger.warning("Validator returned no data")

        try:
            workbook.save(final_output_excel)
            logger.info("Final Excel saved successfully")
        except Exception:
            logger.exception("Failed to save final excel")
            raise
        # --------------------------------
# STEP 9 : XLSX VALIDATOR
# --------------------------------
        excel_counts = execute_step(
            "xlsx validator",
            xlsx.run,
            logger,
            survey_root,
            logger
        )

        if not excel_counts:
            logger.warning("Excel validator returned no data")
        # --------------------------------
# STEP 10 : FINAL VALIDATION
# --------------------------------
        validation_status = execute_step(
            "final validator compare",
            finalvalidator.run,
            logger,
            api_counts,
            excel_counts,
            logger
        )

        if validation_status:
            logger.info("✔ PIPELINE VALIDATION SUCCESSFUL")
        else:
            logger.error("❌ PIPELINE VALIDATION FAILED")

        logger.info("=======================================")
        logger.info("PIPELINE COMPLETED SUCCESSFULLY")
        logger.info(f"FINAL EXCEL : {final_output_excel}")
        logger.info("=======================================")

        return {
            "excel_path": final_output_excel,
            "api_counts": api_counts,
            "excel_counts": excel_counts,
            "validation_status": validation_status
        }

    except Exception as e:

        logger.error("PIPELINE FAILED")
        logger.exception(e)

        return None


# -----------------------------
# STANDALONE EXECUTION
# -----------------------------
if __name__ == "__main__":

    survey_input = input("Enter Survey ID: ").strip()

    if not survey_input.isdigit():
        print("Invalid Survey ID")

    else:
        run_pipeline(int(survey_input))
