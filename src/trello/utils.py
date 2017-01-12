'''
Created on 29.12.2016

@author: glorpen
'''

import functools
import datetime
from collections import OrderedDict
import logging

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

class ApiData(object):
    data_to_load = None
    
    def __init__(self, data_requestor, loader, setter=None):
        super(ApiData, self).__init__()
        
        self._data_requestor = data_requestor
        self._loader = loader
        self._setter = setter
    
    def _do_load(self, data):
        return self._loader(data)
    
    @property
    def loaded(self):
        return hasattr(self.value)
    
    def get_value(self):
        
        if self.data_to_load is None and not hasattr(self, "value"):
            self._data_requestor()
        
        if self.data_to_load is not None:
            self.value = self._do_load(self.data_to_load)
            self.data_to_load = None
        
        try:
            return self.value
        except AttributeError:
            raise Exception("No data to load") from None
    
    def set_value(self, value):
        if self._setter is None:
            raise Exception("Setting value is not supported")
        self._setter(value)
        self.value = value
        self.data_to_load = None

class api_field(object):
    
    f_loader = None
    f_setter = None
    
    def __init__(self, loader=None):
        super(api_field, self).__init__()
        if loader:
            self.loader(loader)
    
    def get_new_data(self, obj):
        return ApiData(
            loader = functools.partial(self.f_loader, obj),
            setter = functools.partial(self.f_setter, obj) if self.f_setter else None,
            data_requestor = obj.load
        )
    
    def get_data(self, obj):
        name = "api_field_data_%d" % hash(self)
        try:
            ret = getattr(obj, name)
        except AttributeError:
            ret = self.get_new_data(obj)
            setattr(obj, name, ret)
        
        return ret
    
    def __get__(self, obj, cls=None):
        return self.get_data(obj).get_value()
    
    def __set__(self, obj, value):
        return self.get_data(obj).set_value(value)
    
    def loader(self, f):
        self.f_loader = f
        return self
    
    def setter(self, f):
        self.f_setter = f
        return self

class simple_api_field(api_field):
    
    writable = True
    
    def __init__(self, data_name, writable=True):
        super(simple_api_field, self).__init__(loader=self.simple_loader)
        self.data_name = data_name
        self.writable = writable
    
    def simple_loader(self, obj, data):
        return data[self.data_name]
    
    def f_setter(self, obj, value):
        if not self.writable:
            raise AttributeError("Trello field %s is not writable" % self.data_name)
        
        # skip request if value didn't change
        if self.__get__(obj) == value:
            return
        
        value = python_to_trello(value)
        
        obj._api.do_request("%s/%s" % (obj.get_object_url(), self.data_name), parameters={"value": value}, method="put")

class ApiMetadata(object):
    
    loaded = False
    
    def __init__(self, obj):
        super(ApiMetadata, self).__init__()
        self.obj = obj
    
    def get_fields(self):
        fields = {}
        visited = set()
        for cls in self.obj.__class__.__mro__:
            for k,v in cls.__dict__.items():
                if k not in visited and isinstance(v, api_field):
                    fields[k] = v.get_data(self.obj)
                visited.add(k)
        return fields
    
    def load(self, data):
        for v in self.get_fields().values():
            v.data_to_load = data
        self.loaded = True
    
    def __getitem__(self, name):
        return self.get_fields()[name]

