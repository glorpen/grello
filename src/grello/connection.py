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
    
    def save_keys(self, token, token_secret):
        print("New token: %r, %r" % (token, token_secret))
    
    def load_keys(self):
        return None

class Api(Logger):
    
    def __init__(self, app_key, ui, token_mode=None, token_expiration=None):
        super(Api, self).__init__()
        
        self.ui = ui
        self.app_key = app_key
        self.token_mode = token_mode
        self.token_expiration = token_expiration
    
        c_args = {
            "app_key": self.app_key,
            "ui": self.ui,
        }
        
        if self.token_mode is not None:
            c_args['token_mode'] = self.token_mode
        if self.token_expiration is not None:
            c_args['token_expiration'] = self.token_expiration
        
        self.connection = Connection(**c_args)
        self.context = Context(self.connection)
        
    def connect(self, app_secret):
        self.connection.connect(app_secret)
    
    def disconnect(self):
        self.connection.disconnect()
        self.context.quit()
    
    def get_any(self, cls, **kwargs):
        return self.context.repository.get_object(cls, **kwargs)
    
    def get_board(self, board_id):
        return self.get_any(Board, id=board_id)
    
    def get_me(self):
        return self.get_any(Member, id="me")

class NotAuthorizedException(Exception):
    pass
class NotFoundException(Exception):
    pass

class Connection(Logger):
    
    api_host = 'api.trello.com'
    api_version = 1
    app_name = "Grello"
    
    MODE_READ = 1<<0
    MODE_WRITE = 1<<1
    MODE_ACCOUNT = 1<<2
    
    session = None
    
    def __init__(self, app_key, ui=None, token_mode=MODE_READ|MODE_WRITE|MODE_ACCOUNT, token_expiration = "30days"):
        super(Connection, self).__init__()
        self.app_key = app_key
        self.token_mode = token_mode
        self.token_expiration = token_expiration
        
        if ui is None:
            ui = ConsoleUI()
        
        self.ui = ui
    
    def connect(self, app_secret):
        self.session = self.get_session(app_secret)
    
    def _create_session(self, resource_key, resource_secret, app_secret):
        return OAuth1Session(
            self.app_key,
            client_secret=app_secret,
            resource_owner_key=resource_key,
            resource_owner_secret=resource_secret
        )
    
    def disconnect(self):
        if self.session:
            self.session.close()
            self.session = None
    
    def do_request(self, *args, **kwargs):
        return self._do_session_request(self.session, *args, **kwargs)
    
    def _do_session_request(self, session, uri, parameters=None, method="get", files = None, max_retries = 3):
        self.logger.info("Requesting %s:%s", method, uri)
        
        last_exception = None
        for i in range(0, max_retries+1):
            
            if i > 0:
                self.logger.info("Retry %d of %d", i, max_retries)
            
            try:
                r = getattr(session, method)("https://%s/%d/%s" % (self.api_host, self.api_version, uri), params=parameters, files=files)
                if r.status_code == 200:
                    return r.json()
                elif r.status_code == 401:
                    raise NotAuthorizedException()
                elif r.status_code == 404:
                    raise NotFoundException()
                
                r.raise_for_status()
            
            except requests.exceptions.RequestException as e:
                last_exception = e
                continue
        
        raise last_exception

    def _do_auth(self, client_secret):
        modes={self.MODE_READ: "read", self.MODE_WRITE: "write", self.MODE_ACCOUNT: "account"}
        scope = ",".join([name for v,name in modes.items() if v & self.token_mode])
        
        request_token_url = 'https://trello.com/1/OAuthGetRequestToken'
        authorize_url = 'https://trello.com/1/OAuthAuthorizeToken'
        access_token_url = 'https://trello.com/1/OAuthGetAccessToken'

        session = OAuth1Session(client_key=self.app_key, client_secret=client_secret)
        response = session.fetch_request_token(request_token_url)
        resource_owner_key = response.get('oauth_token')
        resource_owner_secret = response.get('oauth_token_secret')
        
        url = "{authorize_url}?oauth_token={oauth_token}&scope={scope}&expiration={expiration}&name={app_name}".format(
            authorize_url=authorize_url,
            oauth_token=resource_owner_key,
            expiration=self.token_expiration,
            scope=scope,
            app_name=self.app_name
        )
        
        oauth_verifier = self.ui.verify_pin(url)
        
        session = OAuth1Session(
            client_key=self.app_key,
            client_secret=client_secret,
            resource_owner_key=resource_owner_key,
            resource_owner_secret=resource_owner_secret,
            verifier=oauth_verifier
        )
        response = session.fetch_access_token(access_token_url)
        return (response.get('oauth_token'), response.get('oauth_token_secret'))
    
    def get_session(self, app_secret):
        
        keys = self.ui.load_keys()
        
        if keys is None:
            token = token_secret = None
        else:
            token, token_secret = keys
        
        if token is not None:
            session = self.get_session_for_token(token, token_secret, app_secret)
        
        if token is None or session is None:
            token, token_secret = self._do_auth(app_secret)
            self.ui.save_keys(token, token_secret)
            session = self._create_session(token, token_secret, app_secret)
        
        return session
    
    def get_session_for_token(self, token, token_secret, app_secret):
        session = self._create_session(token, token_secret, app_secret)
        try:
            self._do_session_request(session, 'tokens/%s' % token)
        except NotAuthorizedException:
            return None
        
        return session
