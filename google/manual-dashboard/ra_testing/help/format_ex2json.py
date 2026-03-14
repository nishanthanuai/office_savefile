import pandas as pd
import json

excel_file = 'C:\\Users\\manav\\Desktop\\formatted_excel_script\\MCW\\Porbandar-Dwarka (Package VIII) LHS MCW.xlsx'
df = pd.read_excel(excel_file, sheet_name="Furniture Chainage report", skiprows=7)

road_name = "Main Carriage Way LHS" if "LHS MCW" in excel_file else "Main Carriage Way RHS" if "RHS MCW" in excel_file else ""
print("Columns in the Excel file:", df.columns)

df.columns = df.columns.str.strip()

furniture_chainage_report = {road_name: {}}

for _, row in df.iterrows():
    if pd.notna(row['From']) and pd.notna(row['To']):
        from_value = int(row['From'])
        to_value = int(row['To'])

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


        range_key = f"{from_value} - {to_value}"
        furniture_chainage_report[road_name][range_key] = entry

output_json = furniture_chainage_report


with open("furniture_chainage_report.json", "w") as json_file:
    json.dump(output_json, json_file, indent=4)

print("JSON file created successfully.")
 