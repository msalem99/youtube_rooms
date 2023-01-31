from flask import Flask,render_template
from flask_socketio import SocketIO, emit
from flask_session import Session
from flask_redis import FlaskRedis
#initialize global libraries

sess=Session()
socketio = SocketIO()
redis_client = FlaskRedis()
def init_app():
    """Initialize the core application."""
    app = Flask(__name__, instance_relative_config=False)
    app.config.from_object('config.DevConfig')
    sess.init_app(app)
    redis_client.init_app(app)
    socketio.init_app(app,manage_session=False)
    
    from .main import main
    
    
    
    app.register_blueprint(main.main_bp)
    with app.app_context():

        return app