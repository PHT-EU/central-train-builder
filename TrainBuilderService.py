#!/usr/bin/python3

import socketio
from aiohttp import web
from TrainBuilder import TrainBuilder
import json
import shutil
from util import post_route_to_vault


sio = socketio.AsyncServer()

app = web.Application()

sio.attach(app)

tb = TrainBuilder()

# we can define aiohttp endpoints just as we normally
# would with no change


async def index(request):
    with open('index.html') as f:
        return web.Response(text=f.read(), content_type='text/html')


@sio.event
async def connect(sid, environ):
    print("connect event called")
    print(sid)
    await sio.emit('my_response', {'data': 'Connected', 'count': 0}, room=sid)

# If we wanted to create a new websocket endpoint,
# use this decorator, passing in the name of the
# event we wish to listen out for
@sio.on('my_message')
async def print_message(sid, message):
    # When we receive a new event of type
    # 'message' through a socket.io connection
    # we print the socket ID and the message
    print("Socket ID: ", sid)
    print(message)


@sio.on("generate_hash")
async def generate_hash(sid, message):
    json_message = json.JSONDecoder().decode(message)
    print("Generating Hash")
    hashed_value = tb.provide_hash(json_message)
    print(hashed_value)

    await sio.emit("generated_hash", data={"completed": True,
                                           "hash_value": hashed_value})

@sio.on("train")
async def build_train(sid, message):
    try:
        if message["action"] == 'build':
            try:
                data = message["data"]
                # print(data)
                train_id = data["train_id"]
                route = data["route"]
                route = [str(x) for x in route]  # TR requires strings as harborProjects

                post_route_to_vault(train_id, route)

                msg = tb.build_example(data)
                if msg["success"]:
                    print(msg)
                    return msg, 200
                else:
                    return msg, 300
                # await sio.emit("build_train", data={"completed": True})
            except BaseException as e:
                # shutil.rmtree("pht_train")
                print(e)
                return {"success": False, "msg": "Train building failure"}, 300

                # await sio.emit("build_failure", data={"failed": str(e)})
        else:
            print("No train to build")
    except Exception as e:

        print("Error in building train: {}".format(e))

        return {"success": False}, 300

# We bind our aiohttp endpoint to our app
# router
# app.router.add_get('/', index)

# We kick off our server
if __name__ == '__main__':
    web.run_app(app, host="0.0.0.0", port=443)