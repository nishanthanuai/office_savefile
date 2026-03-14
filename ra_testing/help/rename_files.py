import os
import re

def rename_files(folder_path):

    for filename in os.listdir(folder_path):
        match = re.match(r"^(.*) SRR (\d+)\.xlsx$", filename)
        # match = re.match(r"^(.*) SRR (\d+)_formatted\.xlsx$", filename)

        if match:
            base_name = match.group(1)
            number = match.group(2)

            # Create the new name in the required format
            new_name = f"{base_name} SR{number} RHS.xlsx"

            # Construct full file paths
            old_file_path = os.path.join(folder_path, filename)
            new_file_path = os.path.join(folder_path, new_name)

            # Rename the file
            os.rename(old_file_path, new_file_path)
            print(f"Renamed: {filename} -> {new_name}")

# Example usage:
folder_path = "C:/Users/manav/Desktop/excel_folder_final_maker/formatted_excel_script/SR"  # Replace with the path to your folder
rename_files(folder_path)