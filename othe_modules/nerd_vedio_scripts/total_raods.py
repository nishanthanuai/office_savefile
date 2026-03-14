import requests
from collections import defaultdict

# -----------------------------
# CONFIG
# -----------------------------
SURVEY_ID = 558


BASE_URL = "https://ndd.roadathena.com/api"
HEADERS = {
    "security-Password": "admin@123"
}
TIMEOUT = 30


# -----------------------------
# FETCH ALL ROAD IDS
# -----------------------------
def fetch_road_ids(survey_id):
    url = f"{BASE_URL}/surveys/{survey_id}"
    resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
    resp.raise_for_status()

    data = resp.json()
    roads = data.get("roads", [])
    return sorted([r["id"] for r in roads if "id" in r])


# -----------------------------
# FETCH ROAD TYPE (CORRECT API)
# -----------------------------
def fetch_road_type(road_id):
    url = f"{BASE_URL}/surveys/roads/{road_id}"
    resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT)

    if resp.status_code != 200:
        return "UNKNOWN"

    data = resp.json()
    road = data.get("road", {})
    return road.get("road_type", "UNKNOWN")


# -----------------------------
# MAIN
# -----------------------------
def main(SURVEY_ID):
    print("\nFetching road IDs from survey...\n")

    road_ids = fetch_road_ids(SURVEY_ID)
    total_roads = len(road_ids)

    print(f"Total roads: {total_roads}")
    print(f"Road IDs:\n{road_ids}\n")

    road_type_map = defaultdict(list)

    print("Fetching road types (this may take some time)...\n")

    # for rid in road_ids:
    #     rtype = fetch_road_type(rid)
    #     road_type_map[rtype].append(rid)

    # -----------------------------
    # OUTPUT SUMMARY
    # -----------------------------
    print("\n================ ROAD TYPE SUMMARY ================\n")

    for rtype in sorted(road_type_map.keys()):
        ids = road_type_map[rtype]
        print(f"{rtype}: {len(ids)}")
        print(f"{rtype} Roads: {ids}\n")

    print("==================================================\n")
    
    return road_ids


# -----------------------------
if __name__ == "__main__":
    print(main(SURVEY_ID), type(main(SURVEY_ID)))
