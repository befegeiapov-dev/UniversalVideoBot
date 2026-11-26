
import os
from pathlib import Path

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
OWNER_ID = int(os.getenv("OWNER_ID", "0"))

API_ID = int(os.getenv("API_ID", "0"))
API_HASH = os.getenv("API_HASH", "")

MAX_FILE_SIZE = 49 * 1024 * 1024

DOWNLOAD_DIR = Path("/tmp/video_downloads")
DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)
