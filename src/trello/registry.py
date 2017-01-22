'''
Created on 08.01.2017

@author: glorpen
'''
from trello.utils import fill_args
from trello.fields import api_field
import re

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

class RegisteredObject(object):
    
    re_id_fields = re.compile(r"{([^}]+)}")
    
    def __init__(self, cls, url, fields):
        super(RegisteredObject, self).__init__()
        self.cls = cls
        self.url = url
        self.fields = fields
    
    @property
    def id_fields(self):
        return self.re_id_fields.findall(self.url)

class ApiObjectRegistry(object):
    
    def __init__(self):
        super(ApiObjectRegistry, self).__init__()
        
        self._objects = {}
        self._class_fields = {}
    
    def register(self, url, default_fields=None):
        def inner(cls):
            self._objects[cls.__qualname__] = RegisteredObject(cls, url, default_fields)
            return cls
        return inner
    
    def get_fields(self, cls):
        try:
            ret = self._class_fields[id(cls)]
        except KeyError:
            fields = {}
            visited = set()
            for c in cls.__mro__:
                for k,v in c.__dict__.items():
                    if k not in visited and isinstance(v, api_field):
                        fields[k] = v
                    visited.add(k)
            ret = self._class_fields[id(cls)] = fields
        
        return ret
    
    def get_id_fields_name(self, cls):
        return self._objects[cls.__qualname__].id_fields
    
    def get_default_fields(self, cls):
        return self._objects[cls.__qualname__].fields
    
    def get_url(self, cls):
        return self._objects[cls.__qualname__].url 

objects = ApiObjectRegistry()
api_object = objects.register
