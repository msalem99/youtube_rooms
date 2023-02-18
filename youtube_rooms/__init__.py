from gevent import monkey; monkey.patch_all();
from flask import Flask
from flask_socketio import SocketIO
from flask_redis import FlaskRedis
from os import environ


#initialize global libraries
socketio = SocketIO()
redis_client = FlaskRedis()
def init_app():
    """Initialize the core application."""
    app = Flask(__name__, instance_relative_config=False)
    app.config.from_object('config.DevConfig')

    redis_client.init_app(app)
    
    
    socketio.init_app(app,
                      async_mode='gevent',
                      message_queue=environ.get('REDIS_OM_URL'),)
    
    from .main import main
    
    
    
    
    with app.app_context():
        app.register_blueprint(main.main_bp)
        return app