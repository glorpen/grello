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

def get_uid(cls, data=None, kwargs={}):
    ret = {}
    data = data or {}
    from trello import registry
    # TODO: 
    for n in registry.objects.get_id_fields_name(cls):
        if n in data or n in kwargs:
            ret[n] = data.get(n, kwargs.get(n))
        else:
            raise Exception("Not all ids found")
    return ret

def fill_args(f, obj, context=None):
    p = signature(f).parameters
    
    kwargs = {}
    
    if context is None:
        from trello.context import manager
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
