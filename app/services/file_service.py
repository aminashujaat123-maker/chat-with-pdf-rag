"""
File service module.
Handles validation and saving of uploaded files.
Keeping this logic separate from routes so it can be reused
and tested independently of Flask.
"""

import os
import uuid
from werkzeug.utils import secure_filename
from app.config import UPLOAD_FOLDER, ALLOWED_EXTENSIONS, MAX_FILE_SIZE_MB
from app.logger import get_logger

logger = get_logger(__name__)


def is_allowed_file(filename: str) -> bool:
    """Check if the file has an allowed extension (.pdf for now)."""
    if "." not in filename:
        return False
    extension = filename.rsplit(".", 1)[1].lower()
    return extension in ALLOWED_EXTENSIONS


def is_within_size_limit(file_stream) -> bool:
    """
    Check if the uploaded file is within the allowed size limit.
    Reads the stream to determine size, then resets the pointer
    back to the start so it can be read again later.
    """
    file_stream.seek(0, os.SEEK_END)
    size_in_bytes = file_stream.tell()
    file_stream.seek(0)  # reset pointer for later reads

    size_in_mb = size_in_bytes / (1024 * 1024)
    return size_in_mb <= MAX_FILE_SIZE_MB


def save_uploaded_file(file_storage) -> dict:
    """
    Save an uploaded file to the uploads folder with a unique name,
    to avoid collisions if two users upload files with the same name.

    Args:
        file_storage: Flask's FileStorage object from request.files.

    Returns:
        A dict with metadata about the saved file:
        {
            "original_filename": "notes.pdf",
            "stored_filename": "a1b2c3d4-notes.pdf",
            "file_path": "/absolute/path/to/uploads/a1b2c3d4-notes.pdf",
            "size_mb": 1.42
        }
    """
    original_filename = secure_filename(file_storage.filename)
    unique_id = uuid.uuid4().hex[:8]
    stored_filename = f"{unique_id}-{original_filename}"

    file_path = os.path.join(UPLOAD_FOLDER, stored_filename)

    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    file_storage.save(file_path)

    size_mb = round(os.path.getsize(file_path) / (1024 * 1024), 2)

    logger.info(
        f"File saved: {original_filename} -> {stored_filename} ({size_mb} MB)"
    )

    return {
        "original_filename": original_filename,
        "stored_filename": stored_filename,
        "file_path": file_path,
        "size_mb": size_mb
    }