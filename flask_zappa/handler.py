from __future__ import unicode_literals

import base64
import os
import importlib

from zappa.wsgi import create_wsgi_request

from urllib import urlencode
from StringIO import StringIO


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

    print 'event', event

    # This is a normal HTTP request
    if event.get('method', None):
        # TODO: Enable echo command
        # # If we just want to inspect this,
        # # return this event instead of processing the request
        # # https://your_api.aws-api.com/?event_echo=true
        # event_echo = getattr(settings, "EVENT_ECHO", True)
        # if event_echo:
        #     if 'event_echo' in event['params'].values():
        #         return {'Content': str(event) + '\n' + str(context), 'Status': 200}

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
        environ = create_wsgi_request(event, script_name='app.py:app',
                                      trailing_slash=False)
        print 'environ', environ

        # This entire try-finally clause is stolen directly from
        # flask.app.py:Flask.wsgi_app(self, environ, start_response). The only
        # difference is that we don't call
        # return response(environ, start_response) after the inner try-except,
        # as we need access to the headers, and status code as well.
        ctx = app.request_context(environ)
        ctx.push()
        error = None
        try:
            try:
                response = app.full_dispatch_request()
            except Exception as e:
                error = e
                response = app.make_response(app.app.handle_exception(e))
            # response is now of type app.response_class
            # (default=werkzeug.wrappers.Response)
        finally:
            if app.should_ignore_error(error):
                error = None
            ctx.auto_pop(error)

        # Call close to ensure all registered functions which might have an
        # effect on the response is called.
        response.close()

        status_code = response.status_code

        # This will either contain the content in .next() or None if the http
        # request type requires an empty response.
        response_iter, _, headers = response.get_wsgi_response(environ)

        try:
            response_content = response_iter.next()
            returnme = {'Content': response_content}
        except StopIteration:
            response_content = None
            # Prepare the special dictionary which will be returned to the API GW.
            returnme = dict()

        # Pack the WSGI response into our special dictionary.
        for (header_name, header_value) in headers:
            returnme[header_name] = header_value
        returnme['Status'] = status_code

        # TODO: No clue how to handle the flask-equivalent of this. Or is this
        # something entirely specified by the middleware?
        # # Parse the WSGI Cookie and pack it.
        # cookie = response.cookies.output()
        # if ': ' in cookie:
        #     returnme['Set-Cookie'] = response.cookies.output().split(': ')[1]

        # To ensure correct status codes, we need to
        # pack the response as a deterministic B64 string and raise it
        # as an error to match our APIGW regex.
        # The DOCTYPE ensures that the page still renders in the browser.
        if response.status_code in [400, 401, 403, 500]:
            content = response_content
            content = "<!DOCTYPE html>" + str(status_code) + response.content
            b64_content = base64.b64encode(content)
            raise Exception(b64_content)
        # Internal are changed to become relative redirects
        # so they still work for apps on raw APIGW and on a domain.
        elif status_code in [301, 302]:
            location = returnme['Location']
            location = '/' + location.replace("http://zappa/", "")
            raise Exception(location)
        else:
            return returnme

    # # This is a management command invocation.
    # elif event.get('command', None):
    #     from django.core import management

    #     # Couldn't figure out how to get the value into stdout with StringIO..
    #     # Read the log for now. :[]
    #     management.call_command(*event['command'].split(' '))
    #     return {}
