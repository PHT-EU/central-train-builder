#!/usr/bin/python3

import socketio
from aiohttp import web
from TrainBuilder import TrainBuilder
import json
import shutil
from util import post_route_to_vault
import logging
from datetime import datetime
import jwt

sio = socketio.AsyncServer()

app = web.Application()

sio.attach(app)

tb = TrainBuilder()

# we can define aiohttp endpoints just as we normally
# would with no change

logging.basicConfig(filename="train_builder.log", level=logging.INFO)

with open("rsa.public") as pk_file:
    pk = pk_file.read()


def validate_token(token):
    try:
        decoded_token = jwt.decode(token, pk, verify=False)
        return True
    except jwt.ExpiredSignatureError:
        return False


async def index(request):
    with open('index.html') as f:
        return web.Response(text=f.read(), content_type='text/html')


@sio.event
async def connect(sid, environ):
    print("connect event called")
    # TODO validate token
    logging.info(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - Client {sid} connected")
    print(sid)
    await sio.emit('my_response', {'data': 'Connected', 'count': 0}, room=sid)

# # If we wanted to create a new websocket endpoint,
# # use this decorator, passing in the name of the
# # event we wish to listen out for
# @sio.on('my_message')
# async def print_message(sid, message):
#     # When we receive a new event of type
#     # 'message' through a socket.io connection
#     # we print the socket ID and the message
#     print("Socket ID: ", sid)
#     print(message)
#
#
# @sio.on("generate_hash")
# async def generate_hash(sid, message):
#     json_message = json.JSONDecoder().decode(message)
#     print("Generating Hash")
#     hashed_value = tb.provide_hash(json_message)
#     print(hashed_value)
#
#     await sio.emit("generated_hash", data={"completed": True,
#                                            "hash_value": hashed_value})
#

@sio.on("train")
async def build_train(sid, message):
    # TODO validate token
    print(message)
    token = message["token"]
    if not validate_token(token):
        logging.warning(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} Unauthorized login attempt {sid}")
        return {"success": False, "msg": "Unauthorized"}, 401

    try:
        if message["action"] == 'build':
            print("building train")
            try:
                data = message["data"]
                logging.info(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - Received build request, train id:"
                             f" {data['train_id']}")
                # print(data)
                train_id = data["train_id"]
                route = data["route"]
                route = [str(x) for x in route]  # TR requires strings as harborProjects

                logging.info(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - Posting route to vault:\nid: "
                             f"{data['train_id']}")
                post_route_to_vault(train_id, route)
                logging.info(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - Building the train, id: "
                             f"{data['train_id']}")
                msg = tb.build_example(data)
                if msg["success"]:
                    logging.info(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - Successfully built train: id "
                                 f"{data['train_id']}")
                    print(msg)
                    return msg, 200
                else:
                    logging.error(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - Error during build process of train"
                                  f" {data['train_id']}:\n {msg}")
                    return msg, 300
                # await sio.emit("build_train", data={"completed": True})
            except BaseException as e:
                # shutil.rmtree("pht_train")

                print(e)
                logging.error(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - Something broke: \n{e}")
                return {"success": False, "msg": "Train building failure"}, 300

                # await sio.emit("build_failure", data={"failed": str(e)})

        elif message["action"] == 'generateHash':
            print("Generating Hash")
            try:
                data = message["data"]
                logging.info(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - Generating Hash for train {data['train_id']}")
                msg = tb.provide_hash(data)
                print(msg)
                if msg["success"]:
                    logging.info(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - Successfully generated hash for train"
                                 f" {data['train_id']}:\n Hash: {msg}")
                    print(msg)
                    return msg, 200
                else:
                    logging.error(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - Hash generation failed for train "
                                  f"{data['train_id']} \n {msg}")
                    return msg, 300
                # await sio.emit("build_train", data={"completed": True})
            except BaseException as e:
                # shutil.rmtree("pht_train")
                print(e)
                logging.error(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - Something broke: \n{e}")
                return {"success": False, "msg": "Hash generation failure"}, 300

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
    web.run_app(app, host="0.0.0.0", port=3002)