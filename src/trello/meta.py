'''
Created on 18.01.2017

@author: glorpen
'''

import re
from trello.fields import api_field
from collections import OrderedDict

"""
class ApiClassMetadata(object):
    def __init__(self, cls, url, default_fields=None):
        super(ApiClassMetadata, self).__init__()
        
        self.cls = cls
        self.url = url
        self.default_fields = default_fields or tuple()
    
    def get_fields(self):
        fields = {}
        visited = set()
        for cls in self.cls.__mro__:
            for k,v in self.cls.__dict__.items():
                if k not in visited and isinstance(v, api_field):
                    fields[k] = v
                visited.add(k)
        return fields
    
    #def get_id_fields(self):
    #    pass
    
    #def get_url(self):
    #    pass

class ApiMetadata(ApiClassMetadata):
    loaded = False
    
    def __init__(self, obj, *args, **kwargs):
        super(ApiMetadata, self).__init__(obj.__class__, *args, **kwargs)
        self.obj = obj
    
    def get_fields(self):
        ret = {}
        for k,v in super(ApiMetadata, self).get_fields().items():
            ret[k] = v.get_data(self.obj)
        return ret
    
    def load(self, data):
        for v in self.get_fields().values():
            v.data_to_load = data
        self.loaded = True
    
    def __getitem__(self, name):
        return self.get_fields()[name]
"""

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

registry = ApiObjectRegistry()
api_metadata = registry.register

class InvalidIdException(Exception):
    pass

class ApiData(object):
    
    loaded = False
    _collected_fields = None
    
    def __init__(self, obj):
        super(ApiData, self).__init__()
        self.obj = obj
    
    @property
    def _context(self):
        from trello.repository import manager
        return manager.find_context(self.obj)
    
    @property
    def fields(self):
        if self._collected_fields is None:
            fields = {}
            for k,f in registry.get_fields(self.obj.__class__).items():
                fields[id(f)] = f.create_data(self.obj, self)
            self._collected_fields = fields
        
        return self._collected_fields
    
    def set(self, data=None, ids=None):
        if ids:
            self.set_ids(**ids)
        
        if data is not None:
            self.set_data(data)
        
        self.validate_ids()
    
    def get_id_fields_name(self):
        return registry.get_id_fields_name(self.obj.__class__)
    
    def validate_ids(self):
        for i in self.get_id_fields_name():
            try:
                if getattr(self.obj, i) is None:
                    raise InvalidIdException("Empty id field: %r" % i)
            except AttributeError:
                raise InvalidIdException("Id field %r was not set" % i)
        
    def set_ids(self, **kwargs):
        for name, value in kwargs.items():
            if name not in self.get_id_fields_name():
                raise InvalidIdException("%r is not a id field, available names: %r" % (name, self._api_id_fields))
            else:
                setattr(self.obj, name, value)
    
    def set_data(self, data):
        if not hasattr(self.obj, "id"):
            self.set_ids(id=data["id"])
        
        for f in registry.get_fields(self.obj.__class__).values():
            f.get_data(self.obj).data_to_load = data
    
        self.loaded = True
    
    def load(self):
        data = self._context.connection.do_request(self.get_object_url(), {"fields": registry.get_default_fields(self.obj.__class__)}, method="get")
        self.set_data(data)
    
    def get_field(self, api_field_instance):
        return self.fields[id(api_field_instance)]
    
    def get_object_url(self):
        return registry.get_url(self.obj.__class__).format(**self.get_ids())
    
    def get_ids(self):
        return OrderedDict((name, getattr(self.obj, name)) for name in self.get_id_fields_name())
    
    def fetch_objects(self, url, cls, parameters=None, **kwargs):
        parameters = parameters or {}
        parameters.update({"fields": registry.get_default_fields(cls)})
        
        data = self.do_request(url, method="get", parameters=parameters)
        return self._context.repository.get_objects(cls, data=data, **kwargs)
    
    def fetch_object(self, url, cls, parameters=None, method='post', **kwargs):
        return self.api_context.cache.get_object(cls,
            data=self._do_request(url, method=method, parameters=parameters),
            **kwargs
        )
    
    def do_request(self, url, parameters=None, method='get'):
        url = url.format(**self.get_ids())
        return self._context.connection.do_request(url, parameters, method)
    
    