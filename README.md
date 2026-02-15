# bondage-club-bot-core

Core Bondage Club bot library (socket.io client + chatroom lifecycle management).

## Scope

This repository now only contains core bot features:
- Socket connection and login
- Chatroom search/create/join flow
- Room/member state synchronization
- Event queue and base extension hook (`customized_event_handler`)
- Query helpers for account/room data and message history

## Install

```bash
pip install .
```

## Use as a library

```python
from bondage_club_bot_core import BCBot

class MyBot(BCBot):
    async def customized_event_handler(self, data):
        pass
```

## Local run example

Example runtime files are under `examples/basic_bot/`.

- Script: `examples/basic_bot/main.py`
- Config template: `examples/basic_bot/.env.example`
- Chatroom config: `examples/basic_bot/chatroom_config.json`
- Docker files: `examples/basic_bot/Dockerfile`, `examples/basic_bot/docker-compose.yml`
