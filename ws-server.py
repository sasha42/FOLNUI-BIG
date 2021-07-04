#!/usr/bin/env python

# WS server example that synchronizes state across clients

import asyncio
import json
import logging
import websockets

logging.basicConfig()

STATE = {"value": 0}

USERS = set()


def state_event():
    return json.dumps(STATE)


def users_event():
    return json.dumps(STATE)
    #return json.dumps({"type": "users", "count": len(USERS)})


async def notify_state(data):
    if USERS:  # asyncio.wait doesn't accept an empty list
        #message = state_event()
        message = json.dumps(data) 
        await asyncio.wait([user.send(message) for user in USERS])


async def notify_users():
    if USERS:  # asyncio.wait doesn't accept an empty list
        message = users_event()
        await asyncio.wait([user.send(message) for user in USERS])


async def register(websocket):
    USERS.add(websocket)
    await notify_users()
    #await asyncio.wait(print('user added'))


async def unregister(websocket):
    USERS.remove(websocket)
    await notify_users()
    #await asyncio.wait(print('user removed'))


async def counter(websocket, path):
    # register(websocket) sends user_event() to websocket
    await register(websocket)
    try:
        await websocket.send(state_event())
        async for message in websocket:
            data = json.loads(message)
            print(data)
            STATE = data
            await notify_state(data)
    finally:
        await unregister(websocket)


start_server = websockets.serve(counter, "0.0.0.0", 6789, ping_interval=None)

asyncio.get_event_loop().run_until_complete(start_server)
asyncio.get_event_loop().run_forever()