class Loadable(Logger):
    _api_object_url = None
    _api_object_fields = tuple()
    _api_id_fields = ("id",)
    
    def __init__(self, api, data=None, **kwargs):
        super(Loadable, self).__init__()
        self._api = api
        
        self.set_ids(**kwargs)
        
        if data is not None:
            self.set_data(data)
        
        #TODO: validate id completion
    
    def get_object_url(self):
        return self._api_object_url.format(**self.get_ids())
    
    def get_ids(self):
        return OrderedDict((name, getattr(self, name)) for name in self._api_id_fields)
    
    def load(self):
        data = self._api.do_request(self.get_object_url(), {"fields": self._api_object_fields}, method="get")
        self.set_data(data)
    
    def _fetch_objects(self, url, cls, parameters=None, **kwargs):
        parameters = parameters or {}
        parameters.update({"fields": cls._api_object_fields})
        
        data = self._do_request(url, method="get", parameters=parameters)
        return self._api.get_objects(cls, data=data, **kwargs)
    
    def _fetch_object(self, url, cls, parameters=None, method='post', **kwargs):
        return self._api.get_object(cls,
            data=self._do_request(url, method=method, parameters=parameters),
            **kwargs
        )
    
    def _do_request(self, url, parameters=None, method='get'):
        url = url.format(**self.get_ids())
        return self._api.do_request(url, parameters, method)
    
    def set_ids(self, **kwargs):
        for name, value in kwargs.items():
            if name not in self._api_id_fields:
                raise Exception("%r is not a id field, available names: %r" % (name, self._api_id_fields))
            else:
                setattr(self, name, value)
    
    def set_data(self, data):
        if not hasattr(self, "id"):
            self.set_ids(id=data["id"])

def get_uid(cls, data=None, kwargs={}):
    ret = {}
    data = data or {}
    for n in cls._api_id_fields:
        if n in data or n in kwargs:
            ret[n] = data.get(n, kwargs.get(n))
        else:
            raise Exception("Not all ids found")
    return ret

class ApiCollection(object):
    
    _api_add = None
    _api_remove = None
    
    def __init__(self, items_generator, adder=None, remover=None):
        super(ApiCollection, self).__init__()
        self._items_generator = items_generator
        
        self._api_add = adder
        self._api_remove = remover
    
    @property
    def items(self):
        try:
            return self._items
        except AttributeError:
            self._items = list(self._items_generator())
            return self._items
    
    @property
    def loaded(self):
        return hasattr(self, "_items")
    
    def add(self, *args, **kwargs):
        if self._api_add is None:
            raise Exception("Adding is not supported")
        
        item = self._api_add(*args, **kwargs)
        
        if not self.loaded:
            return item
        
        self.items.append(item)
        return item
    
    def remove(self, item):
        if self._api_remove is None:
            raise Exception("Removing is not supported")
        
        self._api_remove(item)
        
        if not self.loaded:
            return
        
        self.items.remove(item)
    
    def __repr__(self):
        return '<ApiCollection: %r>' % (self.items,)
    
    def __iter__(self):
        yield from self.items

class CollectionApiData(ApiData):
    
    def __init__(self, adder=None, remover=None, **kwargs):
        super(CollectionApiData, self).__init__(**kwargs)
        
        self.f_add = adder
        self.f_remove = remover
    
    def _do_load(self, data):
        loader = functools.partial(super(CollectionApiData, self)._do_load, data)
    
        return ApiCollection(
            loader,
            adder=self.f_add,
            remover=self.f_remove
        )
    
    def set_value(self, value):
        raise AttributeError("Collection cannot be replaced")
    
    def get_value(self):
        try:
            return self.value
        except AttributeError:
            pass
        
        return super(CollectionApiData, self).get_value()

class collection_api_field(api_field):
    
    f_add = None
    f_remove = None
    
    def setter(self, f):
        raise AttributeError("Collection cannot be replaced")
    
    def add(self, f):
        self.f_add = f
        return self
    
    def remove(self, f):
        self.f_remove = f
        return self
    
    def get_new_data(self, obj):
        return CollectionApiData(
            loader = functools.partial(self.f_loader, obj),
            remover = functools.partial(self.f_remove, obj) if self.f_remove else None,
            adder = functools.partial(self.f_add, obj) if self.f_add else None,
            data_requestor = obj.load
        )
    
class ApiObject(Loadable):
    def __init__(self, *args, **kwargs):
        self.api_data = ApiMetadata(self)
        super(ApiObject, self).__init__(*args, **kwargs)
    
    def set_data(self, data):
        super(ApiObject, self).set_data(data)
        self.api_data.load(data)
