import Step_1 as p1
import Step_2 as p2
import Step_3 as p3
import os
import sys

class Submodule:
    """Submodule for running the Excel data extraction pipeline sequentially"""

    def __init__(
        self,
        BASE_FOLDER="Report",
        headers=None,
        api_base_url="https://ndd.roadathena.com/api/surveys/roads/",
        file_base_url="https://ndd.roadathena.com",
    ):
        if headers is None:
            headers = {"Security-Password": "admin@123"}
            
        self.BASE_FOLDER = BASE_FOLDER
        self.headers = headers
        self.api_base_url = api_base_url
        self.file_base_url = file_base_url

        if not os.path.isdir(self.BASE_FOLDER):
            print(f"❌ Error: {self.BASE_FOLDER} is not a valid directory.")
            sys.exit(1)

    def step_one(self):
        print("\n🚀 Starting Step 1: Downloading & Updating JSON data...")
        p1.start_update_json(
            base_folder=self.BASE_FOLDER,
            headers=self.headers,
            api_base_url=self.api_base_url,
            file_base_url=self.file_base_url,
        )

    def step_two(self):
        print("\n🚀 Starting Step 2: Extracting Assets and Formatting Text...")
        p2.main(self.BASE_FOLDER)

    def step_three(self):
        print("\n🚀 Starting Step 3: Generating PDF Reports...")
        p3.process_folder(self.BASE_FOLDER)

    def execute_sequence(self):
        print("Starting Sequential Execution Pipeline...")
        self.step_one()
        self.step_two()
        self.step_three()
        print("\n✅ All 3 Steps Executed Successfully!")


if __name__ == "__main__":
    # If a folder was provided in command line arguments, use it
    folder_to_process = sys.argv[1] if len(sys.argv) > 1 else "Report"
    
    mdl = Submodule(BASE_FOLDER=folder_to_process)

    try:
        mdl.execute_sequence()
    except Exception as e:
        print(f"\n❌ AN ERROR OCCURRED: {e}")
        sys.exit(1)
