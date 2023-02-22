from gevent import monkey; monkey.patch_all();
from flask import Flask
from flask_socketio import SocketIO
from flask_redis import FlaskRedis
from os import environ
from config import config

#initialize global libraries
socketio = SocketIO()
redis_client = FlaskRedis()
def init_app(config_name=None):
    """Initialize the core application."""
    if config_name is None:
        config_name = "development"
    app = Flask(__name__, instance_relative_config=False)
    app.config.from_object(config[config_name])
    redis_client.init_app(app)
    socketio.init_app(app,
                      async_mode='gevent',
                      message_queue=app.config['SOCKETIO_MESSAGE_QUEUE'],)
    
    from .main import main
    with app.app_context():
        app.register_blueprint(main.main_bp)
        return app