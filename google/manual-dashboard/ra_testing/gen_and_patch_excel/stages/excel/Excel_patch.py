# import os
# import json
# import requests


# def fetch_report_id_map(api_url, range_start, range_end):
#     """Fetch the report IDs from the Reports API based on surveyroad within a specific range."""
#     try:
#         response = requests.get(
#             api_url, headers={"Security-Password": "admin@123"})
#         response.raise_for_status()
#         data = response.json()

#         report_id_map = {}
#         for item in data:
#             surveyroad = str(item.get("surveyroad"))
#             report_id = item.get("id")

#             if surveyroad.isdigit():
#                 surveyroad_int = int(surveyroad)
#                 if range_start <= surveyroad_int <= range_end:
#                     report_id_map[surveyroad] = report_id

#         return report_id_map

#     except requests.RequestException as e:
#         print(f"Failed to fetch report IDs from {api_url}: {e}")
#         return {}


# def find_excel_files(folder_path, road_ids):
#     """Find and match Excel files in the folder with road IDs."""
#     matched_files = {}
#     for filename in os.listdir(folder_path):
#         if filename.endswith("_formatted.xlsx"):
#             name_part = filename.replace("_formatted.xlsx", "")
#             if name_part.isdigit():
#                 road_id = int(name_part)
#                 if road_id in road_ids:
#                     matched_files[road_id] = os.path.join(
#                         folder_path, filename)
#     return matched_files


# def patch_excel_files(api_base_url, report_id_map, matched_files):
#     """Patch the Excel files to the API using report IDs."""
#     for road_id, file_path in matched_files.items():
#         report_id = report_id_map.get(str(road_id))
#         if report_id is None:
#             print(
#                 f"No report ID found for road ID {road_id}. Skipping file {file_path}.")
#             continue

#         patch_url = f"{api_base_url}/{report_id}/"
#         try:
#             with open(file_path, 'rb') as file:
#                 files = {'excelreport': file}
#                 response = requests.patch(patch_url, files=files, headers={
#                                           "Security-Password": "admin@123"})
#                 response.raise_for_status()
#                 print(
#                     f"Successfully patched report ID {report_id} with file {file_path}")
#         except requests.RequestException as e:
#             print(
#                 f"Failed to patch report ID {report_id} with file {file_path}: {e}")


# def fetch_road_names(api_url, range_start, range_end):
#     """Fetch road names from the API."""
#     road_names = {}
#     for id in range(range_start, range_end + 1):
#         url = f"{api_url}/{id}"
#         try:
#             response = requests.get(
#                 url, headers={"Security-Password": "admin@123"})
#             response.raise_for_status()
#             data = response.json()
#             road_name = data.get("road", {}).get("name", "")
#             if road_name:
#                 road_names[id] = road_name
#         except requests.RequestException as e:
#             print(f"Failed to fetch road name for ID {id}: {e}")
#     return road_names


# def main():
#     api_url = "https://ndd.roadathena.com/api/surveys/roads"
#     range_start = 16956
#     range_end = 17130
#     folder_path = "C:\\Users\\dibya\\Desktop\\tttttttttttttttttttt\\op"
#     api_base_url = "https://ndd.roadathena.com/api/surveys/reports"

#     # Fetch the report ID mapping
#     report_id_map = fetch_report_id_map(api_url, range_start, range_end)
#     if not report_id_map:
#         print("No report ID mapping found. Exiting.")
#         return

#     # Extract road IDs from the report ID map
#     road_ids = list(map(int, report_id_map.keys()))

#     # Find Excel files by road IDs
#     matched_files = find_excel_files(folder_path, road_ids)
#     if not matched_files:
#         print("No matching Excel files found. Exiting.")
#         return

#     # Patch the Excel files
#     patch_excel_files(api_base_url, report_id_map, matched_files)


# if __name__ == "__main__":
#     main()


# 2nd --------------------------------------------------------------------------------------------------------------------------------------------


# import os
# import requests

# def find_excel_files(folder_path, road_ids):
#     """Find and match Excel files in the folder with road IDs."""
#     matched_files = {}
#     for filename in os.listdir(folder_path):
#         if filename.endswith("_formatted.xlsx"):
#             name_part = filename.replace("_formatted.xlsx", "")
#             if name_part.isdigit():
#                 road_id = int(name_part)
#                 if road_id in road_ids:
#                     matched_files[road_id] = os.path.join(folder_path, filename)
#     return matched_files

# def create_reports(api_base_url, matched_files, survey_request):
#     """POST new reports with Excel files to the API."""
#     for road_id, file_path in matched_files.items():
#         try:
#             with open(file_path, 'rb') as file:
#                 files = {'excelreport': file}
#                 data = {
#                     'survey_request': survey_request,
#                     'surveyroad': road_id,
#                 }
#                 response = requests.post(
#                     api_base_url,
#                     files=files,
#                     data=data,
#                     headers={"Security-Password": "admin@123"}
#                 )
#                 response.raise_for_status()
#                 created = response.json()
#                 print(f"✅ Created report ID {created.get('id')} for Road ID {road_id} with file {file_path}")
#         except requests.RequestException as e:
#             print(f"❌ Failed to create report for Road ID {road_id} with file {file_path}: {e}")

