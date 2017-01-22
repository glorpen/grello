'''
Created on 18.01.2017

@author: glorpen
'''

from collections import OrderedDict
from trello import registry

class InvalidIdException(Exception):
    pass

class ApiData(object):
    
    loaded = False
    _collected_fields = None
    
    def __init__(self, obj, context):
        super(ApiData, self).__init__()
        self.obj = obj
        self._context = context
    
    @property
    def fields(self):
        if self._collected_fields is None:
            fields = {}
            for k,f in registry.objects.get_fields(self.obj.__class__).items():
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
        return registry.objects.get_id_fields_name(self.obj.__class__)
    
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
        
        for f in registry.objects.get_fields(self.obj.__class__).values():
            f.get_data(self.obj).data_to_load = data
    
        self.loaded = True
    
    def load(self):
        data = self._context.connection.do_request(self.get_object_url(), {"fields": registry.objects.get_default_fields(self.obj.__class__)}, method="get")
        self.set_data(data)
    
    def get_field(self, api_field_instance):
        return self.fields[id(api_field_instance)]
    
    def get_object_url(self):
        return registry.objects.get_url(self.obj.__class__).format(**self.get_ids())
    
    def get_ids(self):
        return OrderedDict((name, getattr(self.obj, name)) for name in self.get_id_fields_name())
    
    def fetch_objects(self, url, cls, parameters=None, **kwargs):
        parameters = parameters or {}
        parameters.update({"fields": registry.objects.get_default_fields(cls)})
        
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
