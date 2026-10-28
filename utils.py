import os
import uuid
from werkzeug.utils import secure_filename
from config import Config

def allowed_file(filename):
    """Verifies that the uploaded file extension is allowed."""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in Config.ALLOWED_EXTENSIONS

def generate_unique_filename(original_filename):
    """
    Creates a secure, sanitized, and uniquely prefixed filename
    to avoid collisions and path traversal attacks.
    """
    base_name = secure_filename(original_filename)
    if not base_name:
        base_name = "upload.png"
    unique_id = uuid.uuid4().hex[:10]
    return f"{unique_id}_{base_name}"

def ensure_project_directories():
    """Ensures all necessary project directories exist."""
    directories = [
        Config.UPLOAD_FOLDER,
        Config.REPORT_FOLDER,
        Config.SAMPLE_FOLDER,
        Config.DATABASE_FOLDER
    ]
    for directory in directories:
        os.makedirs(directory, exist_ok=True)
