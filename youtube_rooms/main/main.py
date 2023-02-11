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
    form=create_room()
    
    if form.validate_on_submit():
        room_name=form.name.data+"-room"
        try:
            if not redis_client.exists(room_name):
                #create a set with 1 empty member
                #set expiration time, this expiration is
                #removed once a user joins the room.
                redis_client.sadd(room_name,' ')
                redis_client.expire(room_name,1000)
                #start the worker that will be responsible for
                #synchronization between room members.
                socketio.start_background_task(target=create_room_worker,room_name=room_name)  
                return redirect(url_for('.room',room_name=form.name.data))
        except RedisError: 
            abort(503,"Service currently down")
        flash("Room name already exists, please try another name.")
    return render_template('main.jinja2',form=form)

@main_bp.route('/room/<string:room_name>')
def room(room_name):
    room_name=room_name+"-room"
    try:
        if redis_client.exists(room_name):
            return render_template('room.jinja2')
    except RedisError: abort(503,"Service currently down")
    abort(404,"Room doesn't exist")


#socket io error handler
@socketio.on_error_default
def default_error_handler(e):
    print(e) 
    print(request.event["message"])
    print(request.event["args"])   
    socketio.stop()
class MyNamespace(Namespace):
 
    #If the room exists, allow the user to join and save it to 
    #the user session.    
    def on_set_room_name_event(self, message):
        room_name=message['data']+"-room"
        if redis_client.exists(room_name):
            session['room_name']=room_name
            check_session_and_join_room()
            return
        return disconnect(request.sid)
    
    def on_submit_video_event(self, message):
        
        room_name=session.get('room_name')
        if room_name:
            args=get_duration(message['data'])
            if args is None:
                emit('my_response', {'data':"Please enter a valid youtube address"}, to=request.sid)
            else:
                #queue format : videoDuration videoID
                redis_client.lpush(room_name+"-queue",str(args[0])+" "+str(args[1]))
                emit('my_response', {'data': "Video added to queue successfully"}, to=request.sid) 
    def on_sync_data(self, message):
        room_name=session.get('room_name')
        if room_name:
           redis_client.publish(room_name,request.sid+" "+str(1))                   
        
    def on_connect(self):
        emit('my_response', {'data': 'Connected'})
        
    def on_disconnect(self):
        check_session_and_leave_room()
        disconnect(request.sid)
        print('Client disconnected')
    
socketio.on_namespace(MyNamespace('/'))




#room functions



def check_session_and_join_room():
    room_name=session.get('room_name')
    if room_name: 
        join_room(room_name)
        redis_client.persist(room_name)
        redis_client.sadd(room_name,session.sid)
        redis_client.publish(room_name,request.sid+" "+str(0))
        return
    return disconnect(request.sid)
    

def check_session_and_leave_room():
    room_name=session.get('room_name')
    if room_name: 
        leave_room(room_name)
        session.pop('room_name')
            #problem: if redis fails here then the room will be dormant in redis database with no way to delete
        redis_client.srem(room_name,session.sid)
        if redis_client.scard(room_name) == 1:
            redis_client.expire(room_name,10)

     


#room workers
#Each room consists of 2 workers, 1 is responsible for listening
#to the redis channels, there are 2 channels the worker is listening 
#to : 
#     1- Expiration channel: If the room expires, the worker terminates
#                            the other worker safely then breaks the loop
#                                
#     2- A channel named after the room name.: This channel recieves messages
#                             in two cases, the first is when a user joins 
#                             an existing room, refer to check_session_and_join_room()
#                             the second is when the client sends a sync_data event.
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
           try:
            if str(message.get('data'),encoding='utf-8')==room_name: 
                break
           except:
               pass
           try:
            if str(message.get('channel'),encoding='utf-8')==room_name and worker.current_video is not None:
                #the message contains the request sid and the flag seperated by a space.
                sid=str(message.get('data'),encoding='utf-8').split(" ")[0]
                flag=str(message.get('data'),encoding='utf-8').split(" ")[1]
                #The flag is read by the client side to determine if only sync is required or if the whole 
                #video should be initiated
                video_data=str(str(worker.current_video)+' '+str(worker.current_video_timestamp)+" "+str(flag))
                socketio.emit('start_video_or_sync',
                        {'data': video_data},
                        namespace='/',to=sid)
           except:
               pass
                      
           
            
        
    #Once the create room worker loop terminates, the synchronization
    #worker is also terminated, the room queue is deleted then pushed
    #a flag that will enable the worker to get over blpop blocking.
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
            pop=redis_client.blpop(self.room_name+"-queue")
            if pop[1]==b'END_THREAD': break
            self.current_video_timestamp=0
            y=pop[1].decode("utf-8").split(' ')
            self.current_video=str(y[1])
            self.video_duration=float(y[0])
            video_data=str(str(self.current_video)+' '+str(self.current_video_timestamp)+" "+"0")
            
            socketio.emit('start_video_or_sync',
                        {'data': video_data},
                        namespace='/',to=self.room_name)
            print("here")
            sleep(2)
            time_to_end=get_current_time()+self.video_duration+4
            start_time=get_current_time()
            
            while get_current_time()<time_to_end and self.switch:
                self.current_video_timestamp=get_current_time()-start_time
                sleep(0.01)        
                
    def stop_work(self):
        self.switch=False
    

        
        
        
