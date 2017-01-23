'''
Created on 22.01.2017

@author: glorpen
'''
from trello.repository import Repository
from trello.registry import events, BoundEventDispatcher

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
        self.event_dispatcher = BoundEventDispatcher(self)
        
        self.repository.set_service(self)
        self.repository.set_service(self.event_dispatcher)
        self.repository.set_service(self.repository)
        self.repository.set_service(self.connection)
    
    def quit(self):
        manager.remove(self)
