from gevent import monkey,sleep,kill; monkey.patch_all();
from flask import Blueprint,render_template,session,url_for,redirect,request,flash,abort,copy_current_request_context,current_app
from .forms import my_form
from flask_wtf.csrf import generate_csrf
from flask_socketio import emit, join_room, leave_room,Namespace,disconnect,close_room
from .. import socketio
from .. import redis_client
from ..helper_functions import get_duration,get_current_time,pick_user_color
from functools import wraps
from inspect import getfullargspec
from flask_session import sessions
from redis import RedisError 


main_bp=Blueprint(
    "main_bp",__name__,
    template_folder='templates',
    static_folder='static',
    static_url_path="/main/static")

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
               disconnect(request.sid)
            return f(*args, **kwargs)
        return wrapper
    return decorator

#http routes

@main_bp.route('/',methods=['POST','GET'])
def index():
    form=my_form('Room name')
    
    if form.validate_on_submit():
        room_name=form.name.data.strip()+"-room"
        try:
            if not redis_client.exists(room_name):
                #create a set with 1 empty member
                #set expiration time, this expiration is
                #removed once a user joins the room.
                redis_client.sadd(room_name,' ')
                redis_client.expire(room_name,500)
                #start the worker that will be responsible for
                #synchronization between room members.
                socketio.start_background_task(target=create_room_worker,room_name=room_name)
              
                return redirect(url_for('.room',room_name=form.name.data.strip()))
        except RedisError: 
            abort(503,"Service currently down")
        flash("Room name already exists, please try another name.")
    return render_template('main.jinja2',form=form)

@main_bp.route('/room/<string:room_name>',methods=['POST','GET'])
def room(room_name):
    room_name=room_name+"-room"
    form=my_form('Username')
    websocket_csrf=generate_csrf()
    session['websocket_csrf']=websocket_csrf
    if form.validate_on_submit():
        session['username']=form.name.data.strip()
        
        
        
    
    try:
        if redis_client.exists(room_name):
            if session.get('username') is None:
                session['color']=pick_user_color()
                return render_template("username.jinja2",form=form)
            
            return render_template('room.jinja2',data = {'username': session.get("username"),
                                                         'color':session.get("color"),
                                                         'csrf_token':websocket_csrf})
    except RedisError: abort(503,"Service currently down")
    abort(404,"Room doesn't exist")





#socket io events




#socket io error handler
@socketio.on_error_default
def default_error_handler(e):
    print(e) 
    print(request.event["message"])
    print(request.event["args"])
       
class MyNamespace(Namespace):
 
    @check_if_member_of_room('message') 
    def on_submit_video_event(self, message):
        room_name=message.get('room_name')+"-room"
        args=get_duration(message.get('data'))
        if args is None:
            emit('my_response', {'data':"Please enter a valid youtube link"}, to=request.sid)
            return
        else:
            #queue format : videoDuration videoID
            redis_client.lpush(room_name+"-queue",str(args[0])+" "+str(args[1]))
            emit('my_response', {'data': "Video added to the queue successfully"}, to=request.sid)
            return
        
    @check_if_member_of_room('message')              
    def on_sync_data(self, message):
        room_name=message.get('room_name')+"-room"
        redis_client.publish(room_name,request.sid+" "+"sync_video")
        return
    
    #@check_if_member_of_room('message')                   
    def on_chat_message(self,message):
        room_name=message.get('room_name')+"-room"
        emit('chat_message', {'chat_message': message.get('chat_message'),
                              'username':session.get('username'),
                              'color':session.get('color')},
                                to=room_name,include_self=False)
        return
                              

        
    def on_connect(self):
        
        
       #csrf token checking
        csrf_token=request.args.get('websocket_csrf')
        room_name=request.args.get('room_name')+"-room"
        if csrf_token != session.get('websocket_csrf'):
            print("CSRF ERROR")

            disconnect(request.sid)
            return
        #Make sure the room exists
        if redis_client.exists(room_name):
            join_room(room_name)
            try: 
                redis_client.publish(room_name,request.sid+" join_room")
            except:
                disconnect(request.sid)
                return 
            emit('my_response', {'data': 'Connected to '+room_name})  
        return 
         
        
    def on_disconnect(self):
            room_name=request.args.get("room_name")+"-room"
            redis_client.publish(room_name,request.sid+" leave_room") 
            disconnect(request.sid)
            print(request.sid+' disconnected')
            return
    

socketio.on_namespace(MyNamespace('/'))




#room functions


