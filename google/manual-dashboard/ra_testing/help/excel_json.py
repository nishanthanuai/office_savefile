import pandas as pd
import json
import os
import re  

def generate_json_from_folder(folder_path, output_json_path="furniture_chainage_report.json"):
    furniture_chainage_report = {}

    lhs_service_counter = 1
    rhs_service_counter = 1

    lhs_counter = 1
    rhs_counter = 1 

    lhs_service = 1
    rhs_service = 1

    for file_name in os.listdir(folder_path):
        if file_name.endswith(".xlsx"):
            file_path = os.path.join(folder_path, file_name)

            # Determine road name based on file name patterns
            if "MCW LHS" in file_name:
                road_name = "Main Carriage Way LHS"
            elif "MCW RHS" in file_name:
                road_name = "Main Carriage Way RHS"
            elif "SR" in file_name: 
                match = re.search(r'SR(\d*)\s*(LHS|RHS)', file_name)
                if match:
                    side = match.group
                    if side == "LHS":
                        road_name = f"Service Road LHS{lhs_service_counter} (SRL{lhs_service_counter})"
                        lhs_service_counter += 1  
                    else:
                        road_name = f"Service Road RHS{rhs_service_counter} (SRR{rhs_service_counter})"
                        rhs_service_counter += 1  
                else:
                    print(f"Skipping file {file_name} due to unrecognized format.")
                    continue
            elif "T" in file_name or "C" in file_name:
                match = re.search(r'(T|C)(\d*)\s*(LHS|RHS)', file_name)
                if match:
                    side = match.group(3)
                    if side == "LHS":
                        road_name = f"Intersecting road LHS {lhs_counter} (IRL{lhs_counter})" if match.group(1) == "T" else f"Service Road LHS{lhs_service} (CRL{lhs_service})"
                        lhs_counter += 1 if match.group(1) == "T" else 0
                        lhs_service += 1 if match.group(1) == "C" else 0
                    else:
                        road_name = f"Intersection RHS{rhs_counter} (IRR{rhs_counter})" if match.group(1) == "T" else f"Service Road RHS{rhs_service} (CRR{rhs_service})"
                        rhs_counter += 1 if match.group(1) == "T" else 0
                        rhs_service += 1 if match.group(1) == "C" else 0
                else:
                    print(f"Skipping file {file_name} due to unrecognized format.")
                    continue

                # Read from the "Assets" sheet
                df = pd.read_excel(file_path, sheet_name="Assets", skiprows=5)
                df.columns = df.columns.str.strip()

                # Read the Start Chainage value and clean it up
                start_chainage_row = pd.read_excel(file_path, sheet_name="Assets", skiprows=3)
                start_chainage_value = start_chainage_row.iloc[0].get('Start Chainage', None)

                # Remove non-numeric characters and check if the result is a valid number
                if isinstance(start_chainage_value, str):
                    start_chainage_value = re.sub(r'\D', '', start_chainage_value)

                # Verify if start_chainage_value is numeric after cleaning
                if start_chainage_value.isdigit():
                    start_chainage = int(start_chainage_value)
                    from_value = start_chainage
                    to_value = from_value + 500
                else:
                    print(f"Skipping file {file_name} as 'Start Chainage' is not valid.")
                    continue


                # Initialize entry if it does not exist
                if road_name not in furniture_chainage_report:
                    furniture_chainage_report[road_name] = {}

                # Extract counts based on Asset type and Side
                asset_counts = {
                    "Chevron": {"Avenue/Left": 0, "Median/Right": 0},
                    "CAUTIONARY_WARNING_SIGNS": {"Avenue/Left": 0, "Median/Right": 0},
                    "HAZARD": {"Avenue/Left": 0, "Median/Right": 0},
                    "PROHIBITORY_MANDATORY_SIGNS": {"Avenue/Left": 0, "Median/Right": 0},
                    "INFORMATORY_SIGNS": {"Avenue/Left": 0, "Median/Right": 0}
                }
                for _, row in df.iterrows():
                    asset_type = row.get("Asset type")
                    side = row.get("Side")
                    count = row.get("Count", 0)

                    if asset_type in asset_counts:
                        if side in ["Avenue", "Left"]:
                            asset_counts[asset_type]["Avenue/Left"] += count
                        elif side in ["Median", "Right"]:
                            asset_counts[asset_type]["Median/Right"] += count
    

                entry = {
                    "Road Section": road_name,
                    "from": from_value,
                    "to": to_value,
                    "Chevron": asset_counts["Chevron"],
                    "CAUTIONARY_WARNING_SIGNS": asset_counts["CAUTIONARY_WARNING_SIGNS"],
                    "HAZARD": asset_counts["HAZARD"],
                    "PROHIBITORY_MANDATORY_SIGNS": asset_counts["PROHIBITORY_MANDATORY_SIGNS"],
                    "INFORMATORY_SIGNS": asset_counts["INFORMATORY_SIGNS"]
                }
                furniture_chainage_report[road_name][range_key] = entry
                continue 
            
            # Process "Furniture Chainage report" sheet for other files
            df = pd.read_excel(file_path, sheet_name="Furniture Chainage report", skiprows=7)
            df.columns = df.columns.str.strip()

            if road_name not in furniture_chainage_report:
                furniture_chainage_report[road_name] = {}

            for _, row in df.iterrows():
                if pd.notna(row['From']) and pd.notna(row['To']):
                    from_value = int(row['From'])
                    to_value = int(row['To'])
                    range_key = f"{from_value} - {to_value}"

                    entry = {
                        "Road Section": road_name,
                        "from": from_value,
                        "to": to_value,
                        "Chevron": {
                            "Avenue/Left": row.get('CHEVRON', 0),
                            "Median/Right": row.get('Unnamed: 11', 0)
                        },
                        "CAUTIONARY_WARNING_SIGNS": {
                            "Avenue/Left": row.get('CAUTIONARY_WARNING_SIGNS', 0),
                            "Median/Right": row.get('Unnamed: 13', 0),
                            "Overhead Signs": "NONE"
                        },
                        "HAZARD": {
                            "Avenue/Left": row.get('HAZARD', 0),
                            "Median/Right": row.get('Unnamed: 15', 0)
                        },
                        "PROHIBITORY_MANDATORY_SIGNS": {
                            "Avenue/Left": row.get('PROHIBITORY_MANDATORY_SIGNS', 0),
                            "Median/Right": row.get('Unnamed: 17', 0),
                            "Overhead Signs": "NONE"
                        },
                        "INFORMATORY_SIGNS": {
                            "Avenue/Left": row.get('INFORMATORY_SIGNS', 0),
                            "Median/Right": row.get('Unnamed: 19', 0),
                            "Overhead Signs": "NONE"
                        }
                    }
                    furniture_chainage_report[road_name][range_key] = entry

    with open(output_json_path, "w") as json_file:
        json.dump(furniture_chainage_report, json_file, indent=4)

    print("JSON file created successfully at:", output_json_path)

generate_json_from_folder("C:\\Users\\manav\\Desktop\\formatted_excel_script\\MCW")
