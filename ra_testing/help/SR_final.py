import pandas as pd
import json
import os
import re
import math

def generate_json_from_folder(folder_path, output_json_path="SR_final.json"):
    furniture_chainage_report = {
        "Service Road RHS 1 (SRR1)": {},
        "Service Road RHS 2 (SRR2)": {},
        "Service Road RHS 3 (SRR3)": {}
    }
    
    srl_toggle = True  # Toggle to switch between SRL1 and SRL2
    
    for file_name in os.listdir(folder_path):
        if file_name.endswith(".xlsx"):
            file_path = os.path.join(folder_path, file_name)
            
            df = pd.read_excel(file_path, sheet_name="Furniture Chainage report", skiprows=7)
            df.columns = df.columns.str.strip()
            
            for _, row in df.iterrows():
                if pd.notna(row['From']) and pd.notna(row['To']):
                    from_value = int(row['From'])
                    to_value = int(row['To'])
                    range_key = f"{from_value} - {to_value}"
                    
                    # road_name = "Service Road RHS 1 (SRR1)" if srl_toggle else "Service Road RHS 2 (SRR2)" 
                    if srl_toggle:
                        road_name = "Service Road RHS 1 (SRR1)"
                    elif not srl_toggle:
                        road_name = "Service Road RHS 2 (SRR2)"
                    else:
                        road_name = "Service Road RHS 3 (SRR3)"

                    
                    
                    srl_toggle = not srl_toggle  # Switch between SRL1 and SRL2
                    
                    entry = {
                        "Road Section": road_name,
                        "from": from_value,
                        "to": to_value,
                        "CHEVRON": {
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


# # Example usage
# folder_path = r"C:\\Users\\manav\\Desktop\\excel_folder_final_maker\\formatted_excel_script\\SR"
# generate_json_from_folder(folder_path)