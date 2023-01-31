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
    
class ProdConfig(Config):
    FLASK_ENV = 'production'
    DEBUG = False
    TESTING = False


class DevConfig(Config):
    TESTING = True
    SESSION_TYPE = 'redis'
    SESSION_REDIS=redis.from_url(environ.get('REDIS_OM_URL'))
    REDIS_URL=environ.get('REDIS_OM_URL')
