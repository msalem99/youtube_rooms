from flask import Blueprint,render_template,session,url_for,redirect,request,flash,abort,copy_current_request_context
from .forms import create_room
from flask_socketio import emit, join_room, leave_room,Namespace,disconnect
from .. import socketio
from .. import redis_client
import eventlet
eventlet.monkey_patch()

main_bp=Blueprint(
    "main_bp",__name__,
    template_folder='templates',
    static_folder='static',
    static_url_path="/main/static")

pubsub=redis_client.pubsub()
@main_bp.route('/',methods=['POST','GET'])
def index():
    form=create_room()
    if form.validate_on_submit():
        room_name=form.name.data+"-room"
        if not redis_client.exists(room_name):
            redis_client.expire(room_name,1800)
            redis_client.sadd(room_name,' ')
            socketio.start_background_task(target=create_room_worker,room_name=room_name)          
            return redirect(url_for('.room',room_name=form.name.data))
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
        
    def on_set_room_name_event(self, message):
        room_name=message['data']+"-room"
        if redis_client.exists(room_name):
            session['room_name']=room_name
            check_session_and_join_room()
            
            return
        disconnect(request.sid)
        return
    
    def on_submit_video_event(self, message):
        room_name=session.get('room_name')
        if room_name:
            redis_client.lpush(room_name+"-queue",message['data'])
            emit('my_response', {'data': message['data']}, to=room_name) 
              
        
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
            redis_client.expire(room_name,500)
    return disconnect(request.sid)


        

def create_room_worker(room_name):
    
    
    while True:
        eventlet.sleep()
        socketio.emit('my_response',
                      {'data': room_name,},
                      namespace='/',to=room_name)
        