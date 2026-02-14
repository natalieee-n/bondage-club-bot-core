import asyncio
import json
import os

from dotenv import load_dotenv
from bondage_club_bot_core import BCBot

load_dotenv()


class BasicBot(BCBot):
    async def customized_event_handler(self, data):
        return


with open("chatroom_config.json", "r") as f:
    chatroom_config = json.load(f)


bot_test = BasicBot(
    username=os.getenv("BC_USERNAME", ""),
    password=os.getenv("BC_PASSWORD", ""),
    chatroom_settings=chatroom_config,
    appearance_code=os.getenv("APPEARANCE_CODE", ""),
)

asyncio.run(bot_test.run())
