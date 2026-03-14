import requests
import json
import time
import os


import total_raods as tr




surveyid = 493



# road_ids = range(16119,16138)
# road_ids = [	18766,18767]
# if top row display is none


def main(surveyid=None, road_id:list=None):
    if surveyid:
        road_ids = tr.main(surveyid)
    else:
        road_ids = road_id
    link = "ndd"
    headers = {
        "Security-Password": "admin@123",
    }

    api = "ndd"

    patch = "processed_videos_link"
    patch_api_base_url = f"https://{api}.roadathena.com/api/surveys/reports/"

    fetch_api_url = f"https://{api}.roadathena.com/api/surveys/reports"

    response = requests.get(fetch_api_url, headers=headers)
    data = response.json()


    report_id_map = {str(item.get("surveyroad")): item.get("id") for item in data}
    for i in road_ids:

        dl_link = f"https://raiotransection.s3.ap-south-1.amazonaws.com/output/videos/roadathena/{link}/survey_{surveyid}/road_{i}/{i}/{i}_compressed.mp4"
        # dl_link = f"https://raiotransection.s3.ap-south-1.amazonaws.com/output/videos/roadathena/{api}/survey_{surveyid}/road_{i}/{i}/hls/"

        print("test", dl_link)
        surveyroad = str(i)

        if surveyroad not in report_id_map:
            print(f"Surveyroad {surveyroad} not found in API response, skipping.")
            continue

        report_id = report_id_map[surveyroad]
        patch_url = f"{patch_api_base_url}{report_id}/"

        patch_data = {f"{patch}": dl_link}

        patch_response = requests.patch(patch_url, json=patch_data, headers=headers)

        if patch_response.status_code == 200:
            print(f"Successfully patched surveyroad {surveyroad} with link {link}")
        else:
            print(
                f"Failed to patch surveyroad {surveyroad}. "
                f"Status: {patch_response.status_code}, Response: {patch_response.text}"
            )

#!/usr/bin/env python3
# import requests

# def post_video_links(surveyId, roadId, api_type):
#     """
#     Posts furniture video link to the RoadAthena API for a given survey and road.
#     """

#     # --- Config ---
#     post_field_name = "furniture_videos_link"
#     security_password = "admin@123"
#     headers = {"Security-Password": security_password}

#     fetch_api_url = f"https://{api_type}.roadathena.com/api/surveys/reports"
#     post_api_url = f"https://{api_type}.roadathena.com/api/surveys/reports/"
#     link = "furniture"
#     ExtraArgs = {"ACL": "public-read"}

#     print(f"Fetching reports from: {fetch_api_url}")
#     response = requests.get(fetch_api_url, headers=headers)

#     if response.status_code != 200:
#         print(f"❌ Failed to fetch reports. Status: {response.status_code}, Response: {response.text}")
#         return

#     data = response.json()
#     report_id_map = {str(item.get("surveyroad")): item.get("id") for item in data}
#     print(f"✅ Retrieved {len(report_id_map)} report entries from API")

#     surveyroad = str(roadId)
#     s3_link = (
#         f"https://raiotransection.s3.ap-south-1.amazonaws.com/"
#         f"{link}/output/{api_type}/videos/survey_{surveyId}/road_{roadId}/{roadId}/hls/"
#     )

#     if surveyroad not in report_id_map:
#         print(f"⚠️ Surveyroad {surveyroad} not found in API response, skipping.")
#         return

#     report_id = report_id_map[surveyroad]
#     post_data = {
#         "id": report_id,
#         post_field_name: s3_link
#     }

#     print(f"📤 Posting video link for report_id={report_id} -> {post_field_name}={s3_link}")
#     print(f"ExtraArgs for upload: {ExtraArgs}")

#     try:
#         post_response = requests.post(post_api_url, json=post_data, headers=headers)
#         if post_response.status_code in [200, 201]:
#             print(f"✅ Successfully posted video link for surveyroad {surveyroad}")
#         else:
#             print(f"❌ Failed to post video link for surveyroad {surveyroad}. "
#                   f"Status: {post_response.status_code}, Response: {post_response.text}")
#     except Exception as e:
#         print(f"⚠️ Error posting road {surveyroad}: {e}")

#     print("🎯 Done.")


# if __name__ == "__main__":
#     # --- Change API type here if needed ---
#     api_type = "gurugram"   # or "noida", "delhi", etc.

#     surveyId = 30
#     roadId = 767

#     post_video_links(surveyId, roadId, api_type)


if __name__ == "__main__":
    surveyids = [
        489,
        496,
        493,
        495,
        490,
        531,
        535,
        529,
        533,
        493,
        524,
        526,
        521,
        544,
        543,
        497,
        538,
        523,
    ]
    for sur in surveyids:
        main(surveyid=sur)