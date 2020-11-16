import socketio
from aiohttp import web
from src.TrainBuilder import TrainBuilder
from src.util import post_route_to_vault
import logging
from datetime import datetime
import jwt
import os
from logging import error as err

sio = socketio.AsyncServer()

app = web.Application()

sio.attach(app)

tb = TrainBuilder()

# Directory the TB is running under
tb_dir = os.getenv("tb_dir") if os.getenv("tb_dir") else os.getcwd()
print(tb_dir)

# Setup loggin and public key

logging.basicConfig(filename=os.path.join(tb_dir, "train_builder.log"), level=logging.INFO)

with open(os.path.join(tb_dir, "rsa.public"), "r") as pk_file:
    pk = pk_file.read()


def validate_token(token):
    try:
        decoded_token = jwt.decode(token, pk, verify=False)
        return True
    except jwt.ExpiredSignatureError:
        return False
    except BaseException as e:
        err(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - Token could not be authenticated\n {e}")
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


@sio.on("train")
async def build_train(sid, message):
    # Validate the token sent by the frontend
    token = message["token"]
    if not validate_token(token):
        logging.warning(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} Unauthorized login attempt {sid}")
        return {"success": False, "msg": "Unauthorized"}, 401

    if message["action"] == 'build':
        print("Building train")
        data = message["data"]
        logging.info(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - Received build request, train id:"
                     f" {data['train_id']}")
        # Extract variables
        train_id = data["train_id"]
        route = data["route"]
        route = [str(x) for x in route]  # TR requires strings as harborProjects

        logging.info(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - Posting route to vault:\nid: "
                     f"{data['train_id']}")
        # Add the route to vault to storage for processing by the train router
        try:
            post_route_to_vault(train_id, route)
        except ValueError as error:
            err(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - Error adding route to vault"
                          f" {data['train_id']}:\n {error}")

            return {"success": False, "msg": "Route could not be added to vault"}, 300
        logging.info(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - Building the train, id: "
                     f"{data['train_id']}")

        msg = tb.build_train(data)
        if msg["success"]:
            logging.info(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - Successfully built train: id "
                         f"{data['train_id']}")
            print(msg)
            return msg, 200
        else:
            err(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - Error during build process of train"
                          f" {data['train_id']}:\n {msg}")
            return msg, 300

    elif message["action"] == 'generateHash':
        print("Generating Hash")
        try:
            data = message["data"]
            logging.info(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - Generating Hash for train {data['train_id']}")

            msg = tb.provide_hash(data)
            print(msg)
            if msg["success"]:
                err(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - Successfully generated hash for train"
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
            e(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - Something broke: \n{e}")
            return {"success": False, "msg": "Hash generation failure"}, 300

    # Validate a user submitted docker image and generate the security values for it
    # TODO implement this
    elif message["action"] == "validateImage":
        print("Validating image")

    else:
        return {"success": False, "msg": "Unrecognized command"}, 300

# We bind our aiohttp endpoint to our app
# router
# app.router.add_get('/', index)

# We kick off our server
if __name__ == '__main__':
    web.run_app(app, host="0.0.0.0", port=7777)
