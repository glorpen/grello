'''
Created on 22.01.2017

@author: glorpen
'''
from trello.repository import Repository
from trello.registry import events

class ObjectNotKnownException(Exception):
    pass

class Manager(object):
    
    def __init__(self):
        super(Manager, self).__init__()
        self.contexts = []
    
    def add(self, context):
        self.contexts.append(context)
    
    def remove(self, context):
        self.contexts.remove(context)
    
    def find_context(self, obj):
        for c in self.contexts:
            if c.repository.is_known(obj):
                return c
        raise ObjectNotKnownException()

manager = Manager()

class Context(object):
    def __init__(self, connection):
        super(Context, self).__init__()
        
        manager.add(self)
        
        self.repository = Repository(self)
        self.connection = connection
        
        self.repository.set_service(self)
    
    def quit(self):
        manager.remove(self)
    
    def trigger(self, event, source, subject, **kwargs):
        events.trigger(self, event, source, subject, **kwargs)
