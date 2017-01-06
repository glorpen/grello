from trello.utils import Logger
import requests
from requests_oauthlib.oauth1_session import OAuth1Session
from trello.objects import Board

class Api(Logger):
    
    api_host = 'api.trello.com'
    api_version = 1
    
    def __init__(self, app_key, token=None):
        super(Api, self).__init__()
        self.app_key = app_key
        self.token = token
        
        self.session = requests.Session()
    
    def do_request(self, uri, parameters=None, method="get"):
        self.logger.info("Requesting %s:%s", method, uri)
        
        parameters = parameters or {}
        parameters["key"] = self.app_key
        if self.token:
            parameters["token"] = self.token
        
        max_tries = 3
        for i in range(1,max_tries+1):
            try:
                r = getattr(self.session, method)("https://%s/%d/%s" % (self.api_host, self.api_version, uri), params=parameters)
                if r.status_code == 200:
                    break
            except requests.exceptions.ConnectionError:
                continue
            finally:
                if i > 1:
                    self.logger.info("Try %d or %d", i, max_tries)
        r.raise_for_status()
        return r.json()

    def verify_pin(self, url):
        print("Go to the following link in your browser:")
        print(url)
        return input('What is the PIN? ')
    
    def _get_token(self, client_secret, mode="r", expiration="30days"):
        modes=("read","write")
        scope = ",".join([i for i in modes if i[0] in mode])
        
        request_token_url = 'https://trello.com/1/OAuthGetRequestToken'
        authorize_url = 'https://trello.com/1/OAuthAuthorizeToken'
        access_token_url = 'https://trello.com/1/OAuthGetAccessToken'

        session = OAuth1Session(client_key=self.app_key, client_secret=client_secret)
        response = session.fetch_request_token(request_token_url)
        resource_owner_key, resource_owner_secret = response.get('oauth_token'), response.get('oauth_token_secret')
        
        url = "{authorize_url}?oauth_token={oauth_token}&scope={scope}&expiration={expiration}&name=Grello".format(
            authorize_url=authorize_url,
            oauth_token=resource_owner_key,
            expiration=expiration,
            scope=scope,
        )
        
        oauth_verifier = self.verify_pin(url)
        
        session = OAuth1Session(client_key=self.app_key, client_secret=client_secret,
                                resource_owner_key=resource_owner_key, resource_owner_secret=resource_owner_secret,
                                verifier=oauth_verifier)
        return session.fetch_access_token(access_token_url)["oauth_token"]
    
    def assure_token(self, app_secret):
        if self.token is None:
            self.token = self._get_token(app_secret, "rw")
        else:
            try:
                self.get_token(self.token)
            except requests.exceptions.HTTPError as e:
                if e.response.status_code == 401:
                    self.token = self._get_token(app_secret, "rw")
                else:
                    raise e from None

    
    def get_boards(self):
        return tuple(Board(id=i, api=self) for i in self.do_request("members/me")["idBoards"])
    
    def get_board(self, board_id):
        return Board(id=board_id, api=self)
    
    def get_token(self, token_id):
        return self.do_request('tokens/%s' % token_id)
