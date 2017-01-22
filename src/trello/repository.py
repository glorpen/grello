'''
Created on 08.01.2017

@author: glorpen
'''
from trello.registry import events
from trello.utils import get_uid
from trello.meta import ApiData

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

class Repository(object):
    
    def __init__(self, events_dispatcher):
        super(Repository, self).__init__()
        self.cache = {}
        self.services = {}
        self.ids = []
        
        #self.events_dispatcher = events_dispatcher
        self.set_service(self)
    
    def _as_class_name(self, cls):
        if isinstance(cls, str):
            return cls
        else:
            return cls.__qualname__
    
    def get_object_cache(self, cls):
        k = self._as_class_name(cls)
        if k not in self.cache:
            self.cache[k]={}
        return self.cache[k]
    
    def set_service(self, o):
        self.services[o.__class__.__qualname__] = o
        self.ids.append(id(o))
    
    def get_service(self, cls):
        k = self._as_class_name(cls)
        return self.services[k]
    
    def get_objects(self, cls, data, **kwargs):
        return tuple(self.get_object(cls, i, **kwargs) for i in data)
    
    def _get_object_key(self, cls, id_dict={}):
        return"".join([cls.__qualname__, repr(list(id_dict.values()))])
    
    def get_object(self, cls, data=None, **kwargs):
        uid = self._get_object_key(cls, get_uid(cls, data, kwargs))
        
        cache = self.get_object_cache(cls)
        
        if uid in cache:
            if data:
                cache[uid][1].set_data(data)
        else:
            o = cls()
            api_data = ApiData(o)
            
            cache[uid] = (o, api_data)
            self.ids.append(id(o))
            
            api_data.set(data, kwargs)
            #self.events_dispatcher.trigger("factory.create", self, o)
        
        return cache[uid][0]
    
    def get_object_api_data(self, obj):
        uid = self._get_object_key(obj.__class__, get_uid(obj.__class__, data=obj.__dict__))
        cache = self.get_object_cache(obj.__class__)
        return cache[uid][1]
    
    @events.listener("label.removed")
    def on_object_remove(self, source, subject):
        uid = self._get_object_key(subject.__class__, subject.get_ids())
        self.get_object_cache(subject.__class__).pop(uid, None)
        self.ids.remove(id(subject))
    
    def is_known(self, obj):
        return id(obj) in self.ids
