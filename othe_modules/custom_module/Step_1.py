# import json
# import os
# import requests

# # Set base folder path
# base_folder = "Report"  

# # Headers for API
# headers = {"Security-Password": "admin@123"}
# api_base_url = "https://ndd.roadathena.com/api/surveys/roads/"
# file_base_url = "https://ndd.roadathena.com"

# # Function to update JSON
# def update_json_file(filepath):
#     with open(filepath, 'r') as f:
#         data = json.load(f)

#     updated_assets = []
#     new_anomalies = data.get('anomalies', [])

#     for asset in data.get('assets', []):
#         if asset.get("Asset type") == "DAMAGED_SIGN":
#             anomaly = {
#                 "Anomaly number": asset.get("Assets number"),
#                 "Timestamp on processed video": asset.get("Timestamp on processed video"),
#                 "Anomaly type": asset.get("Asset type"),
#                 "Side": asset.get("Side"),
#                 "Latitude": asset.get("Latitude"),
#                 "Longitude": asset.get("Longitude"),
#                 "Distance": asset.get("Distance"),
#                 "Length": asset.get("Length"),
#                 "Average width": asset.get("Average width"),
#                 "Remarks": asset.get("Remarks"),
#                 "image": asset.get("image"),
#                 "category": asset.get("category")
#             }
#             new_anomalies.append(anomaly)
#         else:
#             updated_assets.append(asset)

#     data['assets'] = updated_assets
#     data['anomalies'] = new_anomalies

#     with open(filepath, 'w') as f:
#         json.dump(data, f, indent=4)

#     print(f"📝 Updated JSON file: {filepath}")

# # Loop through subfolders
# for subfolder_name in os.listdir(base_folder):
#     subfolder_path = os.path.join(base_folder, subfolder_name)
#     if not os.path.isdir(subfolder_path):
#         continue

#     # Find .txt file inside subfolder
#     txt_files = [f for f in os.listdir(subfolder_path) if f.endswith('.txt')]
#     if not txt_files:
#         print(f"⚠️ No .txt file found in {subfolder_path}")
#         continue

#     txt_path = os.path.join(subfolder_path, txt_files[0])

#     # Read ID from the file
#     with open(txt_path, 'r') as f:
#         lines = f.readlines()

#     id_line = next((line for line in lines if "ID -" in line), None)
#     if not id_line:
#         print(f"⚠️ ID not found in {txt_path}")
#         continue

#     try:
#         id = int(id_line.strip().split("ID -")[1].strip())
#     except ValueError:
#         print(f"❌ Invalid ID format in {txt_path}")
#         continue

#     print(f"\n📁 Processing project folder: {subfolder_name} (ID: {id})")

#     # Fetch road data for the given ID
#     api_url = f"https://ndd.roadathena.com/api/surveys/{id}"
#     response = requests.get(api_url, headers=headers)

#     if response.status_code != 200:
#         print(f"❌ Failed to fetch project data for ID {id}")
#         continue

#     data = response.json()
#     road_ids = [road.get("id") for road in data.get("roads", []) if "id" in road]

#     # Download each road's JSON and update
#     for file_id in road_ids:
#         try:
#             road_api_url = f"{api_base_url}{file_id}"
#             road_response = requests.get(road_api_url, headers=headers)

#             if road_response.status_code == 200:
#                 json_data = road_response.json()

#                 if 'furniture_json' in json_data:
#                     json_file_url = json_data['furniture_json']
#                     full_file_url = f"{file_base_url}{json_file_url}"

#                     file_response = requests.get(full_file_url, headers=headers)
#                     if file_response.status_code == 200:
#                         json_file_path = os.path.join(subfolder_path, f"road_{file_id}.json")
#                         with open(json_file_path, 'wb') as json_file:
#                             json_file.write(file_response.content)
#                         print(f"✅ Downloaded: road_{file_id}.json")

#                         update_json_file(json_file_path)
#                     else:
#                         print(f"❌ Failed to download JSON file for road ID {file_id}")
#                 else:
#                     print(f"⚠️ 'furniture_json' not found for road ID {file_id}")
#             else:
#                 print(f"❌ Failed to fetch road data for ID {file_id}")
#         except Exception as e:
#             print(f"❌ Error processing road ID {file_id}: {e}")

