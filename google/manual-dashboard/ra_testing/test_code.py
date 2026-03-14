import json
import os

model_type = "furniture"
survey_id = 556
road_id = 18091

folder_path = "/home/hanuai/Nishant_kagra_code/google/manual-dashboard/media/Model_Testing/ndd.roadathena.com/"
file_path = os.path.join(folder_path,f"{model_type}/{survey_id}/{road_id}/jsonfile/manual_{road_id}.json")

if os.path.exists(file_path):
    with open(file_path,"r") as f:
        data = json.load(f)

        print(data) 