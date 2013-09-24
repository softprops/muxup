# Muxup

A Meetup API flask example

## install

This app depends on [Flask][flask] and [requests][requests]

   easy_install pip
   pip install -r requirements.txt

Before starting the application be sure to export the following environment variables

    export CLIENT_ID=YOUR_REGISTERED_MEETUP_OAUTH_CONSUMER_KEY
    export CLIENT_SECRET=YOUR_REGISTED_MEETUP_OAUTH_CLIENT_SECRET
    export COOKIE_SECRET=RANDOM_STRING_OF_CHARS_USED_TO_SIGN_COOKIES


[flask]: http://flask.pocoo.org/
[requests]: http://docs.python-requests.org/en/latest/
