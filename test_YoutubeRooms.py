import unittest
import random
import string
import logging
from flask import current_app,session
from youtube_rooms import init_app,redis_client,socketio


class YoutubeRoomsTests(unittest.TestCase):
    def setUp(self):
        self.app = init_app('testing')
        self.ctx = self.app.app_context()
        self.ctx.push()
        redis_client.flushall() #just incase
        self.client = self.app.test_client()
        
    def tearDown(self):
        redis_client.flushall()
        self.ctx.pop()
        
        
    def test_app(self):
        assert self.app is not None
        assert current_app == self.app
    def test_main_page(self):
        response = self.client.get('/', follow_redirects=True)
        assert response.status_code == 200
        assert response.request.path == '/'
    def test_room_name_form(self):
        response=self.client.get('/')
        html = response.get_data(as_text=True)
        assert response.status_code == 200
        assert 'name="name"' in html
        assert 'name="submit"' in html
    def test_room_name_submit(self):
 
        room_name='test'
        response=self.client.post('/',
                         data={'name':room_name},
                         follow_redirects=True)
        assert response.status_code == 200
        assert response.request.path == '/room/'+room_name
    def create_room(self,room_name):
        self.room_name=room_name
        response=self.client.post('/',
                         data={'name':self.room_name},
                         follow_redirects=True)
        html = response.get_data(as_text=True)
        
        return html,response    
        
        
        
    def test_room_name_submit_invalid(self):
        html,response=self.create_room('te st')
        assert 'Room name can not contain spaces or special characters.' in html
        assert response.status_code == 200 
        assert response.request.path == '/'
        
        for i in range(100):
            html,response=self.create_room(''.join([random.choice(string.ascii_letters + string.digits + string.punctuation ) for n in range(12)])+random.choice(string.punctuation))
            assert 'Room name can not contain spaces or special characters.' in html
            assert response.status_code == 200 
            assert response.request.path == '/'
            
        html,response=self.create_room('room')
        assert 'Room is a reserved word.' in html
        assert response.status_code == 200 
        assert response.request.path == '/'
        
        html,response=self.create_room('Room')
        assert 'Room is a reserved word.' in html
        assert response.status_code == 200 
        assert response.request.path == '/'
        
        
    def test_room_name_submit_valid(self):
        html,response=self.create_room("test   ")
        assert response.status_code == 200 
        assert response.request.path == '/room/'+self.room_name.strip()
        
        html,response=self.create_room("test1   ")
        assert response.status_code == 200 
        assert response.request.path == '/room/'+self.room_name.strip()
        
        html,response=self.create_room("test2")
        assert response.status_code == 200 
        assert response.request.path == '/room/'+self.room_name.strip()
        
    def test_room_name_already_exists(self):
        html,response=self.create_room("test")
        assert response.status_code == 200 
        assert response.request.path == '/room/'+self.room_name.strip()
        html,response=self.create_room("test")
        assert response.status_code == 200
        assert 'Room name already exists, please try another name.' in html 
        assert response.request.path == '/'  
        
    def test_username_form(self):
        html,response=self.create_room("test")
        assert response.status_code == 200 
        assert response.request.path == '/room/'+self.room_name
        assert 'name="name"' in html
        assert 'name="submit"' in html
        
    def test_username_invalid(self):
        html,response=self.create_room("test")
        assert response.status_code == 200 
        assert response.request.path == '/room/'+self.room_name
        assert 'name="name"' in html
        assert 'name="submit"' in html
        self.username="test user"
        response=self.client.post(response.request.path,
                         data={'name':self.username},
                         follow_redirects=True)
        html = response.get_data(as_text=True)
        assert response.status_code == 200 
        assert response.request.path == '/room/'+self.room_name
        assert 'Username can not contain spaces or special characters.' in html
        self.username="test"+random.choice(string.punctuation)
        response=self.client.post(response.request.path,
                         data={'name':self.username},
                         follow_redirects=True)
        html = response.get_data(as_text=True)
        assert response.status_code == 200 
        assert response.request.path == '/room/'+self.room_name
        assert 'Username can not contain spaces or special characters.' in html
        
    def test_username_in_session(self):
        html,response=self.create_room("test")
        assert response.status_code == 200 
        assert response.request.path == '/room/'+self.room_name
        self.username="testUser"
        with current_app.test_request_context(response.request.path),self.app.test_client() as c:
            #try to join room, set username, then join room.
            response=c.post(response.request.path,
            data={'name':self.username},
            follow_redirects=True)
            html = response.get_data(as_text=True)
            assert response.status_code == 200 
            assert response.request.path == '/room/'+self.room_name
            assert session.get('username') == self.username.strip()
            assert 'id="player"' in html
            #Join another room while username is already set
            html,response=self.create_room("test2")
            response=c.get(response.request.path,
            follow_redirects=True)
            html = response.get_data(as_text=True)
            assert response.status_code == 200 
            assert response.request.path == '/room/'+self.room_name
            assert session.get('username') == self.username.strip()
            assert 'id="player"' in html
            
            
    def test_join_room_that_doesnt_exist(self):
        response=self.client.get('/room/test') #room "test" doesnt exist
        assert response.status_code == 404
        
        
if __name__ == '__main__':

    unittest.main()