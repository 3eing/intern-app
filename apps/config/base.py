from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = "change-me"
MAX_CONTENT_LENGTH = 3072 * 3072
UPLOAD_EXTENSIONS = [".csv", ".xlsx", ".xls"]

ROOT_DIR = BASE_DIR
UPLOAD_PATH = ROOT_DIR / "uploads"
GENERATED_PATH = ROOT_DIR / "generated"