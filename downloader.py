
import asyncio
import logging
import shutil
from pathlib import Path

import yt_dlp

from config import DOWNLOAD_DIR, MAX_FILE_SIZE

logger = logging.getLogger(__name__)


def download_sync(url):
    # Проверяем наличие JavaScript-движка Deno
    deno_path = shutil.which("deno")

    if deno_path:
        logger.info("Deno найден: %s", deno_path)
    else:
        logger.error("Deno НЕ найден в PATH!")

    logger.info("yt-dlp version: %s", yt_dlp.version.__version__)

    Path(DOWNLOAD_DIR).mkdir(parents=True, exist_ok=True)

    options = {
        "format": "best[ext=mp4]/best",
        "outtmpl": str(DOWNLOAD_DIR / "%(id)s.%(ext)s"),
        "merge_output_format": "mp4",
        "noplaylist": True,

        # Подробная диагностика
        "quiet": False,
        "verbose": True,
        "no_warnings": False,

        "socket_timeout": 30,
        "retries": 3,
        "fragment_retries": 3,
        "max_filesize": MAX_FILE_SIZE,

    }

    with yt_dlp.YoutubeDL(options) as ydl:
        info = ydl.extract_info(url, download=True)

        filepath = Path(ydl.prepare_filename(info))

        if not filepath.exists():
            filepath = filepath.with_suffix(".mp4")

        if not filepath.exists():
            raise RuntimeError(
                "Видео не найдено после загрузки."
            )

        if filepath.stat().st_size > MAX_FILE_SIZE:
            filepath.unlink(missing_ok=True)
            raise ValueError(
                "Видео слишком большое (больше 49 МБ)."
            )

        logger.info("Видео успешно загружено: %s", filepath)

        return filepath


async def download_video(url):
    return await asyncio.to_thread(download_sync, url)
