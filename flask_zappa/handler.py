from __future__ import unicode_literals

import base64
import os
import importlib
from urllib import urlencode
from StringIO import StringIO

from werkzeug.wrappers import Response
from zappa.wsgi import create_wsgi_request

from zappa.middleware import ZappaWSGIMiddleware


def lambda_handler(event, context, settings_name="zappa_settings"):
    """ An AWS Lambda function which parses specific API Gateway input into a
    WSGI request, feeds it to Django, procceses the Django response, and returns
    that back to the API Gateway.
    """
    # Loading settings from a python module
    settings = importlib.import_module(settings_name)

    # The flask-app module
    app_module = importlib.import_module(settings.APP_MODULE)

    # The flask-app
    app = getattr(app_module, settings.APP_OBJECT)

    app.wsgi_app = ZappaWSGIMiddleware(app.wsgi_app)

    print 'event', event

    # This is a normal HTTP request
    if event.get('method', None):
        # If we just want to inspect this,
        # return this event instead of processing the request
        # https://your_api.aws-api.com/?event_echo=true
        event_echo = getattr(settings, "EVENT_ECHO", True)
        if event_echo:
            if 'event_echo' in event['params'].values():
                return {'Content': str(event) + '\n' + str(context), 'Status': 200}

        # TODO: Enable Let's Encrypt
        # # If Let's Encrypt is defined in the settings,
        # # and the path is your.domain.com/.well-known/acme-challenge/{{lets_encrypt_challenge_content}},
        # # return a 200 of lets_encrypt_challenge_content.
        # lets_encrypt_challenge_path = getattr(settings, "LETS_ENCRYPT_CHALLENGE_PATH", None)
        # lets_encrypt_challenge_content = getattr(settings, "LETS_ENCRYPT_CHALLENGE_CONTENT", None)
        # if lets_encrypt_challenge_path:
        #     if len(event['params']) == 3:
        #         if event['params']['parameter_1'] == '.well-known' and \
        #             event['params']['parameter_2'] == 'acme-challenge' and \
        #             event['params']['parameter_3'] == lets_encrypt_challenge_path:
        #                 return {'Content': lets_encrypt_challenge_content, 'Status': 200}

        # Create the environment for WSGI and handle the request
        environ = create_wsgi_request(event, script_name=settings.SCRIPT_NAME,
                                      trailing_slash=False)
        print 'environ =', environ

        response = Response.from_app(app, environ)

        # This doesn't work. It should probably be set right after creation, not
        # at such a late stage.
        # response.autocorrect_location_header = False

        zappa_returndict = dict()

        if response.data:
            zappa_returndict['Content'] = response.data

        # Pack the WSGI response into our special dictionary.
        for (header_name, header_value) in response.headers:
            zappa_returndict[header_name] = header_value
        zappa_returndict['Status'] = response.status_code

        # TODO: No clue how to handle the flask-equivalent of this. Or is this
        # something entirely specified by the middleware?
        # # Parse the WSGI Cookie and pack it.
        # cookie = response.cookies.output()
        # if ': ' in cookie:
        #     zappa_returndict['Set-Cookie'] = response.cookies.output().split(': ')[1]

        # To ensure correct status codes, we need to
        # pack the response as a deterministic B64 string and raise it
        # as an error to match our APIGW regex.
        # The DOCTYPE ensures that the page still renders in the browser.
        if response.status_code in [400, 401, 403, 404, 500]:
            content = "<!DOCTYPE html>" + str(response.status_code) + response.data
            b64_content = base64.b64encode(content)
            raise Exception(b64_content)
        # Internal are changed to become relative redirects
        # so they still work for apps on raw APIGW and on a domain.
        elif response.status_code in [301, 302]:
            # Location is by default relative on Flask. Location is by default
            # absolute on Werkzeug. We can set autocorrect_location_header on
            # the response to False, but it doesn't work. We have to manually
            # remove the host part.
            location = response.location.split(environ[u'HTTP_HOST'])[1]
            raise Exception(location)
        else:
            return zappa_returndict

    # # This is a management command invocation.
    # elif event.get('command', None):
    #     from django.core import management

    #     # Couldn't figure out how to get the value into stdout with StringIO..
    #     # Read the log for now. :[]
    #     management.call_command(*event['command'].split(' '))
    #     return {}
