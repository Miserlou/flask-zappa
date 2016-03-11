#!/usr/bin/env python
import os
import json
import importlib
import zipfile
import inspect

import requests
import click

from zappa.zappa import Zappa
import flask_zappa


CUSTOM_SETTINGS = [
        'http_methods',
        'parameter_depth',
        'integration_response_codes',
        'method_response_codes',
        'role_name',
        'aws_region'
]

DEFAULT_SETTINGS = {
        'vpc_config': {},
        'delete_zip': True,
        'touch': True,
        'memory_size': 256
}


class SettingsError(Exception): pass


def apply_zappa_settings(zappa_obj, zappa_settings, environment):
    '''Load Zappa settings, set defaults if needed, and apply to the Zappa object'''

    settings_all = json.load(zappa_settings)
    settings = settings_all[environment]

    # load defaults for missing options
    for key,value in DEFAULT_SETTINGS.items():
        settings[key] = settings.get(key, value)

    if '~' in settings['settings_file']:
        settings['settings_file'] = settings['settings_file'].replace('~', os.path.expanduser('~'))
    if not os.path.isfile(settings['settings_file']):
        raise SettingsError("Please make sure your settings_file "
                            "is properly defined in {0}.".format(zappa_settings))

    for setting in CUSTOM_SETTINGS:
        if setting in settings:
            setattr(zappa_obj, setting, settings[setting])

    return settings



def _init(environment, zappa_settings):
    """

    """
    # Make your Zappa object
    zappa = Zappa()

    # Load settings and apply them to the Zappa object
    settings = apply_zappa_settings(zappa, zappa_settings, environment)

    # Create the Lambda zip package (includes project and virtualenvironment)
    # Also define the path the handler file so it can be copied to the zip root
    # for Lambda.
    module_dir = os.path.dirname(os.path.abspath(flask_zappa.__file__))
    handler_file = os.path.join(module_dir, 'handler.py')
    lambda_name = settings['project_name'] + '-' + environment

    return zappa, settings, handler_file, lambda_name

def _package(environment, zappa_settings):
    """
    """
    zappa, settings, handler_file, lambda_name = _init(environment, zappa_settings)

    # assume zappa_settings is at the project root
    #os.chdir(os.path.dirname(zappa_settings))

    # List of patterns to exclude when zipping our package for Lambda
    exclude = settings.get('exclude', list())

    zip_path = zappa.create_lambda_zip(lambda_name,
                                       handler_file=handler_file,
                                       exclude=exclude)

    # Add this environment's settings to that zipfile
    with open(settings['settings_file'], 'r') as f:
        contents = f.read()
        all_contents = contents
        if 'domain' not in settings:
            script_name = environment
        else:
            script_name = ''

        all_contents = (all_contents +
                        '\n# Automatically added by Zappa:\nSCRIPT_NAME=\'/' +
                        script_name + '\'\n')
        f.close()

    with open('zappa_settings.py', 'w') as f:
        f.write(all_contents)

    with zipfile.ZipFile(zip_path, 'a') as lambda_zip:
        lambda_zip.write('zappa_settings.py', 'zappa_settings.py')
        lambda_zip.close()

    os.unlink('zappa_settings.py')

    return zappa, settings, lambda_name, zip_path


@click.group()
def cli():
    """ Tool for interacting with flask-lambda-apigateway."""
    pass


@cli.command()
@click.argument('environment', required=True)
@click.argument('zappa_settings', required=True, type=click.File('rb'))
def deploy(environment, zappa_settings):
    """ Package, create and deploy to Lambda."""
    print(("Deploying " + environment))

    zappa, settings, lambda_name, zip_path = \
        _package(environment, zappa_settings)

    s3_bucket_name = settings['s3_bucket']

    try:
        # Load your AWS credentials from ~/.aws/credentials
        zappa.load_credentials()

        # Make sure the necessary IAM execution roles are available
        zappa.create_iam_roles()

        # Upload it to S3
        zip_arn = zappa.upload_to_s3(zip_path, s3_bucket_name)

        # Register the Lambda function with that zip as the source
        # You'll also need to define the path to your lambda_handler code.
        lambda_arn = zappa.create_lambda_function(bucket=s3_bucket_name,
                                                  s3_key=zip_path,
                                                  function_name=lambda_name,
                                                  handler='handler.lambda_handler',
                                                  vpc_config=settings['vpc_config'],
                                                  memory_size=settings['memory_size'])

        # Create and configure the API Gateway
        api_id = zappa.create_api_gateway_routes(lambda_arn, lambda_name)

        # Deploy the API!
        endpoint_url = zappa.deploy_api_gateway(api_id, environment)

        # Remove the uploaded zip from S3, because it is now registered..
        zappa.remove_from_s3(zip_path, s3_bucket_name)

        if settings['touch']:
            requests.get(endpoint_url)
    finally:
        try:
            # Finally, delete the local copy our zip package
            if settings['delete_zip']:
                os.remove(zip_path)
        except:
            print("WARNING: Manual cleanup of the zip might be needed.")

    print(("Your Zappa deployment is live!: " + endpoint_url))


@cli.command()
@click.argument('environment', required=True)
@click.argument('zappa_settings', required=True, type=click.File('rb'))
def update(environment, zappa_settings):
    """ Update an existing deployment."""
    print(("Updating " + environment))

    # Package dependencies, and the source code into a zip
    zappa, settings, lambda_name, zip_path = \
        _package(environment, zappa_settings)

    s3_bucket_name = settings['s3_bucket']

    try:

        # Load your AWS credentials from ~/.aws/credentials
        zappa.load_credentials()

        # Update IAM roles if needed
        zappa.create_iam_roles()


        # Upload it to S3
        zip_arn = zappa.upload_to_s3(zip_path, s3_bucket_name)

        # Register the Lambda function with that zip as the source
        # You'll also need to define the path to your lambda_handler code.
        lambda_arn = zappa.update_lambda_function(s3_bucket_name, zip_path,
                                                  lambda_name)

        # Remove the uploaded zip from S3, because it is now registered..
        zappa.remove_from_s3(zip_path, s3_bucket_name)
    finally:
        try:
            # Finally, delete the local copy our zip package
            if settings['delete_zip']:
                os.remove(zip_path)
        except:
            print("WARNING: Manual cleanup of the zip might be needed.")

    print("Your updated Zappa deployment is live!")


@cli.command()
@click.argument('environment', required=True)
@click.argument('zappa_settings', required=True, type=click.File('rb'))
def tail(environment, zappa_settings):
    """ Stolen verbatim from django-zappa: 
        https://github.com/Miserlou/django-zappa/blob/master/django_zappa/management/commands/tail.py
    """

    def print_logs(logs):

        for log in logs:
            timestamp = log['timestamp']
            message = log['message']
            if "START RequestId" in message:
                continue
            if "REPORT RequestId" in message:
                continue
            if "END RequestId" in message:
                continue

            print("[" + str(timestamp) + "] " + message.strip())

    zappa, settings, _, lambda_name = _init(environment, zappa_settings)

    try:
        # Tail the available logs
        all_logs = zappa.fetch_logs(lambda_name)
        print_logs(all_logs)

        # Keep polling, and print any new logs.
        while True:
            all_logs_again = zappa.fetch_logs(lambda_name)
            new_logs = []
            for log in all_logs_again:
                if log not in all_logs:
                    new_logs.append(log)

            print_logs(new_logs)
            all_logs = all_logs + new_logs
    except KeyboardInterrupt:
        # Die gracefully
        try:
            sys.exit(0)
        except SystemExit:
            os._exit(0)

if __name__ == "__main__":
    cli()
