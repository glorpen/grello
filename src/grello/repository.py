'''
Created on 08.01.2017

@author: glorpen
'''
from grello.registry import events
from grello.utils import get_uid
from grello.data import ApiData

class CachedObject(object):
    api_data = None
    object = None
    
    def __init__(self, object, api_data):
        super(CachedObject, self).__init__()
        self.api_data = api_data
        self.object = object

class Repository(object):
    
    def __init__(self, context):
        super(Repository, self).__init__()
        self.cache = {}
        self.services = {}
        self.ids = []
        
        self._context = context
    
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
                cache[uid].api_data.set_data(data)
        else:
            o = cls()
            #TODO: pass context?
            api_data = ApiData(o, context=self._context)
            
            cache[uid] = CachedObject(o, api_data)
            self.ids.append(id(o))
            
            api_data.set(data, kwargs)
            #self.events_dispatcher.trigger("factory.create", self, o)
        
        return cache[uid].object
    
    def get_object_api_data(self, obj):
        uid = self._get_object_key(obj.__class__, get_uid(obj.__class__, data=obj.__dict__))
        cache = self.get_object_cache(obj.__class__)
        return cache[uid].api_data
    
    @events.listener("label.removed")
    def on_object_remove(self, source, subject):
        uid = self._get_object_key(subject.__class__, subject.get_ids())
        self.get_object_cache(subject.__class__).pop(uid, None)
        self.ids.remove(id(subject))
    
    @events.listener("object.id_changed")
    def on_id_change(self, obj, old_ids):
        cache = self.get_object_cache(obj.__class__)
        
        old_uid = self._get_object_key(obj.__class__, old_ids)
        co = cache[old_uid]
        new_uid = self._get_object_key(obj.__class__, co.api_data.get_ids())
        
        del cache[old_uid]
        cache[new_uid] = co
    
    def is_known(self, obj):
        return id(obj) in self.ids
