import asyncio
import json
import os
import traceback
import urllib.request
from copy import deepcopy
from typing import Any, Dict, Optional

import socketio
from lzstring import LZString

from .utils.logger import get_logger
from .utils.socket_event_queue import SocketEventQueue

logger = get_logger(__name__)


class BCBot:
    def __init__(
        self,
        username: str,
        password: str,
        chatroom_settings: dict,
        appearance_code: str = None,
        server_url: str = "https://bondage-club-server.herokuapp.com/",
        origin: str = "https://www.bondage-europe.com",
    ):
        logger.info("Initializing bot...")
        self.sio = socketio.AsyncClient()
        self._register_handlers()

        self.event_queue = SocketEventQueue(self.sio)

        self.player: Dict[str, Any] = {}
        self.others: Dict[int, Dict[str, Any]] = {}
        self.appearance = self._decode_appearance(appearance_code)

        self.is_connected = False
        self.is_logged_in = False

        self.username = username
        self.password = password
        self.server_url = server_url
        self.origin = origin

        self.chatroom_settings = deepcopy(chatroom_settings)
        self.current_chatroom: Optional[Dict[str, Any]] = None
        self.chatroom_search_result: Optional[Dict[str, Any]] = None

        self._target_room_name = (self.chatroom_settings.get("Name") or "").strip()
        self._login_requested = False
        self._chatroom_search_requested = False
        self._chatroom_search_done = False
        self._chatroom_join_requested = False
        self._chatroom_join_response = None
        self._chatroom_create_requested = False
        self._appearance_reset_done = False

        logger.info("Bot initialized")

    def _decode_appearance(self, appearance_code: Optional[str]):
        if not appearance_code:
            return None
        try:
            raw = LZString.decompressFromBase64(appearance_code)
            if not raw:
                logger.warning("Appearance code decompress failed. Skip appearance reset.")
                return None
            return json.loads(raw)
        except Exception as exc:
            logger.warning("Invalid appearance code. Skip appearance reset: %s", exc)
            return None

    def _reset_chatroom_flow(self):
        self.current_chatroom = None
        self.chatroom_search_result = None
        self._chatroom_search_requested = False
        self._chatroom_search_done = False
        self._chatroom_join_requested = False
        self._chatroom_join_response = None
        self._chatroom_create_requested = False
        self._appearance_reset_done = False
        self.others.clear()

    def _register_handlers(self):
        self.sio.on("connect", self.on_connect)
        self.sio.on("disconnect", self.on_disconnect)
        self.sio.on("ServerInfo", self.on_ServerInfo)
        self.sio.on("CreationResponse", self.on_CreationResponse)
        self.sio.on("LoginResponse", self.on_LoginResponse)
        self.sio.on("LoginQueue", self.on_LoginQueue)
        self.sio.on("ForceDisconnect", self.on_ForceDisconnect)
        self.sio.on("ChatRoomSearchResult", self.on_ChatRoomSearchResult)
        self.sio.on("ChatRoomSearchResponse", self.on_ChatRoomSearchResponse)
        self.sio.on("ChatRoomCreateResponse", self.on_ChatRoomCreateResponse)
        self.sio.on("ChatRoomUpdateResponse", self.on_ChatRoomUpdateResponse)
        self.sio.on("ChatRoomSync", self.on_ChatRoomSync)
        self.sio.on("ChatRoomSyncMemberJoin", self.on_ChatRoomSyncMemberJoin)
        self.sio.on("ChatRoomSyncMemberLeave", self.on_ChatRoomSyncMemberLeave)
        self.sio.on("ChatRoomSyncRoomProperties", self.on_ChatRoomSyncRoomProperties)
        self.sio.on("ChatRoomSyncCharacter", self.on_ChatRoomSyncCharacter)
        self.sio.on("ChatRoomSyncReorderPlayers", self.on_ChatRoomSyncReorderPlayers)
        self.sio.on("ChatRoomSyncSingle", self.on_ChatRoomSyncSingle)
        self.sio.on("ChatRoomSyncExpression", self.on_ChatRoomSyncExpression)
        self.sio.on("ChatRoomSyncMapData", self.on_ChatRoomSyncMapData)
        self.sio.on("ChatRoomSyncPose", self.on_ChatRoomSyncPose)
        self.sio.on("ChatRoomSyncArousal", self.on_ChatRoomSyncArousal)
        self.sio.on("ChatRoomSyncItem", self.on_ChatRoomSyncItem)
        self.sio.on("ChatRoomMessage", self.on_ChatRoomMessage)
        self.sio.on("ChatRoomAllowItem", self.on_ChatRoomAllowItem)
        self.sio.on("ChatRoomGameResponse", self.on_ChatRoomGameResponse)
        self.sio.on("PasswordResetResponse", self.on_PasswordResetResponse)
        self.sio.on("AccountQueryResult", self.on_AccountQueryResult)
        self.sio.on("AccountBeep", self.on_AccountBeep)
        self.sio.on("AccountOwnership", self.on_AccountOwnership)
        self.sio.on("AccountLovership", self.on_AccountLovership)

    async def on_ServerInfo(self, data):
        logger.info("on_ServerInfo data: %s", data)

    async def on_CreationResponse(self, data):
        logger.info("on_CreationResponse data: %s", data)

    async def on_ForceDisconnect(self, data):
        logger.warning("on_ForceDisconnect received: %s", data)
        self.is_logged_in = False
        self._login_requested = False
        self._reset_chatroom_flow()
        if self.sio.connected:
            await self.sio.disconnect()

    async def on_ChatRoomCreateResponse(self, data):
        logger.info("on_ChatRoomCreateResponse data: %s", data)
        if data != "ChatRoomCreated":
            self._chatroom_create_requested = False
            if data == "RoomAlreadyExist":
                self._chatroom_search_requested = False
                self._chatroom_search_done = False

    async def on_ChatRoomUpdateResponse(self, data):
        logger.info("on_ChatRoomUpdateResponse data: %s", data)

    async def on_ChatRoomSyncMemberJoin(self, data):
        logger.info("on_ChatRoomSyncMemberJoin data: %s", data)
        character = data.get("Character")
        if isinstance(character, dict) and "MemberNumber" in character:
            self.others[character["MemberNumber"]] = character

    async def on_ChatRoomSyncRoomProperties(self, data):
        logger.info("on_ChatRoomSyncRoomProperties data: %s", data)
        if self.current_chatroom is None:
            self.current_chatroom = {}
        for key, value in data.items():
            if key != "SourceMemberNumber":
                self.current_chatroom[key] = value

    async def on_ChatRoomSyncReorderPlayers(self, data):
        logger.info("on_ChatRoomSyncReorderPlayers data: %s", data)
        if self.current_chatroom is None:
            self.current_chatroom = {}
        self.current_chatroom["PlayerOrder"] = data.get("PlayerOrder", [])

    async def on_ChatRoomSyncExpression(self, data):
        logger.info("on_ChatRoomSyncExpression data: %s", data)

    async def on_ChatRoomSyncMapData(self, data):
        logger.info("on_ChatRoomSyncMapData data: %s", data)

    async def on_ChatRoomSyncPose(self, data):
        logger.info("on_ChatRoomSyncPose data: %s", data)

    async def on_ChatRoomSyncArousal(self, data):
        logger.info("on_ChatRoomSyncArousal data: %s", data)

    async def on_ChatRoomAllowItem(self, data):
        logger.info("on_ChatRoomAllowItem data: %s", data)

    async def on_ChatRoomGameResponse(self, data):
        logger.info("on_ChatRoomGameResponse data: %s", data)

    async def on_PasswordResetResponse(self, data):
        logger.info("on_PasswordResetResponse data: %s", data)

    async def on_AccountBeep(self, data):
        logger.info("on_AccountBeep data: %s", data)

    async def on_AccountOwnership(self, data):
        logger.info("on_AccountOwnership data: %s", data)

    async def on_AccountLovership(self, data):
        logger.info("on_AccountLovership data: %s", data)

    async def connect(self):
        try:
            if self.sio.connected:
                self.is_connected = True
                return True

            logger.info("Connecting to server: %s", self.server_url)
            await self.sio.connect(
                self.server_url,
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; rv:102.0) Gecko/20100101 Firefox/102.0",
                    "Origin": self.origin,
                },
            )
            return True
        except Exception as e:
            if "Already connected" in str(e):
                logger.info("Already connected to server")
                self.is_connected = True
                return True
            logger.error("Failed to connect: %s", e, exc_info=True)
            return False

    async def disconnect(self):
        await self.event_queue.shutdown()
        if self.sio.connected:
            await self.sio.disconnect()
        logger.info("Disconnected from server")

    async def on_connect(self):
        logger.info("Socket connected")
        self.is_connected = True

    async def on_disconnect(self):
        logger.warning("Socket disconnected")
        self.is_connected = False
        self.is_logged_in = False
        self._login_requested = False
        self._reset_chatroom_flow()

    async def on_LoginResponse(self, data):
        logger.info("on_LoginResponse received")
        logger.debug("on_LoginResponse data: %s", data)

        self._login_requested = False
        if isinstance(data, dict) and "MemberNumber" in data:
            self.player = data
            self.is_logged_in = True
            logger.info("Login successful: %s(%s)", data.get("Name"), data.get("MemberNumber"))
            return

        self.player = {}
        self.is_logged_in = False
        logger.warning("Login failed: %s", data)

    async def on_ChatRoomSearchResponse(self, data):
        logger.info("on_ChatRoomSearchResponse data: %s", data)
        self._chatroom_join_response = data
        if data != "JoinedRoom":
            self._chatroom_join_requested = False
            self._chatroom_search_requested = False
            self._chatroom_search_done = False

    async def on_AccountQueryResult(self, data):
        logger.info("on_AccountQueryResult data: %s", data)

    def _send_error_to_discord(self, error_text: str) -> None:
        webhook_url = os.getenv("DISCORD_WEBHOOK_URL", "").strip()
        if not webhook_url:
            return

        message = "BCBot error\n" + f"```{error_text[-1700:]}```"
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
            logger.exception("Failed to send error to Discord webhook")

    async def on_ChatRoomMessage(self, data):
        logger.info(
            "on_ChatRoomMessage data received. Type: %s, Player: %s, Content: %s",
            data.get("Type"),
            data.get("Sender"),
            data.get("Content"),
        )
        try:
            await self.customized_event_handler(data)
        except Exception:
            logger.error("customized_event_handler failed", exc_info=True)
            self._send_error_to_discord(traceback.format_exc())

    async def on_ChatRoomSync(self, data):
        logger.info("on_ChatRoomSync data received")
        logger.debug("on_ChatRoomSync data: %s", data)

        self.current_chatroom = {k: v for k, v in data.items() if k != "Character"}
        self._chatroom_join_response = "JoinedRoom"

        chars = data.get("Character", [])
        member_count = len(chars) if isinstance(chars, list) else 1
        logger.info("Entered room %s, %s members in total", data.get("Name"), member_count)

        await self.on_ChatRoomSyncCharacter(data)

    async def on_ChatRoomSyncItem(self, data):
        logger.info("on_ChatRoomSyncItem data received")
        logger.debug("on_ChatRoomSyncItem data: %s", data)

        item = data.get("Item", {})
        target = item.get("Target")

        if not isinstance(target, int):
            logger.warning("Invalid ChatRoomSyncItem target: %s", target)
            return

        target_data = self.others.get(target)
        if not target_data:
            logger.warning("Item update target %s not in local room cache", target)
            return

        appearance = target_data.setdefault("Appearance", [])
        for idx, cur_item in enumerate(appearance):
            if cur_item.get("Group") == item.get("Group"):
                if item.get("Name"):
                    appearance[idx] = item
                else:
                    del appearance[idx]
                return

        if item.get("Name"):
            appearance.append(item)

    async def on_ChatRoomSyncMemberLeave(self, data):
        logger.info("on_ChatRoomSyncMemberLeave data: %s", data)

        member_number = data.get("SourceMemberNumber")
        self.others.pop(member_number, None)
        logger.info("Player left: %s", member_number)

        if member_number == self.player.get("MemberNumber"):
            self._reset_chatroom_flow()

    async def on_ChatRoomSearchResult(self, data):
        logger.info("on_ChatRoomSearchResult data received")
        logger.debug("on_ChatRoomSearchResult data: %s", data)

        self._chatroom_search_done = True
        self.chatroom_search_result = None

        if not isinstance(data, list):
            logger.warning("Unexpected chatroom search result type: %s", type(data))
            return

        target_name = self._target_room_name.upper()
        for room in data:
            if not isinstance(room, dict):
                continue
            if (room.get("Name") or "").upper() == target_name:
                self.chatroom_search_result = room
                break

        if self.chatroom_search_result:
            logger.info("Target room exists: %s", self.chatroom_search_result.get("Name"))
        else:
            logger.info("Target room not found: %s", self._target_room_name)

    async def on_ChatRoomSyncCharacter(self, data):
        logger.info("on_ChatRoomSyncCharacter data received")
        logger.debug("on_ChatRoomSyncCharacter data: %s", data)

        characters = data.get("Character")
        if characters is None:
            return
        if not isinstance(characters, list):
            characters = [characters]

        for char_data in characters:
            if not isinstance(char_data, dict) or "MemberNumber" not in char_data:
                continue
            logger.info("Update %s(%s)'s data", char_data.get("Name"), char_data.get("MemberNumber"))
            self.others[char_data["MemberNumber"]] = char_data

    async def on_ChatRoomSyncSingle(self, data):
        logger.info("on_ChatRoomSyncSingle data received")
        logger.debug("on_ChatRoomSyncSingle data: %s", data)
        await self.on_ChatRoomSyncCharacter(data)

    async def on_LoginQueue(self, data):
        logger.info("on_LoginQueue data: %s", data)

    async def login(self):
        if not self.username or not self.password:
            raise ValueError("BC username/password is empty")

        logger.info("Logging in using AccountName %s", self.username)
        await self.sio.emit(
            "AccountLogin",
            {
                "AccountName": self.username,
                "Password": self.password,
            },
        )
        self._login_requested = True

    async def search_chatroom(self, name, **kwargs):
        logger.info("Searching for chatroom %s", name)
        data = {
            "Query": name.upper(),
            "Language": "",
            "Space": "",
            "Game": "",
            "FullRooms": True,
            "ShowLocked": True,
        }
        data.update(kwargs)

        self.chatroom_search_result = None
        self._chatroom_search_done = False
        self._chatroom_search_requested = True

        await self.event_queue.put_event("ChatRoomSearch", data)

    async def create_chatroom(self, chatroom_settings: dict):
        data = deepcopy(chatroom_settings)
        admin_list = data.get("Admin")
        if not isinstance(admin_list, list):
            admin_list = []
            data["Admin"] = admin_list

        member_number = self.player.get("MemberNumber")
        if isinstance(member_number, int) and member_number not in admin_list:
            admin_list.append(member_number)

        logger.info("Creating chatroom %s", data.get("Name"))
        logger.debug("Chatroom data: %s", data)

        self._chatroom_create_requested = True
        await self.event_queue.put_event("ChatRoomCreate", data)

    async def join_chatroom(self, name):
        data = {"Name": name}
        logger.info("Joining chatroom %s", name)

        self._chatroom_join_requested = True
        self._chatroom_join_response = None
        await self.event_queue.put_event("ChatRoomJoin", data)

    async def reset_appearance(self):
        logger.info("Resetting appearance")
        if not self.appearance:
            logger.warning("No appearance data found. Skip reset.")
            self._appearance_reset_done = True
            return

        data = {
            "AssetFamily": "Female3DCG",
            "Appearance": self.appearance,
            "ItemPermission": 1,
        }
        await self.event_queue.put_event("AccountUpdate", data)
        self._appearance_reset_done = True

    async def send_to_chat(self, msg):
        logger.info("Sending message: %s", msg)
        data = {"Content": msg, "Type": "Chat", "Target": None}
        await self.event_queue.put_event("ChatRoomChat", data)

    async def customized_event_handler(self, data):
        logger.warning("No customized event handler found.")

    async def run(self):
        try:
            logger.info("Starting event queue")
            await self.event_queue.start()

            while True:
                if not self.is_connected:
                    await self.connect()
                    await asyncio.sleep(2)
                    continue

                if not self.is_logged_in:
                    if not self._login_requested:
                        await self.login()
                    await asyncio.sleep(2)
                    continue

                if not self.current_chatroom:
                    if not self._chatroom_search_requested and not self._chatroom_search_done:
                        await self.search_chatroom(self._target_room_name)
                        await asyncio.sleep(1)
                        continue

                    if not self._chatroom_search_done:
                        await asyncio.sleep(1)
                        continue

                    if self.chatroom_search_result:
                        if not self._chatroom_join_requested and self._chatroom_join_response is None:
                            await self.join_chatroom(self._target_room_name)
                    else:
                        if not self._chatroom_create_requested:
                            await self.create_chatroom(self.chatroom_settings)

                    await asyncio.sleep(2)
                    continue

                if not self._appearance_reset_done:
                    await self.reset_appearance()

                await asyncio.sleep(5)

        except (KeyboardInterrupt, asyncio.CancelledError):
            logger.info("Shutting down with Ctrl+C...")
        except Exception as e:
            logger.error("Bot runtime error: %s", e, exc_info=True)
            self._send_error_to_discord(traceback.format_exc())
        finally:
            await self.disconnect()
