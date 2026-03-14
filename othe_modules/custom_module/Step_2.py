import json
import re
import requests
import os
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import landscape, A4
from reportlab.lib.units import inch
from PIL import Image
from io import BytesIO
import sys


def extract_road_class_from_name(name):
    match = re.search(
        r"\b(SRR|SRL|SLL|IRL|IRR|TL|TR|FP SSR|FP SRL|LRR|LRL|MCW RHS|MCW LHS|MCW|FP)(?:\s+(\d+\.\d+|\d+))?",
        name,
    )
    if match:
        road_class = match.group(1)
        road_id = match.group(2) if match.group(2) else ""
        return road_class, road_id
    else:
        user_input = input(
            f"No match found for '{name}'. Please enter the road class manually: "
        )
        return user_input, ""


def extract_road_id_from_filename(filename):
    match = re.search(r"road_(\d+).json", filename)
    return match.group(1) if match else None


def format_distance(distance):
    kilometers = int(distance) // 1000
    meters = int(distance) % 1000
    return f"{kilometers}+{meters:03d}"


def parse_distance(formatted_distance):
    parts = formatted_distance.split("+")
    if len(parts) == 2:
        kilometers = int(parts[0])
        meters = int(parts[1])
        return kilometers * 1000 + meters
    return 0


def get_road_data(road_id):
    BASE_API_URL = f"https://ndd.roadathena.com/api/surveys/roads/{road_id}"
    headers = {"Security-Password": "admin@123"}

    try:
        response = requests.get(BASE_API_URL, headers=headers)
        road_metadata = response.json()
        return road_metadata
    except Exception as e:
        print(f"Error fetching road data for road ID {road_id}: {e}")
        return {"road": {"name": f"Unknown Road {road_id}"}}


def process_assets_for_subfolder(subfolder_path):
    combined_assets = {}
    txt_data = []

    print(f"\nProcessing subfolder: {subfolder_path}")
    subfolder_name = os.path.basename(subfolder_path)

    for filename in os.listdir(subfolder_path):
        if filename.endswith(".txt"):
            txt_path = os.path.join(subfolder_path, filename)
            with open(txt_path, "r") as file:
                txt_data = file.readlines()
            print("text data", txt_data)

        if filename.endswith(".json"):
            json_path = os.path.join(subfolder_path, filename)
            road_id = extract_road_id_from_filename(filename)

            if not road_id:
                print(f"  Skipping file (no road ID found): {filename}")
                continue

            try:
                with open(json_path, "r") as file:
                    json_data = json.load(file)

                road_metadata = get_road_data(road_id)
                road_name = road_metadata["road"]["name"]
                start_chainage = road_metadata["road"].get("start_chainage", 0)
                end_chainage = road_metadata["road"].get("end_chainage", 0)

                side_direction = "RHS"
                if road_metadata["road"].get("LHR_side"):
                    side_direction = "LHS"

                print("current side", road_id, side_direction)

                road_type, road_suffix = extract_road_class_from_name(road_name)
                road_key = f"{road_type} {road_suffix}".strip()

                if road_key not in combined_assets:
                    combined_assets[road_key] = []

                for asset in json_data.get("anomalies", []):
                    asset_type = asset.get("Anomaly type", "")
                    if asset_type == "PROHIBITORY_MANDATORY_SIGNS":
                        asset_type = "PROHIBITORY-MANDATORY-SIGNS"
                    if asset_type == "INFORMATORY_SIGNS":
                        asset_type = "INFORMATORY-SIGN"
                    if asset_type == "CAUTIONARY_WARNING_SIGNS":
                        asset_type = "CAUTIONARY-WARNING-SIGNS"

                    sign_type = asset.get("category", "")
                    side = asset.get("Side", "Center")
                    lat = asset.get("Latitude", "")
                    lon = asset.get("Longitude", "")
                    image = asset.get("image", "")

                    distance_value = asset.get("Distance")
                    distance_value = float(distance_value) if distance_value else 0

                    if side_direction == "LHS":
                        d_value = float(start_chainage) + distance_value
                    else:
                        d_value = float(start_chainage) - distance_value

                    dist = format_distance(d_value)

                    combined_assets[road_key].append(
                        {
                            "line": f"{dist} {asset_type} {sign_type} {side} {lat:.4f} {lon:.4f} {image}",
                            "dist": dist,
                            "numeric_dist": parse_distance(dist),
                            "image": image,
                        }
                    )

                print(
                    f"  Processed {filename} - Found {len(json_data.get('anomalies', []))} anomalies"
                )

            except Exception as e:
                print(f"  Error processing {filename}: {e}")

    output_path = os.path.join(
        os.path.dirname(subfolder_path), f"{subfolder_name}_formatted.txt"
    )
    with open(output_path, "w") as f:
        if txt_data:
            f.write("".join(txt_data))
            f.write("\n\n")

        for road_key, assets in combined_assets.items():
            if len(assets) > 0:
                sorted_assets = sorted(assets, key=lambda x: x["numeric_dist"])
                f.write(f"{road_key} - {len(sorted_assets)}\n")
                f.write("\n".join([asset["line"] for asset in sorted_assets]))
                f.write("\n\n")

    print(f"✅ Output for subfolder {subfolder_name} written to {output_path}")

    non_empty_roads = sum(1 for lines in combined_assets.values() if len(lines) > 0)
    total_assets = sum(len(lines) for lines in combined_assets.values())

    return non_empty_roads, total_assets


def main(test_folder):
    print(f"Starting processing for all subfolders in {test_folder}")

    total_subfolders = 0
    total_roads = 0
    total_assets = 0

    for item in os.listdir(test_folder):
        subfolder_path = os.path.join(test_folder, item)

        if os.path.isdir(subfolder_path):
            roads_count, assets_count = process_assets_for_subfolder(subfolder_path)
            total_subfolders += 1
            total_roads += roads_count
            total_assets += assets_count

    print("\n===== Summary =====")
    print(f"Processed {total_subfolders} subfolders")
    print(f"Found {total_roads} unique roads with {total_assets} total assets")
    print("===================")


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        test_folder = sys.argv[1]
    else:
        test_folder = "Report"

    if not os.path.isdir(test_folder):
        print(f"❌ Error: {test_folder} is not a valid directory.")
    else:
        main(test_folder)
