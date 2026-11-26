
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

    if "tiktok.com" in url and "/photo/" in url:
        status = await message.answer("⏳ Скачиваю фото...")
        try:
            imgs = scrape_tiktok_photos(url)
            if not imgs:
                await status.edit_text("❌ Фото не найдены.")
                return
            import aiohttp
            paths = []
            for i, img_url in enumerate(imgs):
                p = DOWNLOAD_DIR / f"photo{i}.jpg"
                async with aiohttp.ClientSession() as s:
                    async with s.get(img_url) as resp:
                        p.write_bytes(await resp.read())
                paths.append(p)
            await status.edit_text("📤 Отправляю фото...")
            for p in paths:
                await message.answer_photo(photo=FSInputFile(p))
                p.unlink(missing_ok=True)
            await status.delete()
        except Exception as error:
            logging.exception("Photo error")
            await status.edit_text(f"❌ Ошибка: {str(error)[:500]}")
        return

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


import json, re
from curl_cffi import requests as cffi_requests

def scrape_tiktok_photos(url):
    r = cffi_requests.get(url, impersonate="chrome", timeout=30)
    m = re.search(r'<script id="__UNIVERSAL_DATA_FOR_REHYDRATION__" type="application/json">(.*?)</script>', r.text, re.S)
    if not m:
        return []
    data = json.loads(m.group(1))
    imgs = []
    def walk(o):
        if isinstance(o, dict):
            for k, v in o.items():
                if k == "imagePost" and isinstance(v, dict):
                    for im in v.get("images", []):
                        urls = im.get("imageURL", {}).get("urlList", [])
                        if urls:
                            imgs.append(urls[0])
                walk(v)
        elif isinstance(o, list):
            for x in o:
                walk(x)
    walk(data)
    return imgs
    return web.Response(text="Video Downloader Bot is running!")


async def keep_alive():
    import aiohttp, os, asyncio
    url = os.getenv("RENDER_EXTERNAL_URL", f"http://localhost:{os.getenv('PORT','10000')}")
    while True:
        try:
            async with aiohttp.ClientSession() as s:
                await s.get(url + "/")
        except Exception:
            pass
        await asyncio.sleep(300)


async def main():
    asyncio.create_task(keep_alive())

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
