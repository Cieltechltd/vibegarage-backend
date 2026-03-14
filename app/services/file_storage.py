import os
import uuid
import io
from fastapi import UploadFile
from app.core.config import settings 
from pydub import AudioSegment  

BASE_DIR = "app/uploads"

def save_file(file: UploadFile, folder: str) -> str:
    
    target_folder = os.path.join(BASE_DIR, folder)
    os.makedirs(target_folder, exist_ok=True)

    filename = f"{uuid.uuid4()}_{file.filename}"
    file_path = os.path.join(target_folder, filename)

    
    file_content = file.file.read()

    
    with open(file_path, "wb") as buffer:
        buffer.write(file_content)

   
    if folder == "audio":
        generate_preview(file_content, filename)

    return file_path

def generate_preview(audio_bytes: bytes, original_filename: str):
    
    preview_dir = os.path.join(BASE_DIR, "previews")
    os.makedirs(preview_dir, exist_ok=True)

    try:
        
        audio = AudioSegment.from_file(io.BytesIO(audio_bytes))
        
        fifteen_seconds = 15 * 1000
        preview = audio[:fifteen_seconds]
        
        preview_path = os.path.join(preview_dir, f"preview_{original_filename}")
        
    
        preview.export(preview_path, format="mp3")
    except Exception as e:
        print(f"Error generating preview for {original_filename}: {e}")
