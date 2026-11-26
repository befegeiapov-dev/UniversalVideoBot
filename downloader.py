
import asyncio
from pathlib import Path
import yt_dlp

from config import DOWNLOAD_DIR, MAX_FILE_SIZE


def download_sync(url):
    options = {
        "format": "best[ext=mp4]/best",
        "outtmpl": str(DOWNLOAD_DIR / "%(id)s.%(ext)s"),
        "merge_output_format": "mp4",
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
        "socket_timeout": 30,
        "retries": 2,
        "max_filesize": MAX_FILE_SIZE,
    }

    with yt_dlp.YoutubeDL(options) as ydl:
        info = ydl.extract_info(url, download=True)
        filepath = Path(ydl.prepare_filename(info))

        if not filepath.exists():
            filepath = filepath.with_suffix(".mp4")

        if not filepath.exists():
            raise RuntimeError("Видео не найдено после загрузки.")

        if filepath.stat().st_size > MAX_FILE_SIZE:
            filepath.unlink(missing_ok=True)
            raise ValueError("Видео слишком большое (больше 49 МБ).")

        return filepath


async def download_video(url):
    return await asyncio.to_thread(download_sync, url)