# def main():
#     api_base_url = "https://ndd.roadathena.com/api/surveys/reports/"
#     folder_path = "C:\\Users\\LENOVO\\Desktop\\Hanuai\\excel_code_updated\\op"
#     survey_request = 145   # change this to your actual survey ID
#     range_start = 3742
#     range_end = 3742

#     # road IDs to process
#     road_ids = list(range(range_start, range_end + 1))

#     # find matching Excel files
#     matched_files = find_excel_files(folder_path, road_ids)
#     if not matched_files:
#         print("⚠ No matching Excel files found. Exiting.")
#         return

#     # create reports with Excel
#     create_reports(api_base_url, matched_files, survey_request)

# if __name__ == "__main__":
#     main()


# def chainageWiseCounting(survey_data, json_data, side, value_diff):
#     # ...
#     logger.debug(f"Survey side: {survey_data.get('side')} getting...")
#     logger.debug(f"fux {side}")
#     logger.debug(f"Survey side: {survey_side}")
#     # ...
#     logger.debug(
#         f"Chainage values: start={start_chainage}, from={from_chainage}, to={to_chainage}")
#     # ...
#     logger.error("End key error")
#     # ...
#     logger.error("End chainage value is not defined. Exiting the process.")
#     # ...
#     logger.error(
#         f"Invalid end chainage value: {end_chainage_value}. It must be a valid integer.")
# =============================================================================================================================================

import os
import requests
import logging
from typing import Optional, Dict, Any


REPORTS_API_URL = "https://ndd.roadathena.com/api/surveys/reports"


def _fetch_report_id_for_road(
    road_id: int,
    security_password: str,
    logger: logging.Logger
) -> Optional[int]:
    """
    Fetch report_id for a single road_id.
    Logic preserved from old excel_patch.py.
    """

    try:
        response = requests.get(
            REPORTS_API_URL,
            headers={"Security-Password": security_password},
            timeout=60
        )
        response.raise_for_status()

        data = response.json()

        for item in data:
            surveyroad = str(item.get("surveyroad"))
            if surveyroad == str(road_id):
                return item.get("id")

        logger.warning(f"No report found for road_id={road_id}")
        return None

    except requests.RequestException as e:
        logger.exception(
            f"Failed to fetch reports list | road_id={road_id} | error={str(e)}"
        )
        return None


def run(
    road_id: int,
    excel_root: str,
    security_password: str,
    logger: Optional[logging.Logger] = None,
) -> Dict[str, Any]:

    if logger is None:
        logger = logging.getLogger(__name__)

    results = {
        "road_id": road_id,
        "patched": False,
        "report_id": None,
        "error": None
    }

    logger.info(f"Starting Excel patch stage | road_id={road_id}")

    # ----------------------------------------------------
    # 1️⃣ Locate Excel file
    # ----------------------------------------------------
    excel_path = os.path.join(excel_root, f"{road_id}_formatted.xlsx")

    if not os.path.exists(excel_path):
        logger.error(
            f"Excel file not found | road_id={road_id} | path={excel_path}"
        )
        results["error"] = "excel_file_not_found"
        return results

    # ----------------------------------------------------
    # 2️⃣ Fetch report_id (old logic preserved)
    # ----------------------------------------------------
    report_id = _fetch_report_id_for_road(
        road_id, security_password, logger
    )

    if not report_id:
        results["error"] = "report_not_found"
        return results

    results["report_id"] = report_id

    # ----------------------------------------------------
    # 3️⃣ Patch Excel file
    # ----------------------------------------------------
    patch_url = f"{REPORTS_API_URL}/{report_id}/"

    try:
        with open(excel_path, "rb") as file:
            response = requests.patch(
                patch_url,
                files={"excelreport": file},
                headers={"Security-Password": security_password},
                timeout=120
            )

        if response.status_code == 200:
            logger.info(
                f"Excel patched successfully | road_id={road_id} | report_id={report_id}"
            )
            results["patched"] = True
        else:
            logger.error(
                f"Excel patch failed | road_id={road_id} | "
                f"report_id={report_id} | "
                f"status={response.status_code} | "
                f"response={response.text}"
            )
            results["error"] = f"patch_failed_{response.status_code}"

    except Exception as e:
        logger.exception(
            f"Exception during Excel patch | road_id={road_id} | error={str(e)}"
        )
        results["error"] = "exception_during_patch"

    logger.info(
        f"Excel patch stage completed | road_id={road_id} | patched={results['patched']}"
    )

    return results
