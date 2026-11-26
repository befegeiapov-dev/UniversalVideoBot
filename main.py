
import asyncio
import logging
import re
from pathlib import Path
from urllib.parse import urlparse

from aiohttp import web

from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.types import Message, FSInputFile

from config import BOT_TOKEN, OWNER_ID, MAX_FILE_SIZE
from downloader import download_video

logging.basicConfig(level=logging.INFO)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

URL_PATTERN = re.compile(r"https?://\S+")

SUPPORTED_DOMAINS = (
    "tiktok.com",
    "youtube.com",
    "youtu.be",
    "instagram.com",
    "twitter.com",
    "x.com",
    "reddit.com",
    "redd.it",
    "facebook.com",
    "fb.watch",
    "vimeo.com",
)


def valid_url(url):
    try:
        parsed = urlparse(url)
        host = (parsed.hostname or "").lower().removeprefix("www.")

        return (
            parsed.scheme in ("http", "https")
            and any(
                host == domain or host.endswith("." + domain)
                for domain in SUPPORTED_DOMAINS
            )
        )
    except Exception:
        return False


@dp.message(CommandStart())
async def start(message: Message):
    if not message.from_user or message.from_user.id != OWNER_ID:
        return

    await message.answer(
        "Привет! Я Video Downloader Bot.\n\n"
        "Отправь ссылку на видео из TikTok, YouTube, "
        "Instagram, Reddit или других поддерживаемых сайтов.\n\n"
        "Я скачаю видео и отправлю его тебе."
    )


@dp.message(F.text)
async def handle_link(message: Message):
    if not message.from_user or message.from_user.id != OWNER_ID:
        return

    match = URL_PATTERN.search(message.text)

    if not match:
        await message.answer("Отправь ссылку на видео.")
        return

    url = match.group(0).rstrip(".,!?)")

    if not valid_url(url):
        await message.answer("Этот сайт пока не поддерживается.")
        return

    status = await message.answer("⏳ Скачиваю видео...")

    filepath = None

    try:
        filepath = await download_video(url)

        if filepath.stat().st_size > MAX_FILE_SIZE:
            raise ValueError("Видео превышает лимит 49 МБ.")

        await status.edit_text("📤 Отправляю видео...")

        await message.answer_video(
            video=FSInputFile(filepath),
            caption="✅ Готово!",
            supports_streaming=True
        )

        await status.delete()

    except Exception as error:
        logging.exception("Download error")

        error_text = str(error)[:500]

        await status.edit_text(
            f"❌ Ошибка загрузки:\n{error_text}"
        )

    finally:
        if filepath and filepath.exists():
            filepath.unlink(missing_ok=True)


async def health(request):
    return web.Response(text="Video Downloader Bot is running!")


async def main():
    if not BOT_TOKEN or OWNER_ID == 0:
        raise RuntimeError("Не настроены BOT_TOKEN или OWNER_ID.")

    app = web.Application()
    app.router.add_get("/", health)

    runner = web.AppRunner(app)
    await runner.setup()

    port = int(__import__("os").getenv("PORT", 10000))

    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()

    try:
        await dp.start_polling(bot)
    finally:
        await runner.cleanup()
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
