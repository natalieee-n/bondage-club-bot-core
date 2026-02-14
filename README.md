# bondage-club-bot-core

Core Bondage Club bot library (socket.io client + chatroom lifecycle management).

## Scope

This repository now only contains core bot features:
- Socket connection and login
- Chatroom search/create/join flow
- Room/member state synchronization
- Event queue and base extension hook (`customized_event_handler`)

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

`main.py` includes a minimal runnable subclass (`BasicBot`) that only uses core features.
