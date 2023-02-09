import eventlet
from eventlet.green.urllib.request import urlopen
eventlet.monkey_patch()
from os import environ
import re
import isodate
import urllib.parse
import json


key = environ.get('YOUTUBE_API_KEY')  # from https://console.cloud.google.com/apis/credentials

def verify_youtube_video_and_return_id(url):
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
      r = eventlet.spawn(urlopen, url + urllib.parse.urlencode(params))
      my_dict=json.loads(r.wait().read())
      items=my_dict.get('items')[0]
      dur=items.get('contentDetails').get('duration')
      dur = isodate.parse_duration(dur).total_seconds()
  except:
      return None
  return dur if dur>0 else None # youtube api sets time to 0 if video is a livestream.



