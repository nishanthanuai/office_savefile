import total_raods as tr
import requests
from pathlib import Path
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

base_dir = Path(__file__).resolve().parent
url = "https://ndd.roadathena.com/17730/video/play/?surveyType=pavement"

logging.basicConfig(
    filename=base_dir / "video_check.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

MAX_WORKERS = 2  # adjust based on available resources / machine capacity

def run(survey_id,road_id:list=None):
    if survey_id:
        road_ids = tr.main(survey_id)
    else:
        road_ids = road_id
    
    for ids in road_ids:
        url = f"https://ndd.roadathena.com/{survey_id}/video/play/?surveyType=pavement"
        response = requests.get(url)
        
        if response.ok:
            logging.info(f"Surveyroad {ids} found in API response")
        else:
            logging.info(f"Surveyroad {ids} not found in API response")
            
        
    
        


if __name__ == "__main__":
    EMAIL = "Nhai@ra.com"
    PASSWORD = "81Sp3jfJ1^hK"

    # put all survey ids in this list
    surveyids = [
        489,
        496,
        493,
        495,
        490,
        531,
        535,
        529,
        533,
        493,
        524,
        526,
        521,
        544,
        543,
        497,
        538,
        523,
    ]
    
    for sur in surveyids:
        run(survey_id=sur,road_id=None)