import os
import requests

BASE_URL = "https://ndd.roadathena.com/api"
ROAD_API_PASSWORD = os.getenv("ROAD_API_PASSWORD")

road_id = 18051  # pick one from your list

url = f"{BASE_URL}/surveys/roads/{road_id}"
response = requests.get(
    url, headers={"Security-Password": ROAD_API_PASSWORD}, timeout=30)
print("Status code:", response.status_code)
print("Raw JSON:", response.json())
