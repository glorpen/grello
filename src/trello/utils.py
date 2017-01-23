'''
Created on 29.12.2016

@author: glorpen
'''

import datetime
import logging
from inspect import signature
import functools
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

def get_uid(cls, data=None, kwargs={}):
    from trello import registry
    
    ret = OrderedDict()
    data = data or {}
    for n in registry.objects.get_id_fields_name(cls):
        if n in data or n in kwargs:
            ret[n] = data.get(n, kwargs.get(n))
        else:
            raise Exception("Not all ids found")
    return ret

class ArgFiller(object):
    
    def __init__(self, f):
        super(ArgFiller, self).__init__()
        self.callable = f
    
    @property
    def callable(self):
        return self._f
    
    @callable.setter
    def callable(self, v):
        self._f = v
        self._sig = signature(v)
    
    def bind(self, *args, **kwargs):
        bsig = self._sig.bind_partial(*args, **kwargs)
        self.callable = functools.partial(self.callable, *bsig.args, **bsig.kwargs)
        return self
    
    def inject(self, context, obj=None):
        p = self._sig.parameters
        
        kwargs = {}
        
        if "connection" in p:
            kwargs["connection"] = context.connection
        if "repository" in p:
            kwargs["repository"] = context.repository
        if "event_dispatcher" in p:
            kwargs["event_dispatcher"] = context.event_dispatcher
        
        if obj:
            if "api_data" in p:
                api_data = context.repository.get_object_api_data(obj)
                kwargs["api_data"] = api_data
        
        self.bind(**kwargs)
        
        return self
    
    def __call__(self, *args, **kwargs):
        return self.callable(*args, **kwargs)

def fill_args(f, obj=None, service=None, context=None):
    
    if context is None:
        from trello.context import manager
        context = manager.find_context(obj)
    
    af = ArgFiller(f).inject(context, obj)
    
    if obj or service:
        af.bind(obj or service)
    
    return af.callable
