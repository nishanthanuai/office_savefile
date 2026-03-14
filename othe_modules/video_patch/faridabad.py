# import requests

# api = "https://faridabad.roadathena.com/api/surveys/reports/"

# survey_id = 130
# road_ids = [3422]

# headers = {
#     "Security-Password": "admin@123",
#     "Content-Type": "application/json"
# }

# base_video_url = f"https://raiotransection.s3.ap-south-1.amazonaws.com/input/videos/pavement/faridabad/survey_{survey_id}"

# for road_id in road_ids:
#     payload = {
#         "surveyroad": road_id,
#         "survey_request": survey_id,
#         "processed_videos_link": f"{base_video_url}/road_{road_id}/NORM0001.MP4"

#     }

#     response = requests.post(api, json=payload, headers=headers)

#     print(f"Road {road_id} → Status:", response.status_code)
#     try:
#         print(response.json())
#     except Exception:
#         print(response.text)


import requests

api = "https://faridabad.roadathena.com/api/surveys/reports/"

survey_id = 4
road_ids = [177]

headers = {"Security-Password": "admin@123", "Content-Type": "application/json"}

base_video_url = (
    f"https://raiotransection.s3.ap-south-1.amazonaws.com/input/videos/pavement/faridabad/survey_{survey_id}"
    # f"input/videos/pavement/faridabad/survey_{survey_id}"
)

for road_id in road_ids:
    payload = {
        "surveyroad": road_id,
        "survey_request": survey_id,
        "processed_videos_link": f"{base_video_url}/road_{road_id}/NORM0081.MP4",
    }

    response = requests.post(api, json=payload, headers=headers)

    print(f"Road {road_id} -> Status:", response.status_code)

    try:
        print(response.json())
    except Exception:
        print(response.text)
