from youtube_rooms import init_app,socketio
from redis import RedisError

app=init_app()

if __name__ == "__main__":
        socketio.run(app, host="0.0.0.0",port=5000)
