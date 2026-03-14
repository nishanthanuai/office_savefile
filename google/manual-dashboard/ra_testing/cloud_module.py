"""
cloud_module.py
===============
NISHANT KAGRA

This module provides a complete utility layer for interacting with an
Amazon S3 bucket using the boto3 SDK.

It is designed to:
- Upload individual files to S3
- Upload paired image and JSON annotation files to predefined S3 paths
- Download individual files from S3
- Download all files from a given S3 "folder" (prefix)
- List objects stored under a specific prefix
- Delete objects from the S3 bucket

The module relies on environment variables for AWS credentials and
configuration, which are loaded using python-dotenv.

Required environment variables:
- AWS_ACCESS_KEY_ID
- AWS_SECRET_ACCESS_KEY
- AWS_S3_REGION_NAME
- AWS_STORAGE_BUCKET_NAME

This module is framework-agnostic and can be safely used in:
- Django / Flask backends
- CLI scripts
- Data pipelines
- Background workers
- Standalone Python programs

All filesystem paths are handled using pathlib.Path for portability
across Linux, macOS, and Windows.
"""

# ------------------------------------------------------------------ script ----------------------
import os
import boto3
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# ----------------------------------------------------------------- S3 SETUP ----------------------


s3 = boto3.client(
    "s3",
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
    aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
    region_name=os.getenv("AWS_S3_REGION_NAME"),
)
bucket_name = os.getenv("AWS_STORAGE_BUCKET_NAME")


# ---------------------------------------------------------------- UPLOAD FUNCTIONS ----------------------
def upload_file(local_path: Path, s3_path: str):
    """
    Upload a single file to S3.
    """
    try:
        with open(local_path, "rb") as f:
            s3.put_object(Bucket=bucket_name, Key=s3_path, Body=f)
        print(f"✅ Uploaded {local_path} → {s3_path}")
    except Exception as e:
        print(f"❌ Upload failed for {local_path}:", e)


# ---------------------------------------------------------------- upload both image and json ----------------
def sort_and_upload_files(img_file: Path, json_file: Path):
    """
    Upload one image and its corresponding JSON file to S3.
    """
    img_s3_path = f"anotationdata_test/data/images/{img_file.name}"
    json_s3_path = f"anotationdata_test/data/json_data/{json_file.name}"

    upload_file(img_file, img_s3_path)
    upload_file(json_file, json_s3_path)


# ------------------------------------------------------------------- DOWNLOAD FUNCTIONS ----------------------
def download_file(s3_path: str, local_path: Path):
    """
    Download a single file from S3 to local path.
    """
    try:
        os.makedirs(local_path.parent, exist_ok=True)
        s3.download_file(bucket_name, s3_path, str(local_path))
        print(f"✅ Downloaded {s3_path} → {local_path}")
    except Exception as e:
        print(f"❌ Download failed for {s3_path}:", e)


def download_folder(s3_folder: str, local_folder: Path):
    """
    Download all files from a given S3 folder (prefix) to a local folder.
    """
    os.makedirs(local_folder, exist_ok=True)
    paginator = s3.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=bucket_name, Prefix=s3_folder):
        for obj in page.get("Contents", []):
            s3_key = obj["Key"]
            filename = os.path.basename(s3_key)
            if not filename:  # skip "folders"
                continue
            download_file(s3_key, local_folder / filename)


# ---------------------------------------------------------------method to see the data and directory inside the s3-----------
def list_s3_files(prefix=""):
    """
    List all files in an S3 bucket under a given prefix (folder).
    """
    paginator = s3.get_paginator("list_objects_v2")
    all_files = []

    for page in paginator.paginate(Bucket=bucket_name, Prefix=prefix):
        for obj in page.get("Contents", []):
            all_files.append(obj["Key"])

    return all_files


# ------------------------------------------------------------------delete method (access denied) -----------------
def delete_file(s3_key):
    """
    Delete a single file from S3.
    :param s3_key: Full key of the file in S3
    """
    try:
        s3.delete_object(Bucket=bucket_name, Key=s3_key)
        print(f"✅ Deleted {s3_key}")
    except Exception as e:
        print(f"❌ Failed to delete {s3_key}:", e)


# ------------------------------------------------------------------------------
# -------------------------------------------------------------------------------
# -------------------------------------------------------------------------------
# -------------------------------------------------------------------------------
# -------------------------------------------------------------------------------
# -------------------------------------------------------------------------------


# ----------------------Testing the MAIN SCRIPT ----------------------
if __name__ == "__main__":
    BASE_DIR = Path(__file__).resolve().parent / "media"
    # annotated_img = BASE_DIR / "annotated_images"
    # annotated_json = BASE_DIR / "annotations_json"

    # img_files = [f for f in annotated_img.iterdir() if f.is_file()]
    # json_files = [f for f in annotated_json.iterdir() if f.is_file()]

    # # Upload all image + JSON pairs
    # for img, json_file in zip(img_files, json_files):
    #     sort_and_upload_files(img, json_file)

    # # Example: Download all images from a folder
    # download_folder("anotationdata_test/data/DATASET /", BASE_DIR / "downloaded_datasetimg")

    # files = list_s3_files("anotationdata_test/data/")
    # for f in files:
    #     print(f)

    # delete_file("anotationdata_test/data/hello.txt")

    # os.system("clear")

    # files = list_s3_files("anotationdata_test/data/DATASET/")
    # for f in files:
    #     print(f)


    # directory structure inside bucket

    # anotationdata_test
    #                       data
    #                               DATASET
