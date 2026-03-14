import json
import openpyxl

def extract_bounds(chainage_range):
    """Extracts numeric bounds from a chainage range string (e.g., '381000 - 381500')"""
    try:
        start, end = map(int, chainage_range.split(" - "))
        return min(start, end), max(start, end) 
    except ValueError:
        return None, None

# Load JSON data
with open('C:\\Users\\manav\\Desktop\\excel_folder_final_maker\\formatted_excel_script\\CR\\CR_final.json', 'r') as json_file:
    data = json.load(json_file)

# Load Excel workbook and target sheet
excel_file_path = 'T4.xlsx'
workbook = openpyxl.load_workbook(excel_file_path)
sheet = workbook['Sheet1']

# Define the columns where each sign type will be placed
columns_mapping = {
    "Chevron": ["E", "F"],
    "CAUTIONARY_WARNING_SIGNS": ["I", "J", "K"],
    "HAZARD": ["G", "H"],
    "PROHIBITORY_MANDATORY_SIGNS": ["L", "M", "N"],
    "INFORMATORY_SIGNS": ["O", "P", "Q"]
}

for road_section, chainages in data.items():
    for chainage_range, details in chainages.items():
        from_chainage = details['from']
        to_chainage = details['to']
        match_string = f"{from_chainage} - {to_chainage}"
        reverse_match_string = f"{to_chainage} - {from_chainage}"

        prev_chainage = None  
        for row in range(7, sheet.max_row + 1):  
            excel_chainage = sheet[f'A{row}'].value  
            excel_road_section = sheet[f'B{row}'].value  

            if excel_chainage is None:
                excel_chainage = prev_chainage
            else:
                prev_chainage = excel_chainage  

            if excel_chainage is None:
                continue

            excel_start, excel_end = extract_bounds(excel_chainage)
            match_start, match_end = extract_bounds(match_string)
            
            # Check if both chainage range and road section match (including reverse chainage order)
            if (excel_road_section == road_section and
                ((excel_chainage == match_string or excel_chainage == reverse_match_string) or
                 (excel_start <= match_start <= excel_end and excel_start <= match_end <= excel_end))):
                
                # Populate data into the matched row
                sheet[f'C{row}'].value = from_chainage
                sheet[f'D{row}'].value = to_chainage

                
                for asset_type, columns in columns_mapping.items():
                    if asset_type in details:
                        asset_values = details[asset_type]
                        
                        # Populate Avenue/Left and Median/Right for each asset
                        if len(columns) >= 2:
                            sheet[f'{columns[0]}{row}'].value = asset_values.get('Avenue/Left', 0)
                            sheet[f'{columns[1]}{row}'].value = asset_values.get('Median/Right', 0)
                        
                        # Populate Overhead Signs if present
                        if len(columns) == 3 and "Overhead Signs" in asset_values:
                            sheet[f'{columns[2]}{row}'].value = asset_values["Overhead Signs"]

                break

# Save the updated workbook to a new file
updated_excel_file_path = '4 OF AHEMDABAD_GODHRA.xlsx'
workbook.save(updated_excel_file_path)

print(f"Updated data saved to {updated_excel_file_path}")
