import asyncio
import json
import os
import traceback
import urllib.request
from pathlib import Path

from dotenv import load_dotenv
from bondage_club_bot_core import BCBot

BASE_DIR = Path(__file__).resolve().parent

load_dotenv(BASE_DIR / ".env")


class BasicBot(BCBot):
    async def customized_event_handler(self, data):
        return


def send_error_to_discord(error_text: str) -> None:
    webhook_url = os.getenv("DISCORD_WEBHOOK_URL", "").strip()
    if not webhook_url:
        return

    message = (
        "BCBot error\n"
        f"```{error_text[-1700:]}```"
    )
    payload = json.dumps({"content": message}).encode("utf-8")
    request = urllib.request.Request(
        webhook_url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=5):
            pass
    except Exception:
        # Do not mask the original bot error if webhook sending fails.
        pass


with open(BASE_DIR / "chatroom_config.json", "r") as f:
    chatroom_config = json.load(f)


bot_test = BasicBot(
    username=os.getenv("BC_USERNAME", ""),
    password=os.getenv("BC_PASSWORD", ""),
    chatroom_settings=chatroom_config,
    appearance_code=os.getenv("APPEARANCE_CODE", ""),
)

try:
    asyncio.run(bot_test.run())
except Exception:
    send_error_to_discord(traceback.format_exc())
    raise
