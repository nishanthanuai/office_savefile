# import os
# import requests


# api_base_url = "https://ndd.roadathena.com/api/surveys/roads/"

# json_folder = "jsons"

# # road_furniture_44_updated.json
# ids = [3735,3736]

# for file_id in ids:
#     print(file_id)
#     json_file_path = os.path.join(json_folder, f"road_furniture_{file_id}.json")


#     if os.path.exists(json_file_path):
#         print(f"Processing {json_file_path}")

#         try:

#             with open(json_file_path, 'rb') as json_file:

#                 files = {
#                     'furniture_json': json_file
#                 }


#                 api_url = f"{api_base_url}{file_id}"
#                 response = requests.patch(api_url, files=files, headers={"Security-Password": "admin@123"})

#                 # Check if the request was successful
#                 if response.status_code == 200:
#                     print(f"Successfully patched data for ID {file_id}")
#                 else:
#                     print(f"Failed to patch data for ID {file_id}. Status code: {response.status_code}")
#                     print(f"Response: {response.text}")

#         except Exception as e:
#             print(f"Error processing ID {file_id}: {str(e)}")
#     else:
#         print(f"File {json_file_path} does not exist, skipping...")


# import os
# import requests


# api_base_url = "https://ndd.roadathena.com/api/surveys/roads/"

# json_folder = "C:\\Users\\dibya\\Desktop\\E_C_U\\excel_code_updated\\jsons2"  # input folder

# # road_furniture_44_updated.json
# # ids = list(range(7505,7506))

# ids = [15821, 15822, 15823, 15824, 15825, 15826, 15827, 15828, 15829, 15830, 15831, 15832, 15833, 15834, 15835, 15836, 15837, 15838, 15839, 15840, 15841, 15842, 15843, 15844, 15845, 15846, 15847, 15848, 15849, 15850, 15900, 15901, 15902, 15903, 15904,
#        15905, 15906, 15907, 15908, 15909, 15910, 15911, 15912, 15913, 15914, 15915, 15916, 15917, 15918, 15919, 15920, 15921, 15922, 15923, 15924, 15925, 15926, 15927, 15928, 15929, 15930, 15931, 15932, 15933, 15934, 15935, 15936, 15938, 15939, 15940]


# for file_id in ids:
#     json_file_path = os.path.join(json_folder, f"road_{file_id}.json")

#     if os.path.exists(json_file_path):
#         print(f"Processing {json_file_path}")

#         try:

#             with open(json_file_path, 'rb') as json_file:

#                 files = {
#                     'furniture_json': json_file
#                 }

#                 api_url = f"{api_base_url}{file_id}"
#                 response = requests.patch(api_url, files=files, headers={
#                                           "Security-Password": "admin@123"})

#                 # Check if the request was successful
#                 if response.status_code == 200:
#                     print(f"Successfully patched data for ID {file_id}")
#                 else:
#                     print(
#                         f"Failed to patch data for ID {file_id}. Status code: {response.status_code}")
#                     print(f"Response: {response.text}")

#         except Exception as e:
#             print(f"Error processing ID {file_id}: {str(e)}")
#     else:
#         print(f"File {json_file_path} does not exist, skipping...")


import os
import requests
import logging
from typing import List, Optional, Dict, Any


API_BASE_URL = "https://ndd.roadathena.com/api/surveys/roads/"


def run(
    road_ids: List[int],
    road_type: str,
    json_root: str,
    security_password: str,
    logger: Optional[logging.Logger] = None,
) -> Dict[str, Any]:

    if logger is None:
        logger = logging.getLogger(__name__)

    results = {
        "patched": [],
        "failed": [],
        "total": 0
    }

    # subfolder = road_type.lower()

    folder = json_root

    if not os.path.exists(folder):
        logger.error(f"JSON folder not found: {folder}")
        return results

    logger.info(
        f"Starting JSON patch | road_type={road_type} | folder={folder}"
    )

    for road_id in road_ids:

        file_path = os.path.join(folder, f"road_{road_id}.json")

        if not os.path.exists(file_path):
            logger.error(
                f"JSON not found for patch | road_id={road_id} | path={file_path}"
            )
            results["failed"].append(road_id)
            continue

        try:
            with open(file_path, "rb") as json_file:

                response = requests.patch(
                    f"{API_BASE_URL}{road_id}",
                    files={"furniture_json": json_file},
                    headers={"Security-Password": security_password},
                    timeout=60
                )

            if response.status_code == 200:
                logger.info(f"Patched road successfully | road_id={road_id}")
                results["patched"].append(road_id)
            else:
                logger.error(
                    f"Patch failed | road_id={road_id} | "
                    f"status={response.status_code} | "
                    f"response={response.text}"
                )
                results["failed"].append(road_id)

        except Exception as e:
            logger.exception(
                f"Exception during patch | road_id={road_id} | error={str(e)}"
            )
            results["failed"].append(road_id)

        results["total"] += 1

    logger.info(
        f"JSON patch stage completed | "
        f"patched={len(results['patched'])} | "
        f"failed={len(results['failed'])}"
    )

    return results
