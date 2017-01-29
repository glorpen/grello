'''
Created on 26.01.2017

@author: glorpen
'''
import unittest
from grello.connection import ConsoleUI, Api, Connection
from unittest.mock import patch, MagicMock
from grello.objects import Member, Board
from requests.exceptions import ConnectionError, RequestException

class TestUi(unittest.TestCase):
    
    def test_console(self):
        ui = ConsoleUI()
        
        self.assertEqual(ui.load_keys(), None)
        
        with patch("grello.connection.print") as p:
            ui.save_keys("t", "s")
            self.assertTrue(p.called)
        
        with patch("grello.connection.print") as p:
            with patch("grello.connection.input") as i:
                v = "some_value"
                i.return_value = v
                ret = ui.verify_pin("some_url")
                self.assertTrue(p.called)
                self.assertTrue(i.called)
                self.assertEqual(ret, v, "Returned value is same as input")

class TestApi(unittest.TestCase):
    def test_connection_creating(self):
        
        app_key = "test_app_key"
        token_mode = "test_mode"
        token_expiration = "test_expiration"
        app_secret = "test_secret"
        
        ui = MagicMock()
        
        with patch("grello.connection.Connection") as con:
            
            con_instance = MagicMock()
            con.return_value = con_instance
            
            with patch("grello.connection.Context") as ctx:
                a = Api(app_key, ui, token_mode, token_expiration)
                a.connect(app_secret)
                
                con.assert_called_once_with(app_key=app_key, ui=ui, token_mode=token_mode, token_expiration=token_expiration)
                
                ctx.assert_called_once_with(con_instance)
                con_instance.connect.assert_called_once_with(app_secret)
    
    def test_quit(self):
        a = Api(None, None)
        a.context = MagicMock()
        a.connection = MagicMock()
        
        a.disconnect()
        # context.quit should be called on disconnecting
        a.context.quit.assert_called_once_with()
        a.connection.disconnect.assert_called_once_with()
    
    def test_global_getters(self):
        a = Api(None, None)
        
        a.context = MagicMock()
        obj_getter = a.context.repository.get_object
        
        a.get_me()
        obj_getter.assert_called_once_with(Member, id="me")
        
        obj_getter.reset_mock()
        a.get_board("test_id")
        obj_getter.assert_called_once_with(Board, id="test_id")

class TestConnection(unittest.TestCase):
    
    def test_request(self):
        app_key = "app_key"
        test_uri = "test_uri"
        token = "test_token"
        
        ui = MagicMock()
        ui.load_token.return_value = token
        
        request_error = RequestException
        
        with patch("grello.connection.requests") as r:
            r.exceptions.RequestException = request_error
            
            c = Connection(app_key, ui)
            
            r_get = MagicMock()
            r_get.status_code = 200
            
            c.session = r.Session()
            
            c_get = c.session.get
            c_get.return_value = r_get
            
            c.do_request(test_uri, {"param1":1}, "get", files={"file1":"f"})
            c_get.assert_called_once_with(
                'https://%s/%d/%s' % (c.api_host, c.api_version, test_uri),
                files={"file1":"f"},
                params={"param1":1}
            )
            
            c_get.reset_mock()
            r_get.status_code = 500
            r_get.raise_for_status.side_effect = RequestException()
            with self.assertRaises(RequestException, msg="exception after repeated failure"):
                c.do_request(test_uri, {})
            self.assertEqual(c_get.call_count, 4, "repeat request on failure")
            
            c_get.reset_mock()
            c_get.side_effect = RequestException()
            with self.assertRaises(RequestException, msg="Exception after repeated connection exception"):
                c.do_request(test_uri, {})
            self.assertEqual(c_get.call_count, 4, "repeat request on exception")
    
    def test_default_ui(self):
        c = Connection("app_key")
        self.assertIsInstance(c.ui, ConsoleUI, "default ui is set")
    
    def test_token_creation(self):
        app_secret = "test_secret"
        known_token = ("test_token", "test_secret")
        
        ui = MagicMock()
        ui.load_keys.return_value = known_token
        
        response = MagicMock()
        response.status_code = 200
        
        with patch("grello.connection.OAuth1Session") as s:
            s().get.return_value = response
            c = Connection("app_key", ui=ui)
            c.connect(app_secret)
        
            s().get.assert_called_once_with('https://api.trello.com/1/tokens/test_token', files=None, params=None)
            # token should be checked for validity
