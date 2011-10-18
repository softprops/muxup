from os import getenv
from urllib import urlencode
from urllib2 import Request, urlopen, quote, URLError, HTTPError
from datetime import datetime
from json import dumps as to_json, loads as from_json

MU_HOST            = getenv('MU_HOST', 'https://secure.meetup.com')
AUTHENTICATION_URI = '%s/oauth2/authorize' % MU_HOST
TOKEN_URI          = '%s/oauth2/access' % MU_HOST
API_HOST           = getenv('API_HOST', 'https://api.meetup.com')
CLIENT_ID          = getenv('CLIENT_ID')
CLIENT_SECRET      = getenv('CLIENT_SECRET')
VERSION            = '0.1.0'
USER_AGENT         = 'MeetupFlask/%s' % VERSION

if not CLIENT_ID or not CLIENT_SECRET: raise Exception(
    'CLIENT_ID and CLIENT_SECRET must be set as env vars'
)

def url_for_authentication(redirect_uri, response_type='code',
                           state=str(datetime.now()), scopes=[]):
    ''' return the configured uri for
        acquireing user authorization for oauth2
    '''
    uri = "%s?client_id=%s&response_type=%s&state=%s&redirect_uri=%s" % (
        AUTHENTICATION_URI,
        CLIENT_ID,
        response_type,
        quote(state),
        quote(redirect_uri))
    return scopes and "%s&scope=%s" % (uri, '+'.join(scopes)) or uri

def request_access_token(code, redirect_uri):
    ''' make a request for an access token given
        an access grant
    '''
    req = Request(TOKEN_URI,
                  data = urlencode({
                      'client_id': CLIENT_ID,
                      'client_secret': CLIENT_SECRET,
                      'grant_type': 'authorization_code',
                      'code': code,
                      'redirect_uri': redirect_uri }),
                  headers = {
                      'User-Agent' : USER_AGENT
                  })
    resp = urlopen(req).read()
    return from_json(resp)

def refresh_access_token(refresh_token):
    ''' request a new set of oauth2 credentials given
        a previously acquired refresh_token
    '''
    req = Request(TOKEN_URI,
                  data = urlencode({
                      'client_id': CLIENT_ID,
                      'client_secret': CLIENT_SECRET,
                      'grant_type': 'refresh_token',
                      'refresh_token': refresh_token,
                   }),
                   headers = {
                       'User-Agent': USER_AGENT
                   })
    resp = urlopen(req).read()
    return from_json(resp)

def client(access_token):
    ''' returns a new configured meetup api client
    '''
    return Client(API_HOST, access_token)

class MeetupNotAuthorized(Exception):
    ''' Represents an exception thrown when an api request
        is rejected due to invalid authorization
    '''
    pass

class MeetupBadRequest(Exception):
    ''' Represents an exception throw when an api request
        is rejected for being malformed
    '''
    pass

class Client():
    ''' rest client for api.meetup.com
    '''
  
    def __init__(self, host, access_token, encoding = 'ISO-8859-1'):
        self.host = host
        self.access_token = access_token
        self.encoding = encoding

    def with_access(self, params):
        return dict(params.items() + { 'access_token': self.access_token }.items())

    def client_headers(self):
        return { 'User-Agent': USER_AGENT }

    def get(self, path, params = {}):
        try:
            url = "%s%s?%s" % (self.host, path, urlencode(self.with_access(params)))
            print url
            return from_json(urlopen(Request(url, headers = self.client_headers())).read(), encoding = self.encoding)
        except HTTPError, e:
            if 401 == e.code: raise MeetupNotAuthorized(e.read())
            if 400 == e.code: raise MeetupBadRequest(e.read())
        except URLError, e:
            raise MeetupBadRequest("malformed url %s" % e.reason)
        except Exception, e:
            raise MeetupNotAuthorized('not authorized to request %s: %s' % (path, e))

    def post(self, path, params = {}):
        try:
            url = "%s%s" % (self.host, path)
            return from_json(urlopen(Request(url,
                             data = urlencode(self.with_access(params)),
                             headers = self.client_headers())).read(), encoding = self.encoding)
        except HTTPError, e:
            if 401 == e.code: raise MeetupNotAuthorized(e.read())
            if 400 == e.code: raise MeetupBadRequest(e.read())
            raise e
        except URLError, e:
            raise MeetupBadRequest("malformed url %s" % e.reason)
        except Exception, e:
            raise MeetupNotAuthorized('not authorized to request %s: %s' % (path, e))

    def current_user(self):
        ''' return the user that authorized this client
        '''
        return self.get('/2/member/self')

    def open_events(self, params):
        ''' return events that are in public in groups
            and public to rsvp to
        '''
        return self.get('/2/open_events', params)
