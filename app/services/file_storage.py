# import os
# import uuid
# import io
# from fastapi import UploadFile
# from app.core.config import settings 
# from pydub import AudioSegment  
# from supabase import create_client, Client


# supabase_url = settings.SUPABASE_URL
# supabase_key = settings.SUPABASE_KEY
# supabase: Client = create_client(supabase_url, supabase_key)

# BASE_DIR = "app/uploads"
# BUCKET_NAME = "vibegarage"

# def save_file(file: UploadFile, folder: str) -> str:
    
#     target_folder = os.path.join(BASE_DIR, folder)
#     os.makedirs(target_folder, exist_ok=True)

#     filename = f"{uuid.uuid4()}_{file.filename}"
#     file_path = os.path.join(target_folder, filename)

    
#     file.file.seek(0)  
#     file_content = file.file.read()

    
#     with open(file_path, "wb") as buffer:
#         buffer.write(file_content)

    
#     supabase_destination_path = f"app/uploads/{folder}/{filename}"
    
#     try:
#         supabase.storage.from_(BUCKET_NAME).upload(
#             path=supabase_destination_path,
#             file=file_content,
#             file_options={"content-type": file.content_type}
#         )
#     except Exception as e:
#         print(f"Supabase Storage Upload Failed for {filename}: {e}")
        
#     if folder == "audio":
#         generate_preview(file_content, filename)

    
#     return f"app/uploads/{folder}/{filename}"


# def generate_preview(audio_bytes: bytes, original_filename: str):
#     preview_dir = os.path.join(BASE_DIR, "previews")
#     os.makedirs(preview_dir, exist_ok=True)

#     try:
#         audio = AudioSegment.from_file(io.BytesIO(audio_bytes))
        
#         fifteen_seconds = 15 * 1000
#         preview = audio[:fifteen_seconds]
        
#         preview_filename = f"preview_{original_filename}"
#         preview_path = os.path.join(preview_dir, preview_filename)
        
        
#         preview.export(preview_path, format="mp3")

        
#         with open(preview_path, "rb") as f:
#             preview_bytes = f.read()
            
#         supabase.storage.from_(BUCKET_NAME).upload(
#             path=f"app/uploads/previews/{preview_filename}",
#             file=preview_bytes,
#             file_options={"content-type": "audio/mpeg"}
#         )
#     except Exception as e:
#         print(f"Error generating preview for {original_filename}: {e}")

import os
import uuid
import io
import asyncio
from fastapi import UploadFile
from app.core.config import settings 
from pydub import AudioSegment  
from supabase import create_client, Client

supabase_url = settings.SUPABASE_URL
supabase_key = settings.SUPABASE_KEY
supabase: Client = create_client(supabase_url, supabase_key)

BASE_DIR = "app/uploads"
BUCKET_NAME = "vibegarage"

async def save_file(file: UploadFile, folder: str) -> str:
    target_folder = os.path.join(BASE_DIR, folder)
    os.makedirs(target_folder, exist_ok=True)

    filename = f"{uuid.uuid4()}_{file.filename}"
    file_path = os.path.join(target_folder, filename)

    await file.seek(0)
    file_content = await file.read()

    with open(file_path, "wb") as buffer:
        buffer.write(file_content)

    supabase_destination_path = f"app/uploads/{folder}/{filename}"
    
    try:
        supabase.storage.from_(BUCKET_NAME).upload(
            path=supabase_destination_path,
            file=file_content,
            file_options={"content-type": file.content_type}
        )
    except Exception as e:
        print(f"Supabase Storage Upload Failed for {filename}: {e}")
        
    if folder == "audio":
        asyncio.create_task(
            asyncio.to_thread(generate_preview, file_content, filename)
        )
    return f"{supabase_url}/storage/v1/object/public/{BUCKET_NAME}/{supabase_destination_path}"


def generate_preview(audio_bytes: bytes, original_filename: str):
    preview_dir = os.path.join(BASE_DIR, "previews")
    os.makedirs(preview_dir, exist_ok=True)

    preview_filename = f"preview_{original_filename}"
    preview_path = os.path.join(preview_dir, preview_filename)

    try:
        audio = AudioSegment.from_file(io.BytesIO(audio_bytes))
        
        fifteen_seconds = 15 * 1000
        preview = audio[:fifteen_seconds]
        
        preview.export(preview_path, format="mp3")

        with open(preview_path, "rb") as f:
            preview_bytes = f.read()
            
        supabase.storage.from_(BUCKET_NAME).upload(
            path=f"app/uploads/previews/{preview_filename}",
            file=preview_bytes,
            file_options={"content-type": "audio/mpeg"}
        )
        
        if os.path.exists(preview_path):
            os.remove(preview_path)
            
    except Exception as e:
        print(f"Error generating preview for {original_filename}: {e}")
