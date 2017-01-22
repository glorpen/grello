'''
Created on 29.12.2016

@author: glorpen
'''

import datetime
import logging
from inspect import signature
import functools

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

"""
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

class InvalidIdException(Exception):
    pass

class Loadable(Logger):
    _api_object_url = None
    _api_object_fields = tuple()
    _api_id_fields = ("id",)
    
    api_context = None
    
    def __init__(self, data=None, **kwargs):
        super(Loadable, self).__init__()
        
        self.set_ids(**kwargs)
        
        if data is not None:
            self.set_data(data)
        
        self.validate_ids()
    
    def validate_ids(self):
        for i in self._api_id_fields:
            try:
                if getattr(self, i) is None:
                    raise InvalidIdException("Empty id field: %r" % i)
            except AttributeError:
                raise InvalidIdException("Id field %r was not set" % i)
    
    def get_object_url(self):
        return self._api_object_url.format(**self.get_ids())
    
    def get_ids(self):
        return OrderedDict((name, getattr(self, name)) for name in self._api_id_fields)
    
    def load(self):
        data = self.api_context.connection.do_request(self.get_object_url(), {"fields": self._api_object_fields}, method="get")
        self.set_data(data)
    
    def _fetch_objects(self, url, cls, parameters=None, **kwargs):
        parameters = parameters or {}
        parameters.update({"fields": cls._api_object_fields})
        
        data = self._do_request(url, method="get", parameters=parameters)
        return self.api_context.cache.get_objects(cls, data=data, **kwargs)
    
    def _fetch_object(self, url, cls, parameters=None, method='post', **kwargs):
        return self.api_context.cache.get_object(cls,
            data=self._do_request(url, method=method, parameters=parameters),
            **kwargs
        )
    
    def _do_request(self, url, parameters=None, method='get'):
        url = url.format(**self.get_ids())
        return self._api.do_request(url, parameters, method)
    
    def set_ids(self, **kwargs):
        for name, value in kwargs.items():
            if name not in self._api_id_fields:
                raise InvalidIdException("%r is not a id field, available names: %r" % (name, self._api_id_fields))
            else:
                setattr(self, name, value)
    
    def set_data(self, data):
        if not hasattr(self, "id"):
            self.set_ids(id=data["id"])
"""

def get_uid(cls, data=None, kwargs={}):
    ret = {}
    data = data or {}
    from trello import meta
    # TODO: 
    for n in meta.registry.get_id_fields_name(cls):
        if n in data or n in kwargs:
            ret[n] = data.get(n, kwargs.get(n))
        else:
            raise Exception("Not all ids found")
    return ret

def fill_args(f, obj, context=None):
    p = signature(f).parameters
    
    kwargs = {}
    
    if context is None:
        from trello.repository import manager
        # TODO:
        context = manager.find_context(obj)
    
    if "connection" in p:
        kwargs["connection"] = context.connection
    if "repository" in p:
        kwargs["repository"] = context.repository
    if "api_data" in p:
        api_data = context.repository.get_object_api_data(obj)
        kwargs["api_data"] = api_data
    
    return functools.partial(f, obj, **kwargs)
