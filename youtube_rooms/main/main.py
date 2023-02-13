from gevent import monkey,sleep,kill; monkey.patch_all();
from flask import Blueprint,render_template,session,url_for,redirect,request,flash,abort,copy_current_request_context
from .forms import create_room
from flask_socketio import emit, join_room, leave_room,Namespace,disconnect,close_room
from .. import socketio
from .. import redis_client
from ..helper_functions import get_duration,get_current_time

from redis import RedisError 


main_bp=Blueprint(
    "main_bp",__name__,
    template_folder='templates',
    static_folder='static',
    static_url_path="/main/static")


#http routes

@main_bp.route('/',methods=['POST','GET'])
def index():
    form=create_room('username')
    
    if form.validate_on_submit():
        room_name=form.name.data+"-room"
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
                return redirect(url_for('.room',room_name=form.name.data))
        except RedisError: 
            abort(503,"Service currently down")
        flash("Room name already exists, please try another name.")
    return render_template('main.jinja2',form=form)

@main_bp.route('/room/<string:room_name>',methods=['POST','GET'])
def room(room_name):
    room_name=room_name+"-room"
    form=create_room('username')
    if form.validate_on_submit():session['username']=form.name.data
    
    try:
        if redis_client.exists(room_name):
            if session.get('username') is None:
                return render_template("main.jinja2",form=form)
            
            return render_template('room.jinja2',data = {'username': session.get("username")})
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
 
    #If the room exists, allow the user to join and save it to 
    #the user session.    
    def on_set_room_name_event(self, message):
        room_name=message.get('room_name')+"-room"
        if redis_client.exists(room_name):
            # session['room_name']=room_name
            check_session_and_join_room(room_name)
            return
        return disconnect(request.sid)
    
    def on_submit_video_event(self, message):
        room_name=message.get('room_name')+"-room"
        if session.get(request.sid)==room_name:
            args=get_duration(message.get('data'))
            if args is None:
                emit('my_response', {'data':"Please enter a valid youtube address"}, to=request.sid)
                return
            else:
                #queue format : videoDuration videoID
                redis_client.lpush(room_name+"-queue",str(args[0])+" "+str(args[1]))
                emit('my_response', {'data': "Video added to queue successfully"}, to=request.sid)
                return
        return disconnect(request.sid) 
                
    def on_sync_data(self, message):
        room_name=message.get('room_name')+"-room"
        if session.get(request.sid)==room_name:
           redis_client.publish(room_name,request.sid+" "+"sync_video")
           return
        disconnect(request.sid)                   
    def on_chat_message(self,message):
        room_name=message.get('room_name')+"-room"
        if session.get(request.sid)==room_name:
                emit('chat_message', {'chat_message': message.get('chat_message'),'username':session.get('username')}, to=room_name,include_self=False)

                              

        
    def on_connect(self):
        emit('my_response', {'data': 'Connected'})
        
    def on_disconnect(self):
        check_session_and_leave_room()
        disconnect(request.sid)
        print('Client disconnected')
    
socketio.on_namespace(MyNamespace('/'))




#room functions



def check_session_and_join_room(room_name):
    # room_name=session.get('room_name')
    # if room_name: 
        join_room(room_name)
        session[request.sid]=room_name
        redis_client.persist(room_name)
        redis_client.sadd(room_name,request.sid)
        redis_client.publish(room_name,request.sid+" "+"start_video")
        return
    # return disconnect(request.sid)
    

def check_session_and_leave_room():
    room_name=session.get(request.sid)
    if room_name:
        leave_room(room_name)
        session.pop(request.sid)
            #problem: if redis fails here then the room will be dormant in redis database with no way to delete
        redis_client.srem(room_name,request.sid)
        if redis_client.scard(room_name) == 1:
            redis_client.expire(room_name,500)
    return

     


#room workers
#Each room consists of 2 workers, the first is responsible for listening
#to the redis channels, there are 2 channels the worker is listening 
#to : 
#     1- Expiration channel: If the room expires, the worker terminates
#                            the other worker safely then breaks the loop
#                                
#     2- A channel named after the room name.: This channel recieves messages
#                             in two cases, the first is when a user joins 
#                             an existing room, refer to check_session_and_join_room()
#                             the second is when the client sends a sync_video event.
#                             refer to  on_sync_data(self, message) event
#
#
#the second worker (SynchronizationWorker) is responsible for the video queue
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

            if str(message.get('channel'),encoding='utf-8')==room_name and worker.current_video is not None:
                #the message contains the request sid and the event name to be emitted seperated by a space.
                [room_name_or_sid,event_name]=str(message.get('data'),encoding='utf-8').split(" ")
                #The event_name could be used in  the client side to decide if a new video is being loaded
                #or to just sync data. 2 events are used instead of only one for convenience on the client side.
                #event_name could be sync_data or start_video.
                socketio.emit(event_name,
                            {'current_video':worker.current_video,
                            'time_stamp':worker.current_video_timestamp},
                            namespace='/',
                            to=room_name_or_sid)
 
                      
           
            
        
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
    

        
        
        
