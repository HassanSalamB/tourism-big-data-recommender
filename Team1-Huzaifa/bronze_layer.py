import os
import json
import shutil
from zipfile import ZipFile
import rarfile


# change path according to your project

DOWNLOADS_FILE = r"D:\tourism_DE_project\bronze\data\data.rar" 
BRONZE_PATH = r"D:\holiday_project\data\bronze\datatourisme\objects"

os.makedirs(BRONZE_PATH, exist_ok=True)


# Extract Function

def extract_file(file_path):
    if file_path.endswith(".zip"):
        print("Extracting ZIP...")
        with ZipFile(file_path, 'r') as zip_ref:
            zip_ref.extractall(BRONZE_PATH)

    elif file_path.endswith(".rar"):
        print("Extracting RAR...")
        with rarfile.RarFile(file_path) as rf:
            rf.extractall(BRONZE_PATH)

    else:
        print("Unsupported file format")


# Run extraction

extract_file(DOWNLOADS_FILE)
print("Extraction complete.")


# Validate JSON files

valid_files = 0
invalid_files = 0

for root, _, files in os.walk(BRONZE_PATH):
    for file in files:
        if not file.endswith(".json"):
            continue

        file_path = os.path.join(root, file)

        try:
            with open(file_path, encoding="utf-8") as f:
                json.load(f)
            valid_files += 1

        except:
            invalid_files += 1

print(f"Valid files: {valid_files}")
print(f"Invalid files: {invalid_files}")