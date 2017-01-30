'''
Created on 26.01.2017

@author: glorpen
'''
import unittest
from grello.ui import ConsoleUi, BaseUi
from unittest.mock import patch

class TestUi(unittest.TestCase):
    
    def test_console(self):
        ui = ConsoleUi()
        
        self.assertEqual(ui.load_keys(), None)
        
        with patch("sys.stdout") as s:
            ui.save_keys("t", "s")
            self.assertTrue(s.write.called)
        
        with patch("sys.stdout") as p:
            with patch("sys.stdin") as i:
                v = "some_value"
                i.readline.return_value = v
                ret = ui.verify_pin("some_url")
                self.assertTrue(p.write.called)
                self.assertEqual(ret, v, "Returned value is same as input")
    
    def test_abstract(self):
        ui = BaseUi()
        
        # just for coverage
        
        with self.assertRaises(NotImplementedError):
            ui.load_keys()
        with self.assertRaises(NotImplementedError):
            ui.save_keys("test", "test")
        with self.assertRaises(NotImplementedError):
            ui.verify_pin("test")
