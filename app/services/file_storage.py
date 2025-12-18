import os
import uuid
from fastapi import UploadFile

BASE_DIR = "app/uploads"

def save_file(file: UploadFile, folder: str) -> str:
    os.makedirs(f"{BASE_DIR}/{folder}", exist_ok=True)

    filename = f"{uuid.uuid4()}_{file.filename}"
    file_path = f"{BASE_DIR}/{folder}/{filename}"

    with open(file_path, "wb") as buffer:
        buffer.write(file.file.read())

    return file_path
