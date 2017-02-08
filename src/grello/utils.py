'''
Created on 29.12.2016

@author: glorpen
'''

import datetime
import logging
from collections import OrderedDict
import inspect

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
    from grello import registry
    
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
        self._sig = inspect.signature(v)
        self._args = {}
    
    def _get_other_params(self, names):
        other = OrderedDict()
        for n,p in self._sig.parameters.items():
            if n not in names:
                other[n] = p
        
        return other
    
    def _get_next_positional_param(self, bound_args):
        for p in self._get_other_params(bound_args.keys()).values():
            if p.kind in (inspect.Parameter.POSITIONAL_ONLY, inspect.Parameter.POSITIONAL_OR_KEYWORD):
                return p
    
    def _bind_inline(self, args, kwargs, base_args={}):
        bound_args = base_args.copy()
        
        for a in args:
            p = self._get_next_positional_param(bound_args)
            if p is None:
                raise Exception("Positional arg not matched")
            bound_args[p.name] = a
        
        for kn, kv in kwargs.items():
            other_params = self._get_other_params(bound_args.keys())
            if kn not in other_params:
                raise Exception("Keyword arg not found")
            bound_args[kn] = kv
        
        return bound_args
    
    def bind(self, *args, **kwargs):
        self._args = self._bind_inline(args, kwargs, self._args)
    
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
        inline_args = self._bind_inline(args, kwargs, self._args)
        bp = self._sig.bind(**inline_args)
        return self.callable(*bp.args, **bp.kwargs)


def fill_args(f, obj=None, service=None, context=None):
    
    if context is None:
        from grello.context import manager
        context = manager.find_context(obj)
    
    af = ArgFiller(f).inject(context, obj)
    
    if obj or service:
        af.bind(obj or service)
    
    return af
