'''
Created on 21.01.2017

@author: glorpen
'''
import functools
from grello.utils import python_to_trello, fill_args
from inspect import signature

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
    
    def create_data(self, obj, api_data):
        return ApiData(
            loader = fill_args(self.f_loader, obj),
            setter = fill_args(self.f_setter, obj) if self.f_setter else None,
            data_requestor = api_data.load
        )
    
    def get_data(self, obj):
        from grello.context import manager
        # TODO:
        context = manager.find_context(obj)
        api_data = context.repository.get_object_api_data(obj)
        
        return api_data.get_field(self)
    
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
    
    def f_setter(self, obj, value, connection, api_data):
        if not self.writable:
            raise AttributeError("Trello field %s is not writable" % self.data_name)
        
        # skip request if value didn't change
        if self.__get__(obj) == value:
            return
        
        value = python_to_trello(value)
        
        connection.do_request("%s/%s" % (api_data.get_object_url(), self.data_name), parameters={"value": value}, method="put")


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
    
    def create_data(self, obj, api_data):
        return CollectionApiData(
            loader = fill_args(self.f_loader, obj),
            remover = fill_args(self.f_remove, obj) if self.f_remove else None,
            adder = fill_args(self.f_add, obj) if self.f_add else None,
            data_requestor = api_data.load
        )
