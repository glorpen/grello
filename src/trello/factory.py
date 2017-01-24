'''
Created on 08.01.2017

@author: glorpen
'''
from trello.registry import events
from trello.utils import get_uid

class Factory(object):
    
    def __init__(self, api):
        super(Factory, self).__init__()
        self.cache = {}
        self.api = api
    
    def get_class_cache(self, cls):
        if isinstance(cls, str):
            k = cls
        else:
            k = cls.__qualname__
        
        if k not in self.cache:
            self.cache[k]={}
        return self.cache[k]
    
    def get_multiple(self, cls, data, **kwargs):
        return tuple(self.get(cls, i, **kwargs) for i in data)
    
    def _get_key(self, cls, id_dict):
        return"".join([cls.__qualname__, repr(list(id_dict.values()))])
    
    def get(self, cls, data=None, **kwargs):
        uid = self._get_key(cls, get_uid(cls, data, kwargs))
        
        cache = self.get_class_cache(cls)
        
        if uid in cache:
            if data:
                cache[uid].set_data(data)
        else:
            cache[uid] = cls(api=self.api, data=data, **kwargs)
        
        return cache[uid]
    
    @events.listener("label.removed")
    def on_remove(self, source, subject):
        uid = self._get_key(subject.__class__, subject.get_ids())
        self.get_class_cache(subject.__class__).pop(uid, None)
