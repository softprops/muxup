from os import getenv
from urllib2 import quote, URLError, HTTPError
from datetime import datetime
import requests

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

def url_for_authentication(
    redirect_uri,
    response_type='code',
    state=str(datetime.now()),
    scopes=[]):
    ''' return the configured uri for
        acquiring user authorization for oauth2
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
    resp = requests.post(TOKEN_URI,
                         data = { 'client_id': CLIENT_ID,
                                  'client_secret': CLIENT_SECRET,
                                  'grant_type': 'authorization_code',
                                  'code': code,
                                  'redirect_uri': redirect_uri },
                         headers = { 'User-Agent' : USER_AGENT }).json()
    return resp

def refresh_access_token(refresh_token):
    ''' request a new set of oauth2 credentials given
        a previously acquired refresh_token
    '''
    resp = requests.post(TOKEN_URI,
                         data = { 'client_id': CLIENT_ID,
                                  'client_secret': CLIENT_SECRET,
                                  'grant_type': 'refresh_token',
                                  'refresh_token': refresh_token },
                         headers = { 'User-Agent': USER_AGENT })
    if 400 == resp.status_code:
        raise MeetupNotAuthorized(resp.json())
    return resp.json()

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

    def __init__(self, host, access_token):
        self.host = host
        self.access_token = access_token

    def url(self, path):
        return "%s%s" % (self.host, path)

    def client_headers(self):
        return { 'User-Agent': USER_AGENT, 'Authorization': 'Bearer %s' % self.access_token }

    def get(self, path, params = {}):
        try:
            resp = requests.get(self.url(path), params = params, headers = self.client_headers())
            if 401 == resp.status_code:
                raise MeetupNotAuthorized(resp.json())
            if 400 == resp.status_code:
                raise MeetupBadRequest(resp.json())
            return resp.json()
        except HTTPError, e:
            if 401 == e.code: raise MeetupNotAuthorized(e.read())
            if 400 == e.code: raise MeetupBadRequest(e.read())
        except URLError, e:
            raise MeetupBadRequest("malformed url %s" % e.reason)
        except Exception, e:
            raise MeetupNotAuthorized('not authorized to request %s: %s' % (path, e))

    def post(self, path, params = {}):
        try:
            resp = requests.post(self.url(path), data = params, headers = self.client_headers())
            if 401 == resp.status_code:
                raise MeetupNotAuthorized(resp.json())
            if 400 == resp.status_code:
                raise MeetupBadRequest(resp.json())
            return resp.json()
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