#join the room and send video data to the user that just joined.
def join_redis_room(sid,room_name):
 
       
        pipe=redis_client.pipeline()
        redis_client.persist(room_name)
        redis_client.sadd(room_name,sid)
        redis_client.publish(room_name,sid+" "+"start_video")
        pipe.execute()
        
        
        return

    
#If room is empty, it will expire after 500 seconds, unless a user joins and the expiry is removed.
def leave_redis_room(sid,room_name):
        
        
        redis_client.srem(room_name,sid)
        if redis_client.scard(room_name) == 1:
            redis_client.expire(room_name,10)
        
        
        return

     


#########################Room Workers#####################################
#Each room consists of 2 workers, the first is responsible for listening
#to the redis channels, there are 2 channels the worker is listening 
#to : 
#     1- Expiration channel: If the room expires, the worker terminates
#                            the other worker safely then breaks the loop
#                                
#     2- A channel named after the room name: 
#          This channel recieves messages in 5 cases:
#          
#          1-A user joined the room
#          2-A user left the room 
#          3-A user just joined the room so start_video is called to send new video data
#          4-The synchronization worker wants to start a new video so start_video is called.
#          5-The client calls sync_data to retrieve the current video data. 
#
#
#The second worker (SynchronizationWorker) is responsible for the video queue
#and the video data 


def create_room_worker(room_name):
    worker=SynchronizationWorker(room_name)
    
    try:
        pubsub = redis_client.pubsub(ignore_subscribe_messages=True)
        #listen to redis for expiration of keys, if a room expires
        #that means the room's worker should also be terminated.
        redis_client.config_set('notify-keyspace-events', 'Ex')
        pubsub.psubscribe({"__keyevent@0__:expired"})
        pubsub.subscribe({room_name})
    except RedisError:
        return
    synch_worker=socketio.start_background_task(target=worker.work)    
    while True:
        sleep(0.01)
        try:
            message = pubsub.get_message()
        except RedisError:
            break
        
        if type(message) is dict:
            if str(message.get('data'),encoding='utf-8')==room_name: 
                break

            if str(message.get('channel'),encoding='utf-8')==room_name:
                #the message contains the request sid and the event name to be emitted seperated by a space.
                [room_name_or_sid,event_name]=str(message.get('data'),encoding='utf-8').split(" ")
                #The event_name could be used in  the client side to decide if a new video is being loaded
                #or to just sync data. 2 events are used instead of only one for convenience on the client side.
                #event_name could be sync_video or start_video.
                match event_name:
                    case "start_video" | "sync_video":
                        if worker.current_video:socketio.emit(event_name,
                                    {'current_video':worker.current_video,
                                    'time_stamp':worker.current_video_timestamp},
                                    namespace='/',
                                    to=room_name_or_sid)
                    case "join_room":
                        join_redis_room(room_name_or_sid,worker.room_name)
                    case "leave_room":
                        leave_redis_room(room_name_or_sid,worker.room_name)
 
                      
           
            
        
    #Once the create room worker loop terminates, the synchronization
    #worker is also terminated by deleting the room queue then pushing
    #a flag "END_THREAD" that will enable the synchronization worker to
    #exit the loop and join()
    
    
    
    
    pubsub.close() 
    
    worker.stop_work()
    try:
        #problem: if redis fails the room queue will persist in database with no way to delete.
        redis_client.delete(room_name+"-queue")
        redis_client.lpush(room_name+"-queue","END_THREAD")
        synch_worker.join()
    except RedisError:
        synch_worker.kill()

    print("Workers successfully terminated")
    
    
    
class SynchronizationWorker:
    def __init__(self, room_name):
        self.room_name = room_name
        self.switch = True
        self.current_video=None
        self.current_video_timestamp=0
        self.video_duration=None
        self.just_started=None    
    def work(self):
        #2 loops, one pops the video queue and the other updates the 
        #video timestamp for synchronization purposes.
        while True:
            try:
                pop=redis_client.blpop(self.room_name+"-queue")
            except:
                break
            if pop[1]==b'END_THREAD': break
            self.current_video_timestamp=0
            y=pop[1].decode("utf-8").split(' ')
            self.current_video=str(y[1])
            self.video_duration=float(y[0])
            #publishing to the channel to indicate to the other worker to emit the new video
            redis_client.publish(self.room_name,self.room_name+" "+"start_video")
            sleep(2)
            time_to_end=get_current_time()+self.video_duration+4
            start_time=get_current_time()
            
            while get_current_time()<time_to_end and self.switch:
                self.current_video_timestamp=get_current_time()-start_time
                sleep(0.01)        
                
    def stop_work(self):
        self.switch=False
    

        
        
        
