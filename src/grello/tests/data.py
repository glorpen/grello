'''
Created on 14.01.2017

@author: glorpen
'''
import unittest
from grello.data import InvalidIdException, ApiData
from unittest.mock import patch, MagicMock

class SomeObject(object): pass

class TestApiData(unittest.TestCase):
    
    def assertObjectsIds(self, ids_data, expected_ids=False, msg=None):
        with patch("grello.registry.objects") as objects:
            objects.get_id_fields_name = MagicMock(return_value=("id","id2"))
        
            obj = SomeObject()
            ad = ApiData(obj, None)
            
            if expected_ids is False:
                with self.assertRaises(InvalidIdException, msg=msg):
                    ad.set(**ids_data)
            else:
                ad.set(**ids_data)
            
            objects.get_id_fields_name.assert_called_with(obj.__class__)
            
            if expected_ids is not False:
                for k,v in expected_ids.items():
                    self.assertEqual(getattr(obj, k), v, msg)
    
    def test_ids_validation(self):
        self.assertObjectsIds({"ids":{"unknown":1}}, False, "Throws exception when unknown id field is given")
        self.assertObjectsIds({"ids":{"id":1}}, False, "Throws exception when partial ids are given")
        self.assertObjectsIds({"ids":{"id":1,"id2":2}}, {"id":1,"id2":2}, "All ids are passed to object")
        self.assertObjectsIds({"ids":{"id2":2},"data":{"id":1, "some_data":"some"}}, {"id":1,"id2":2}, "Some ids are set from passed data")
