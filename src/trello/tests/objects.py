'''
Created on 14.01.2017

@author: glorpen
'''
import unittest
from unittest import mock
from trello.data import ApiData
from trello.objects import Attachment, Label, Card
from unittest.mock import patch

class TestAttachment(unittest.TestCase):
    
    @patch("trello.context.manager")
    def test_loading_request(self, manager):
        context = mock.MagicMock()
        
        manager.find_context().return_value = context
        
        a = Attachment()
        a.id = "some_id"
        a.card_id = "some_card_id"
        
        d = ApiData(a, context)
        d.load()
        
        context.connection.do_request.assert_called_with("cards/some_card_id/attachments/some_id", {"fields": None}, method="get")

class TestLabel(unittest.TestCase):
    
    @patch("trello.context.manager")
    def test_loading_request(self, manager):
        context = mock.MagicMock()
        
        manager.find_context.return_value = context
        
        a = Label()
        a.id = "some_id"
        d = ApiData(a, context)
        d.load()
        
        context.connection.do_request.assert_called_with('labels/some_id', {'fields': ('color', 'name', 'uses')}, method="get")
    
    @patch("trello.context.manager")
    def test_assigment_trigger(self, manager):
        context = mock.MagicMock()
        manager.find_context.return_value = context
        
        l = Label()
        ld = ApiData(l, context)
        
        c = Card()
        cd = ApiData(c, context)
        
        context.repository.get_object_api_data.side_effect = lambda obj: cd if obj is c  else ld
        
        ld.set_data({"id":"some_id"})
        cd.set_data({"id":"some_id"})
        
        ret = c.labels.add(label=l)
        self.assertIs(l, ret)
        
        context.event_dispatcher.trigger.assert_called_with('label.assigned', c, l, None)
