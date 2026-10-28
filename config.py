import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

class Config:
    """Application configuration for Legal Metrology Compliance System."""
    
    SECRET_KEY = os.environ.get("SECRET_KEY", "legal-metrology-demo-secret-key-2026")
    
    # Upload and report storage paths
    UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
    REPORT_FOLDER = os.path.join(BASE_DIR, "reports")
    SAMPLE_FOLDER = os.path.join(BASE_DIR, "static", "samples")
    DATABASE_FOLDER = os.path.join(BASE_DIR, "database")
    DATABASE_PATH = os.path.join(DATABASE_FOLDER, "rules.db")
    
    # Upload constraints
    ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB max upload size
    
    # Tesseract OCR Windows Configuration
    # Standard 64-bit & 32-bit Windows installer paths
    DEFAULT_TESSERACT_PATHS = [
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\Programs\Tesseract-OCR\tesseract.exe"),
    ]
    
    # Allow override via environment variable TESSERACT_PATH
    CUSTOM_TESSERACT_PATH = os.environ.get("TESSERACT_PATH", "")
    
    @classmethod
    def get_tesseract_cmd(cls):
        """Returns the verified Tesseract binary path or None if not found."""
        if cls.CUSTOM_TESSERACT_PATH and os.path.isfile(cls.CUSTOM_TESSERACT_PATH):
            return cls.CUSTOM_TESSERACT_PATH
        for path in cls.DEFAULT_TESSERACT_PATHS:
            if os.path.isfile(path):
                return path
        return None
