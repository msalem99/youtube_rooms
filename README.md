# Youtube-Rooms

Youtube-rooms is an app made by flask that allows users to create rooms and watch
youtube videos synchronously with a chatroom.

## Design

The app uses websockets to keep the user connected to the room. Flask-socketIO was used
for a fast implementation of websockets. To provide background tasks, gevent coroutines
were used. Redis was used to provide mapping between the rooms, users and the running flask app.

Each room has 2 gevents spawned to manage the room. We will call them workers.

- The first worker is responsible for listening to the redis channel associated with the room.
- The second worker is responsible for the video queue for each room and the current video details.

If a room is empty, the room works as intended in the background for a specified time then it gets removed and the workers terminated. This time is specified by ROOM_EXPIRATION_TIME in seconds in the config file.

Incase more than 1 process is running, a redis message queue is used to share messages between the processes. When a user joins a room, leaves a room or requests video info, an event is published to the redis channel associated with the room then the room worker listening to this channel acts based on the event received.

## Tools

- [Flask] - A python backend framework
- [Flask-SocketIO] - Websocket implementation with flask
- [gevent] - coroutine-based cooperative multitasking python framework
- [jQuery + socketIO] - frontend tools to implement websocket support client side

## Installation

Youtube-rooms runs with the server chosen by flask-socketIO. In case of async_mode='gevent', the library chooses pywsgi to run the server.

To run Youtube-rooms on a production ready server, create a python virtual environment

```sh
python -m venv c:\path\to\myenv
```

Activate the virtual environment then install the requirements.

```sh
pip install -r requirements.txt
```

To run the app:

```sh
python wsgi.py
```

## Your .env file should include

- SECRET_KEY: The key used by the flask app so secure communication between the client and the server.
- REDIS_OM_URL: Your redis database address.
- YOUTUBE_API_KEY: A youtube data api key, this is used to fetch data needed for the queued youtube videos by the users.
- TEST_REDIS_OM_URL: A separate redis database used during testing.
