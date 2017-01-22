'''
Created on 08.01.2017

@author: glorpen
'''
from trello.utils import fill_args

class EventDispatcher(object):
    
    def __init__(self):
        super(EventDispatcher, self).__init__()
        self.listeners = {}
    
    def get_listeners_for_event(self, event):
        if event not in self.listeners:
            self.listeners[event] = []
        
        return self.listeners[event]
    
    def listener(self, event):
        def inner(f):
            self.get_listeners_for_event(event).append(f)
            return f
        return inner

    def trigger(self, context, event, source, subject, **kwargs):
        repository = context.repository
        
        for l in self.listeners.get(event, []):
            parent_name = l.__qualname__.rsplit(".", 1)[0]
            for v in repository.get_object_cache(parent_name).values():
                fill_args(l, v, context=context)(source, subject, **kwargs)
            
            try:
                service = repository.get_service(parent_name)
            except KeyError:
                pass
            else:
                fill_args(l, service, context=context)(source, subject, **kwargs)

events = EventDispatcher()