import json
import os
import requests

# Set base folder path
base_folder = "Report"  

# Headers for API
headers = {"Security-Password": "admin@123"}
api_base_url = "https://ndd.roadathena.com/api/surveys/roads/"
file_base_url = "https://ndd.roadathena.com"

# Function to update JSON
def update_json_file(filepath):
    with open(filepath, 'r') as f:
        data = json.load(f)

    # We start with empty lists to ensure we ONLY keep what we want
    final_anomalies = []
    final_assets = []
    found_damaged_sign = False

    # 1. Check existing anomalies for DAMAGED_SIGN
    for anomaly in data.get('anomalies', []):
        if anomaly.get("Anomaly type") == "DAMAGED_SIGN":
            final_anomalies.append(anomaly)
            found_damaged_sign = True

    # 2. Check assets for DAMAGED_SIGN and move them to anomalies
    for asset in data.get('assets', []):
        if asset.get("Asset type") == "DAMAGED_SIGN" and "OBSTRUCTED_SIGN":
            new_anomaly = {
                "Anomaly number": asset.get("Assets number"),
                "Timestamp on processed video": asset.get("Timestamp on processed video"),
                "Anomaly type": asset.get("Asset type"),
                "Side": asset.get("Side"),
                "Latitude": asset.get("Latitude"),
                "Longitude": asset.get("Longitude"),
                "Distance": asset.get("Distance"),
                "Length": asset.get("Length"),
                "Average width": asset.get("Average width"),
                "Remarks": asset.get("Remarks"),
                "image": asset.get("image"),
                "category": asset.get("category")
            }
            final_anomalies.append(new_anomaly)
            found_damaged_sign = True
        else:
            # Keep other assets in the assets list
            final_assets.append(asset)

    # 3. Final Decision: If no DAMAGED_SIGN found, delete the file.
    if not found_damaged_sign:
        print(f"🗑️ No DAMAGED_SIGN found. Deleting file: {filepath}")
        os.remove(filepath)
        return

    # Update data object
    data['assets'] = final_assets
    data['anomalies'] = final_anomalies

    with open(filepath, 'w') as f:
        json.dump(data, f, indent=4)

    print(f"✅ Success: DAMAGED_SIGN found and saved in {filepath}")

# Loop through subfolders
def start_update_json(base_folder,headers,api_base_url,file_base_url):
    for subfolder_name in os.listdir(base_folder):
        subfolder_path = os.path.join(base_folder, subfolder_name)
        if not os.path.isdir(subfolder_path):
            continue

        # Find .txt file inside subfolder
        txt_files = [f for f in os.listdir(subfolder_path) if f.endswith('.txt')]
        if not txt_files:
            continue

        txt_path = os.path.join(subfolder_path, txt_files[0])

        # Read ID from the file
        with open(txt_path, 'r') as f:
            lines = f.readlines()

        id_line = next((line for line in lines if "ID -" in line), None)
        if not id_line:
            continue

        try:
            id = int(id_line.strip().split("ID -")[1].strip())
        except (ValueError, IndexError):
            continue

        print(f"\n📁 Processing ID: {id}")

        # Fetch road data for the given ID
        api_url = f"https://ndd.roadathena.com/api/surveys/{id}"
        try:
            response = requests.get(api_url, headers=headers)
            if response.status_code != 200:
                continue

            data = response.json()
            road_ids = [road.get("id") for road in data.get("roads", []) if "id" in road]

            for file_id in road_ids:
                road_api_url = f"{api_base_url}{file_id}"
                road_response = requests.get(road_api_url, headers=headers)

                if road_response.status_code == 200:
                    json_data = road_response.json()

                    if 'furniture_json' in json_data:
                        json_file_url = json_data['furniture_json']
                        full_file_url = f"{file_base_url}{json_file_url}"

                        file_response = requests.get(full_file_url, headers=headers)
                        if file_response.status_code == 200:
                            json_file_path = os.path.join(subfolder_path, f"road_{file_id}.json")
                            with open(json_file_path, 'wb') as json_file:
                                json_file.write(file_response.content)
                            
                            # Process and filter the file
                            update_json_file(json_file_path)
        except Exception as e:
            print(f"❌ Error: {e}")