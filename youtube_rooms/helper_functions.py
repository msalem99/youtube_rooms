from gevent import monkey; monkey.patch_all();
from requests import get
from os import environ
import re
import isodate
import time
import random
from functools import wraps
from inspect import getfullargspec
from . import socketio,redis_client
from flask import request

key = environ.get('YOUTUBE_API_KEY')  

def verify_youtube_video_and_return_id(url):
    #regex1 ensures that the link is a valid youtube video
    #regex2 extracts the id after ensuring its also a valid youtube video
    #2 regexes are used for extra verification
    regex1=re.compile("^((?:https?:)?\/\/)?((?:www|m)\.)?((?:youtube(-nocookie)?\.com|youtu.be))(\/(?:[\w\-]+\?v=|embed\/|v\/)?)([\w\-]+)(\S+)?$")   
    if regex1.search(url):
        regex2 = re.compile("^.*(?:(?:youtu\.be\/|v\/|vi\/|u\/\w\/|embed\/|shorts\/)|(?:(?:watch)?\?v(?:i)?=|\&v(?:i)?=))([^#\&\?]*).*")
        return regex2.findall(url)[0] if regex2.findall(url) else None
    return None
 

def get_duration(url):
  id=verify_youtube_video_and_return_id(url) 
  if id is None:
      return None
  url = 'https://www.googleapis.com/youtube/v3/videos/?'
  params = {
      'id': str(id),
      'part': 'contentDetails',
      'key': str(key)
  }
  try:
      r = get(url, params)   
      items=r.json().get('items')[0]
      dur=items.get('contentDetails').get('duration')
      dur = isodate.parse_duration(dur).total_seconds()
  except:
      return None
  return (dur,id) if dur>0 else None # youtube api sets time to 0 if video is a livestream.

def get_current_time():
    return float(time.time())

def pick_user_color():
    colors=['maroon','red','purple','fuchsia','green','lime'
            ,'olive','yellow','navy','blue','teal','aqua']
    return random.choice(colors)
    
#decorators
#This decorator ensures that the user is a member of the room. This is done
#to prevent users from connecting then sending data to what may be other rooms.
def check_if_member_of_room(argument_name):
    def decorator(f):
        argspec = getfullargspec(f)
        argument_index = argspec.args.index(argument_name)
        @wraps(f)
        def wrapper(*args, **kwargs):
            try:
                message = args[argument_index]
            except IndexError:
                message = kwargs[argument_name]
            room_name=message.get('room_name')+"-room"
            if redis_client.smismember(room_name,request.sid)!=[1]:
               socketio.disconnect(request.sid)
            return f(*args, **kwargs)
        return wrapper
    return decorator    