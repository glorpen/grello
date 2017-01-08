'''
Created on 29.12.2016

@author: glorpen
'''

import logging
import inspect
import functools
import datetime
from collections import OrderedDict

# todo: cache + filling cached objects with new data if already fetched 

def python_to_trello(value):
    if isinstance(value, bool):
        return "true" if value else "false"
    
    if isinstance(value, datetime.datetime):
        return value.strftime('%Y-%m-%dT%H:%M:%S.%fZ')
    
    return value

class Logger(object):
    def __init__(self):
        super(Logger, self).__init__()
        self.logger = logging.getLogger(self.__class__.__name__)

class FieldData(object):
    loaded = False
    value = None
    data_version = None

class api_field(object):
    
    _setter = None
    _loader = None
    
    def __init__(self, loader=None):
        super(api_field, self).__init__()
        if loader is not None:
            self.loader(loader)
    
    def get_field_data(self, obj) -> FieldData:
        name = "__api_field"
        try:
            ret = getattr(obj, name)
        except AttributeError:
            ret = {}
            setattr(obj, name, ret)
        
        k = hash(self)
        
        if k not in ret:
            ret[k] = FieldData()
        
        return ret[k]
    
    def setter(self, f):
        self._setter = f
        return self
    
    def loader(self, f):
        self._loader = f
        return self
    
    def normalize_loaded_value(self, obj, v):
        return v
    
    def load(self, obj):
        field_data = self.get_field_data(obj)
        
        value = self._loader(obj, obj.get_api_data())
        value = self.normalize_loaded_value(obj ,value)
        
        field_data.value = value
        field_data.data_version = obj._api_data_version
        field_data.loaded = True
    
    def __set__(self, obj, value):
        if value == self.__get__(obj):
            return
        
        self._setter(obj, value)
        self.get_field_data(obj).value = value
    
    def is_fresh(self, field_data, obj):
        return field_data.data_version >= obj._api_data_version
    
    def __get__(self, obj, cls=None):
        field_data = self.get_field_data(obj)
        
        if not field_data.loaded or not self.is_fresh(field_data, obj):
            self.load(obj)
        
        return self.get_field_data(obj).value

class simple_api_field(api_field):
    
    writable = True
    
    def __init__(self, data_name, writable=True):
        super(simple_api_field, self).__init__(loader=self.simple_loader)
        self.data_name = data_name
        self.writable = writable
    
    def simple_loader(self, obj, data):
        return data[self.data_name]
    
    def _setter(self, obj, value):
        if not self.writable:
            raise AttributeError("Trello field %s is not writable" % self.data_name)
        
        value = python_to_trello(value)
        
        obj._api.do_request("%s/%s" % (obj.get_object_url(), self.data_name), parameters={"value": value}, method="put")

class api_listener(object):
    def __init__(self, event):
        super(api_listener, self).__init__()
        self.event = event
    
    def __call__(self, f):
        f._api_listener_event = self.event
        return f

class ApiObject(Logger):
    
    _api_id_fields = ("id",)
    _api_data = None
    _api_registered_fields = None
    _api_data_version = None
    _api_object_url = None
    
    @classmethod
    def get_registered_fields(cls):
        if cls._api_registered_fields is None:
            cls._find_tagged_properties()
        return cls._api_registered_fields
    
    @classmethod
    def _find_tagged_properties(cls):
        fields = {}
        for c in reversed(inspect.getmro(cls)):
            if hasattr(c, "__dict__"):
                for k,v in c.__dict__.items():
                    if isinstance(v, api_field):
                        fields[k] = v
        cls._api_registered_fields = fields
    
    def get_api_field_data(self, name):
        return self.get_registered_fields()[name].get_field_data(self)
    
    @property
    def is_loaded(self):
        return self._api_data is not None
    
    def __init__(self, api, **kwargs):
        super(ApiObject, self).__init__()
        
        self._api = api
        
        data = kwargs.pop("data", None)
        
        self.set_ids(**kwargs)
        
        if data is not None:
            self.set_data(data)
        
        #todo: validate id completion
    
    def set_ids(self, **kwargs):
        for name, value in kwargs.items():
            if name not in self._api_id_fields:
                raise Exception("%r is not a id field, available names: %r" % (name, self.id_fields))
            else:
                setattr(self, name, value)
    
    def set_data(self, data):
        self.set_ids(id=data["id"])
        self._api_data = data
        self._api_data_version = datetime.datetime.utcnow()
    
    def get_object_url(self):
        return self._api_object_url.format(**self.get_ids())
    
    def get_api_data(self):
        if self._api_data is None:
            data = self._api.do_request(self.get_object_url())
            self.set_data(data)
        
        return self._api_data
    
    def get_ids(self):
        return OrderedDict((name, getattr(self, name)) for name in self._api_id_fields)

def get_uid(cls, data=None, kwargs={}):
    ret = {}
    data = data or {}
    for n in cls._api_id_fields:
        if n in data or n in kwargs:
            ret[n] = data.get(n, kwargs.get(n))
        else:
            raise Exception("Not all ids found")
    return ret

class ApiCollection(Logger):
    
    _api_add = None
    _api_remove = None
    
    def __init__(self, items):
        super(ApiCollection, self).__init__()
        self.items = list(items)
    
    def add(self, *args, **kwargs):
        if self._api_add is None:
            raise Exception("Adding is not supported")
        
        item = self._api_add(*args, **kwargs)
        self.items.append(item)
        return item
    
    def remove(self, item):
        if self._api_remove is None:
            raise Exception("Removing is not supported")
        
        self._api_remove(item)
        self.items.remove(item)
    
    def __repr__(self):
        return '<ApiCollection: %r>' % (self.items,)
    
    def __iter__(self):
        yield from self.items

class collection_api_field(api_field):
    
    f_add = None
    f_remove = None
    
    def __init__(self, loader=None, always_fresh=False):
        super(collection_api_field, self).__init__(loader=loader)
        self.always_fresh = always_fresh
    
    def __call__(self, f):
        self.loader(f)
        return self
    
    def _setter(self, obj, value):
        raise AttributeError("Collection is not writable")
    
    def add(self, f):
        self.f_add = f
        return self
    
    def is_fresh(self, field_data, obj):
        return self.always_fresh or super(collection_api_field, self).is_fresh(field_data, obj)
    
    def remove(self, f):
        self.f_remove = f
        return self
    
    def normalize_loaded_value(self, obj, value):
        coll = ApiCollection(value)
        
        if self.f_add:
            coll._api_add = functools.partial(self.f_add, obj)
        if self.f_remove:
            coll._api_remove = functools.partial(self.f_remove, obj)
        
        return coll
