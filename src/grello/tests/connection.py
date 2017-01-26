'''
Created on 26.01.2017

@author: glorpen
'''
import unittest
from grello.connection import ConsoleUI, Api
from unittest.mock import patch, MagicMock
from grello.objects import Member, Board

class TestUi(unittest.TestCase):
    
    def test_console(self):
        ui = ConsoleUI()
        
        self.assertEqual(ui.load_token(), None)
        
        with patch("grello.connection.print") as p:
            ui.save_token("asd")
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
                con_instance.assure_token.assert_called_once_with(app_secret)
    
    def test_quit(self):
        a = Api(None, None)
        a.context = MagicMock()
        
        a.quit()
        # context.quit should be called on disconnecting
        a.context.quit.assert_called_once_with()
    
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
    pass