"""App configuration."""
from os import environ, path
import redis
from dotenv import load_dotenv

# Load variables from .env
basedir = path.abspath(path.dirname(__file__))
load_dotenv(path.join(basedir, ".env"))


class Config:
    """Base config."""
    SECRET_KEY = environ.get('SECRET_KEY')
    FLASK_APP = environ.get('FLASK_APP')
    SOCKETIO_MESSAGE_QUEUE = environ.get('REDIS_OM_URL')
class ProdConfig(Config):
    FLASK_ENV = 'production'
    DEBUG = False
    TESTING = False


class DevConfig(Config):
    REDIS_URL=environ.get('REDIS_OM_URL')
    
    
class TestingConfig(Config):
    TESTING = True
    REDIS_URL=environ.get('TEST_REDIS_OM_URL')
    SOCKETIO_MESSAGE_QUEUE = None
    WTF_CSRF_ENABLED = False
config = {
    'development': DevConfig,
    'production': ProdConfig,
    'testing': TestingConfig
}