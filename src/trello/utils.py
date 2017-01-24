'''
Created on 29.12.2016

@author: glorpen
'''

import logging
import inspect
import functools
import datetime

# todo: cache + filling cached objects with new data if already fetched 

class _Logger(object):
    def __init__(self):
        super(_Logger, self).__init__()
        self.logger = logging.getLogger(self.__class__.__name__)

class api_field(object):
    
    _setter = None
    
    def __init__(self, loader):
        super(api_field, self).__init__()
        self._loader = loader
    
    def get_field_data(self, obj):
        name = "__api_field"
        try:
            ret = getattr(obj, name)
        except AttributeError:
            ret = {}
            setattr(obj, name, ret)
        
        k = hash(self)
        
        if k not in ret:
            ret[k] = {
                "listeners": []
            }
        
        return ret[k]
    
    def setter(self, f):
        self._setter = f
        return self
    
    def get_value(self, obj):
        return self.get_field_data(obj)["value"]
    
    def set_value(self, obj, value):
        self.get_field_data(obj)["value"] = value
    
    def set_data(self, obj, data):
        self.get_field_data(obj)["data"] = data
    
    def load(self, obj):
        field_data = self.get_field_data(obj)
        
        if "loaded" in field_data:
            raise Exception("Already loaded")
        
        for l in field_data.get("listeners"):
            # should set "data"
            l()
        
        data = field_data["data"]
        value = self._loader(obj, data)
        self.set_value(obj, value)
        
        field_data["loaded"] = True
        field_data.pop("data", None)
    
    def add_before_load_listener(self, obj, cb):
        field_data = self.get_field_data(obj)
        field_data["listeners"].append(cb)
    
    def __set__(self, obj, value):
        if value == self.__get__(obj):
            return
        
        self._setter(obj, value)
        self.set_value(obj, value)
    
    def __get__(self, obj, cls=None):
        field_data = self.get_field_data(obj)
        
        is_loaded = "loaded" in field_data
        
        if not is_loaded:
            self.load(obj)
        
        return self.get_value(obj)

class simple_api_field(api_field):
    
    writable = True
    
    def __init__(self, data_name, writable=True):
        super(simple_api_field, self).__init__(self.simple_loader)
        self.data_name = data_name
        self.writable = writable
    
    def simple_loader(self, obj, data):
        return data[self.data_name]
    
    def loader(self, f):
        self._loader = f
        return self
    
    def _setter(self, obj, value):
        if not self.writable:
            raise AttributeError("Trello field %s is not writable" % self.data_name)
        
        if isinstance(value, bool):
            value = "true" if value else "false"
        
        if isinstance(value, datetime.datetime):
            value = value.strftime('%Y-%m-%dT%H:%M:%S.%fZ')
        
        obj._api.do_request("%s/%s" % (obj._get_data_url(), self.data_name), parameters={"value": value}, method="put")

class ApiObject(_Logger):
    
    is_loaded = False
    _id_fields = ("id",)
    
    def __init__(self, api, **kwargs):
        super(ApiObject, self).__init__()
        
        self._api = api
        
        data = kwargs.pop("data", None)
        
        if data is not None:
            self._load_ids(**dict((k, data.get(k, kwargs.get(k))) for k in self._id_fields if k in data or k in kwargs))
            self._load_data(data)
        else:
            self._load_ids(**kwargs)
            
            for _name, obj in inspect.getmembers(self.__class__, lambda x: isinstance(x, (api_field,))):
                obj.add_before_load_listener(self, self._assure_loaded)
    
    def _load_ids(self, **kwargs):
        for name in self._id_fields:
            if name not in kwargs:
                raise Exception("Not all ids given")
            else:
                setattr(self, name, kwargs.get(name))
        
    def _load_data(self, data):
        for _name, obj in inspect.getmembers(self.__class__, lambda x: isinstance(x, (api_field,))):
            obj.set_data(self, data)
        
        self._on_data_load(data)
        
        self.is_loaded = True
    
    def _get_data_url(self):
        raise NotImplementedError()
    
    def _on_data_load(self, data):
        pass
    
    def _assure_loaded(self):
        if self.is_loaded == False:
            data = self._api.do_request(self._get_data_url())
            self._load_data(data)

class ApiCollection(_Logger):
    
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
    
    def _setter(self, obj, value):
        raise AttributeError("Collection is not writable")
    
    def add(self, f):
        self.f_add = f
        return self
    
    def remove(self, f):
        self.f_remove = f
        return self
    
    def set_value(self, obj, value):
        coll = ApiCollection(value)
        
        if self.f_add:
            coll._api_add = functools.partial(self.f_add, obj)
        if self.f_remove:
            coll._api_remove = functools.partial(self.f_remove, obj)
        
        super(collection_api_field, self).set_value(obj, coll)
