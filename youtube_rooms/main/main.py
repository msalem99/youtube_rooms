from gevent import monkey,sleep; monkey.patch_all();
from flask import Blueprint,render_template,session,url_for,redirect,request,flash,abort,copy_current_request_context
from .forms import create_room
from flask_socketio import emit, join_room, leave_room,Namespace,disconnect
from .. import socketio
from .. import redis_client
from ..helper_functions import get_duration


main_bp=Blueprint(
    "main_bp",__name__,
    template_folder='templates',
    static_folder='static',
    static_url_path="/main/static")


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
                redis_client.expire(room_name,1800)
                #start the worker that will be responsible for
                #synchronization between room members.
                socketio.start_background_task(target=create_room_worker,room_name=room_name)  
                return redirect(url_for('.room',room_name=form.name.data))
        except:
            flash("Something went wrong")
            return render_template('main.jinja2',form=form)
        flash("Room name already exists, please try another name.")
    return render_template('main.jinja2',form=form)

@main_bp.route('/room/<string:room_name>')
def room(room_name):
    room_name=room_name+"-room"
    if redis_client.exists(room_name):
        return render_template('room.jinja2')
    abort(404,"Room doesn't exist")


class MyNamespace(Namespace):

    def on_my_broadcast_event(self, message):
        room_name = session.get('room_name')
        emit('my_response', {'data': message['data']}, to=room_name)
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
                emit('my_response', {'data':"Please enter a valid youtube address"}, to=room_name)
            else:
                #queue format : videoDuration videoID
                redis_client.lpush(room_name+"-queue",str(args[0])+" "+str(args[1]))
          #  redis_client.publish(room_name+"-queue", message['data'])
                emit('my_response', {'data': "Video added to queue successfully"}, to=room_name) 
              
        
    def on_connect(self):
        emit('my_response', {'data': 'Connected'})
        print(socketio.async_mode)
        
    def on_disconnect(self):
        check_session_and_leave_room()
        disconnect(request.sid)
        print('Client disconnected')
    
socketio.on_namespace(MyNamespace('/'))

def check_session_and_join_room():
    room_name=session.get('room_name')
    if room_name: 
        join_room(room_name)
        redis_client.persist(room_name)
        redis_client.sadd(room_name,session.sid)
        return
    return disconnect(request.sid)
    

def check_session_and_leave_room():
    room_name=session.get('room_name')
    if room_name: 
        leave_room(room_name)
        session.pop('room_name')
        redis_client.srem(room_name,session.sid)
        if redis_client.scard(room_name) == 1:
            redis_client.expire(room_name,5)
     

def create_room_worker(room_name):
    worker=SynchronizationWorker(room_name)
    synch_worker=socketio.start_background_task(target=worker.work)
    pubsub = redis_client.pubsub(ignore_subscribe_messages=True)
    #listen to redis for expiration of keys, if a room expires
    #that means the room's worker should also be terminated.
    redis_client.config_set('notify-keyspace-events', 'Ex')
    pubsub.psubscribe({"__keyevent@0__:expired"})
    #pubsub.subscribe({room_name+'-queue'})
    while True:
        sleep(0.1)
        message = pubsub.get_message()
        
        if type(message) is dict:
           try:
            if str(message.get('data'),encoding='utf-8')==room_name: 
                break
           except:
               pass
        print("working")
    #Once the create room worker loop terminates, the synchronization
    #worker is also terminated, the room queue is deleted then pushed
    #a flag that will enable the thread to get over blpop blocking.
    worker.stop_work()
    redis_client.delete(room_name+"-queue")
    redis_client.lpush(room_name+"-queue","END_THREAD")
    synch_worker.join()
    del worker
    print("Workers successfully terminated")
    
    
    
class SynchronizationWorker:
    def __init__(self, room_name):
        self.room_name = room_name
        self.switch = True
            
    def work(self):
        while True:
            pop=redis_client.blpop(self.room_name+"-queue")
            if pop[1]==b'END_THREAD': break
            y=pop[1].decode("utf-8").split(' ')
            duration=float(y[0])
            socketio.emit('start_video',
                        {'data': str(y[1])},
                        namespace='/',to=self.room_name)   
            while duration>0 and self.switch:
                sleep(0.5)
                duration=duration-0.5
                socketio.emit('synch_data',
                        {'data': str([duration,y[1]])},
                        namespace='/',to=self.room_name)
    def stop_work(self):
        self.switch=False
    



        
        
        
        
