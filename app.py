from flask import (Flask, flash, session, redirect, url_for,
                   escape, render_template, request)
from datetime import datetime
from os import getenv
from anyjson import dumps as to_json, loads as from_json
from meetup import (client, url_for_authentication, request_access_token,
                    refresh_access_token, MeetupNotAuthorized, MeetupBadRequest)
from urllib2 import HTTPError

app = Flask(__name__)

@app.route('/')
def index():
    ''' let's make this as simple as possbile.
        are you or are you not oauthenticated?
    '''
    if connected():
        return render_template('connected.html',
                               current_user = mu().current_user())
    else:
        return render_template('index.html')

@app.route('/topics/<topic>')
def events(topic):
    if connected():
        try:
            current_user = mu().current_user()
            events = mu().open_events({ 'topic': topic, 'page': 10,
                                    'lat': current_user['lat'],
                                    'lon': current_user['lon'] })
            return render_template('events.html', topic = topic,
                               events = events['results'],
                               current_user = current_user)
        except MeetupNotAuthorized:
            try:
                session['credentials'] = refresh_access_token(session['credentials']['refresh_token'])
                events(topic)
            except HTTPError:
                empty_credentials()
                flash('User revoked access')
                return redirect(url_for('index'))
    else:
        return redirect(url_for('index'))

@app.route('/signout')
def signout():
    ''' let's go back to where we started
    '''
    empty_credentials()
    flash('Signed out')
    return redirect(url_for('index'))

@app.route('/connect')
def connect():
    ''' let's connect with meetup.com
    '''
    return redirect(url_for_authentication(url_for('auth', _external = True)))

@app.route('/auth')
def auth():
    ''' meetup.com will redirect the user here after
        they were prompted for authentication.
        if the user authorized this application, we
        should request an access token
    '''
    if request.args.get('error'):
        return redirect(url_for('denied'))
    else:
        code, state = map(lambda k: request.args.get(k), ['code', 'state'])
        session['credentials'] = request_access_token(
            code, url_for('auth', _external = True))
        flash('Get muxin.')
        return redirect(url_for('index'))

@app.route('/denied')
def denied():
    return render_template('denied.html')

@app.errorhandler(404)
def not_found(error):
    return render_template('not_found.html')

@app.errorhandler(500)
def server_error(error):
    return render_template('app_error.html',
                           error = 'Server error %s' % error)

@app.errorhandler(MeetupNotAuthorized)
def meetup_not_authorized(error):
    try:
        fresh = refresh_access_token(session['credentials']['refresh_token'])
        session['credentials'] = fresh
        return render_template('app_error.html', error = 'had to freshin up')
    except Exception, e:
        empty_credentials()
        flash('User revoked access')
        return redirect(url_for('index'))

@app.errorhandler(MeetupBadRequest)
def meetup_bad_request(error):
    return render_template('app_error.html', error = error)

@app.template_filter('millidate')
def millidate_filter(t):
   return datetime.fromtimestamp(t/1000).strftime('%a %b %d @ %I:%M%p')

app.secret_key = getenv(
    'COOKIE_SECRET',
    '\xd1\x9fQ=\xd7:\x89|\xce\x02\x93\xb5O\x1a\x8e\xf1\xccy\x92tu\\PF')

# helpers

def empty_credentials():
    session.pop('credentials', None)

def connected():
  ''' return True if the current user is connected
      to meetup, otherwise return False
  '''
  return 'credentials' in session


def mu():
    ''' shorthand for getting a configured meetup client
    '''
    return client(session['credentials']['access_token'])

if __name__ == '__main__':
    app.run()
