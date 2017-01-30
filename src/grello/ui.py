'''
Created on 30.01.2017

@author: glorpen
'''

class BaseUi(object):
    def verify_pin(self, url):
        raise NotImplementedError()
    
    def save_keys(self, token, token_secret):
        raise NotImplementedError()
    
    def load_keys(self):
        raise NotImplementedError()

class ConsoleUi(BaseUi):
    def verify_pin(self, url):
        print("Go to the following link in your browser:")
        print(url)
        return input('What is the PIN? ')
    
    def save_keys(self, token, token_secret):
        print("New token: %r, %r" % (token, token_secret))
    
    def load_keys(self):
        return None
