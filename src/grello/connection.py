'''
Created on 18.01.2017

@author: glorpen
'''

import requests
from requests_oauthlib.oauth1_session import OAuth1Session
from grello.utils import Logger
from grello.objects import Board, Member
from grello.context import Context

class ConsoleUI(object):
    def verify_pin(self, url):
        print("Go to the following link in your browser:")
        print(url)
        return input('What is the PIN? ')
    
    def save_token(self, token):
        print("New token: %r" % token)
    
    def load_token(self):
        return None

class Api(Logger):
    
    def __init__(self, app_key, ui, token_mode=None, token_expiration=None):
        super(Api, self).__init__()
        
        self.ui = ui
        self.app_key = app_key
        self.token_mode = token_mode
        self.token_expiration = token_expiration
    
    def connect(self, app_secret):
        c_args = {
            "app_key": self.app_key,
            "ui": self.ui,
        }
        
        if self.token_mode is not None:
            c_args['token_mode'] = self.token_mode
        if self.token_expiration is not None:
            c_args['token_expiration'] = self.token_expiration
        
        c = Connection(**c_args)
        
        self.context = Context(c)
        
        c.assure_token(app_secret)
    
    def quit(self):
        self.context.quit()
    
    def get_any(self, cls, **kwargs):
        return self.context.repository.get_object(cls, **kwargs)
    
    def get_board(self, board_id):
        return self.get_any(Board, id=board_id)
    
    def get_me(self):
        return self.get_any(Member, id="me")

class Connection(Logger):
    
    api_host = 'api.trello.com'
    api_version = 1
    app_name = "Grello"
    
    MODE_READ = 1<<0
    MODE_WRITE = 1<<1
    MODE_ACCOUNT = 1<<2
    
    def __init__(self, app_key, ui=None, token_mode=MODE_READ|MODE_WRITE|MODE_ACCOUNT, token_expiration = "30days"):
        super(Connection, self).__init__()
        self.app_key = app_key
        self.token_mode = token_mode
        self.token_expiration = token_expiration
        
        if ui is None:
            ui = ConsoleUI()
        
        self.ui = ui
        self.token = ui.load_token()
        
        self.session = requests.Session()
    
    def do_request(self, uri, parameters=None, method="get", files = None):
        self.logger.info("Requesting %s:%s", method, uri)
        
        parameters = parameters or {}
        parameters["key"] = self.app_key
        if self.token:
            parameters["token"] = self.token
        
        max_tries = 3
        last_exception = None
        for i in range(1,max_tries+1):
            
            try:
                r = getattr(self.session, method)("https://%s/%d/%s" % (self.api_host, self.api_version, uri), params=parameters, files=files)
                if r.status_code == 200:
                    return r.json()
                r.raise_for_status()
            
            except requests.exceptions.RequestException as e:
                last_exception = e
                continue
            
            finally:
                if i > 1:
                    self.logger.info("Try %d or %d", i, max_tries)
        
        raise last_exception

    def _get_token(self, client_secret):
        modes={self.MODE_READ: "read", self.MODE_WRITE: "write", self.MODE_ACCOUNT: "account"}
        scope = ",".join([name for v,name in modes.items() if v & self.token_mode])
        
        request_token_url = 'https://trello.com/1/OAuthGetRequestToken'
        authorize_url = 'https://trello.com/1/OAuthAuthorizeToken'
        access_token_url = 'https://trello.com/1/OAuthGetAccessToken'

        session = OAuth1Session(client_key=self.app_key, client_secret=client_secret)
        response = session.fetch_request_token(request_token_url)
        resource_owner_key, resource_owner_secret = response.get('oauth_token'), response.get('oauth_token_secret')
        
        url = "{authorize_url}?oauth_token={oauth_token}&scope={scope}&expiration={expiration}&name={app_name}".format(
            authorize_url=authorize_url,
            oauth_token=resource_owner_key,
            expiration=self.token_expiration,
            scope=scope,
            app_name=self.app_name
        )
        
        oauth_verifier = self.ui.verify_pin(url)
        
        session = OAuth1Session(client_key=self.app_key, client_secret=client_secret,
                                resource_owner_key=resource_owner_key, resource_owner_secret=resource_owner_secret,
                                verifier=oauth_verifier)
        return session.fetch_access_token(access_token_url)["oauth_token"]
    
    def assure_token(self, app_secret):
        
        def get_new_token():
            self.token = self._get_token(app_secret)
            self.ui.save_token(self.token)
        
        if self.token is None:
            get_new_token()
        else:
            try:
                self.get_token(self.token)
            except requests.exceptions.HTTPError as e:
                if e.response.status_code == 401:
                    get_new_token()
                else:
                    raise e from None
    
    def get_token(self, token_id):
        return self.do_request('tokens/%s' % token_id)
