'''
Created on 08.01.2017

@author: glorpen
'''

class Registry(object):
    
    def __init__(self):
        super(Registry, self).__init__()
        self.listeners = {}
    
    def get_listeners_for_event(self, event):
        if event not in self.listeners:
            self.listeners[event] = []
        
        return self.listeners[event]
    
    def listener(self, event):
        def inner(f):
            self.get_listeners_for_event(event).append(f)
            return f
        return inner

    def trigger(self, cache, event, source, subject, *args, **kwargs):
        for l in self.listeners.get(event, []):
            parent_name = l.__qualname__.rsplit(".", 1)[0]
            for v in cache.get_class_cache(parent_name).values():
                l(v, source, subject, *args, **kwargs)

api = Registry()

if __name__ == "__main__":
    class Test(object):
        
        _api_id_fields = ("id",)
        
        def __init__(self, *args, **kwargs):
            super(Test, self).__init__()
        
        @api.listener('label.assigned')
        def asd(self, source, subject, *args, **kwargs):
            print(args, kwargs)
    
    c = Factory(api=None)
    c.get(Test, id=123)
    api.trigger(c, "label.assigned", "test-source", "subject", "argg")
