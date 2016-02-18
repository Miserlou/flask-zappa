import os
import json
import importlib
import zipfile
import inspect

import requests
import click

from zappa.zappa import Zappa


def _package(environment, zappa_settings):
    # Loading settings from json
    settings = json.load(zappa_settings)

    print settings

    project_name = settings[environment]['project_name']

    # Make your Zappa object
    zappa = Zappa()

    # Load environment-specific settings
    s3_bucket_name = settings[environment]['s3_bucket']
    vpc_config = settings[environment].get('vpc_config', {})
    settings_file = settings[environment]['settings_file']
    if '~' in settings_file:
        settings_file = settings_file.replace('~', os.path.expanduser('~'))
    if not os.path.isfile(settings_file):
        print("Please make sure your settings_file is properly defined.")
        return

    custom_settings = [
        'http_methods',
        'parameter_depth',
        'integration_response_codes',
        'method_response_codes',
        'role_name',
        'aws_region'
    ]
    for setting in custom_settings:
        if setting in settings[environment]:
            setattr(zappa, setting, settings[environment][setting])

    # Load your AWS credentials from ~/.aws/credentials
    zappa.load_credentials()

    # Make sure the necessary IAM execution roles are available
    zappa.create_iam_roles()

    # Create the Lambda zip package (includes project and virtualenvironment)
    # Also define the path the handler file so it can be copied to the zip root
    # for Lambda.
    current_file = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
    print 'current_file', current_file
    handler_file = current_file + os.sep + 'flask_zappa' + os.sep + 'handler.py'
    lambda_name = project_name + '-' + environment
    zip_path = zappa.create_lambda_zip(lambda_name, handler_file=handler_file)

    # Add this environment's Django settings to that zipfile
    with open(settings_file, 'r') as f:
        contents = f.read()
        all_contents = contents
        if 'domain' not in settings[environment]:
            script_name = environment
        else:
            script_name = ''

        if "ZappaMiddleware" not in all_contents:
            print("\n\nWARNING!\n")
            print("You do not have ZappaMiddleware in your remote settings's MIDDLEWARE_CLASSES.\n")
            print("This means that some aspects of your application may not work!\n\n")

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
    print zip_path

    return zappa, settings, s3_bucket_name, lambda_name, zip_path


@click.group()
def cli():
    """ Tool for interacting with flask-lambda-apigateway."""
    pass


@cli.command()
@click.argument('environment', required=True)
@click.argument('zappa_settings', required=True, type=click.File('rb'))
def deploy(environment, zappa_settings):
    """ Package, create and deploy to Lambda."""
    print "deploying to %s" % environment

    zip_path = None

    try:
        zappa, settings, s3_bucket_name, lambda_name, zip_path = \
            _package(environment, zappa_settings)

        # Upload it to S3
        zip_arn = zappa.upload_to_s3(zip_path, s3_bucket_name)

        # Register the Lambda function with that zip as the source
        # You'll also need to define the path to your lambda_handler code.
        lambda_arn = zappa.create_lambda_function(s3_bucket_name, zip_path,
                                                  lambda_name,
                                                  'handler.lambda_handler')

        # Create and configure the API Gateway
        delay = settings[environment].get('deploy_delay', 1)
        api_id = zappa.create_api_gateway_routes(lambda_arn, lambda_name, delay)

        # Deploy the API!
        endpoint_url = zappa.deploy_api_gateway(api_id, environment)

        # Remove the uploaded zip from S3, because it is now registered..
        zappa.remove_from_s3(zip_path, s3_bucket_name)

        if settings[environment].get('touch', True):
            requests.get(endpoint_url)
    finally:
        # Finally, delete the local copy our zip package
        if settings[environment].get('delete_zip', True):
            os.remove(zip_path)

    print("Your Zappa deployment is live!: " + endpoint_url)


@cli.command()
@click.argument('environment', required=True)
@click.argument('zappa_settings', required=True, type=click.File('rb'))
def update(environment, zappa_settings):
    """ Update an existing deployment."""
    print "update"

    print "deploying to %s" % environment

    zip_path = None

    try:
        # Package dependencies, and the source code into a zip
        zappa, settings, s3_bucket_name, lambda_name, zip_path = \
            _package(environment, zappa_settings)

        # Upload it to S3
        zip_arn = zappa.upload_to_s3(zip_path, s3_bucket_name)

        # Register the Lambda function with that zip as the source
        # You'll also need to define the path to your lambda_handler code.
        lambda_arn = zappa.update_lambda_function(s3_bucket_name, zip_path,
                                                  lambda_name)

        # Remove the uploaded zip from S3, because it is now registered..
        zappa.remove_from_s3(zip_path, s3_bucket_name)
    finally:
        # Finally, delete the local copy our zip package
        if zip_path and settings[environment].get('delete_zip', True):
            os.remove(zip_path)

    print("Your updated Zappa deployment is live!")


if __name__ == "__main__":
    cli()
