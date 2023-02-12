from gevent import monkey; monkey.patch_all();
from flask import Flask,render_template
from flask_socketio import SocketIO, emit
from flask_session import Session
from flask_redis import FlaskRedis
from os import environ
import logging
from flask_cors import CORS

#initialize global libraries

sess=Session()
socketio = SocketIO()
redis_client = FlaskRedis()
logging.getLogger('flask_cors').level = logging.DEBUG
def init_app():
    """Initialize the core application."""
    app = Flask(__name__, instance_relative_config=False)
    app.config.from_object('config.DevConfig')
    sess.init_app(app)
    redis_client.init_app(app)
    
    
    socketio.init_app(app,manage_session=False,async_mode='gevent',message_queue=environ.get('REDIS_OM_URL'),
                      engineio_logger=True,logger=True)
    
    from .main import main
    
    
    
    app.register_blueprint(main.main_bp)
    with app.app_context():

        return app