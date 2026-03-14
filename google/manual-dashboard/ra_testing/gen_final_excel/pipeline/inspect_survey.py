import requests
import os
import json

ROAD_API_PASSWORD = os.getenv("ROAD_API_PASSWORD")


def inspect_survey(survey_id):

    url = f"https://ndd.roadathena.com/api/surveys/{survey_id}"

    response = requests.get(
        url,
        headers={"Security-Password": ROAD_API_PASSWORD}
    )

    print("STATUS:", response.status_code)

    data = response.json()

    print("\nFULL RESPONSE STRUCTURE:\n")
    print(json.dumps(data, indent=2))

    roads = data.get("roads", [])

    print("\nTOTAL ROADS:", len(roads))

    print("\nROAD STRUCTURE SAMPLE:\n")

    if roads:
        print(json.dumps(roads[0], indent=2))

    print("\nROAD TYPES:\n")

    for road in roads:
        print(
            "road_id:",
            road.get("road_id") or road.get("id"),
            "| type:",
            road.get("road_type")
        )


if __name__ == "__main__":

    survey_id = input("Enter survey id: ").strip()

    inspect_survey(survey_id)
