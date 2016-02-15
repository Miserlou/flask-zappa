# flask-zappa
Serverless Flask on AWS Lambda + API Gateway

![Logo](http://i.imgur.com/vLflpND.gif)
# flask-zappa [![Build Status](https://travis-ci.org/Miserlou/flask-zappa.svg)](https://travis-ci.org/Miserlou/flask-zappa)
#### Serverless Flask with AWS Lambda + API Gateway

**flask-zappa** makes it super easy to deploy Flask applications on AWS Lambda + API Gateway. Think of it as "serverless" web hosting for your Flask apps.

That means:

* **No more** tedious web server configuration!
* **No more** paying for 24/7 server uptime!
* **No more** worrying about load balancing / scalability!
* **No more** worrying about keeping servers online!
* **No more** worrying about security vulernabilities and patches!

**flask-zappa** handles:

* Packaging projects into Lambda-ready zip files and uploading them to S3
* Correctly setting up IAM roles and permissions
* Automatically configuring API Gateway routes, methods and integration responses
* Deploying the API to various stages of readiness

__Awesome!__

This project is for Flask-specific integration. If you are intersted in how this works under the hood, you should look at the **[Zappa core library](https://github.com/Miserlou/Zappa)**, which can be used by any WSGI-compatible web framework and **[django-zappa](https://github.com/Miserlou/django-zappa)**, which works for django apps.

## Installation

    $ pip install flask-zappa

## Configuration

There are a few settings that you must define before you deploy your application. First, you must have your AWS credentials stored in _~/.aws/credentials'_.

Finally, define a ZAPPA_SETTINGS setting in your local settings file which maps your named deployment environments to deployed settings and an S3 bucket (which must already be created). These can be named anything you like, but you may wish to have seperate _dev_, _staging_ and _production_ environments in order to separate your data.

```python
ZAPPA_SETTINGS = {
    'production': {
        's3_bucket': 'production-bucket',
        'settings_file': '~/Projects/MyApp/settings/production_settings.py',
    },
    'staging': {
        's3_bucket': 'staging-bucket',
        'settings_file': '~/Projects/MyApp/settings/staging_settings.py',
    },
}
```

Notice that each environment defines a path to a settings file. This file will be used as your _server-side_ settings file. Specifically, you will want to define [a new SECRET_KEY](https://gist.github.com/Miserlou/a9cbe22d06cbabc07f21), as well as your deployment DATABASES information.

#### A Note About Databases

Since Zappa requirements are called from a bundled version of your local environment and not from pip, and because we have no way to determine what platform our Zappa handler will be executing on, we need to make sure that we only use portable packages. So, instead of using the default MySQL engine, we will instead need to use _mysql-python-connector_.

Currently, Zappa only supports MySQL and Aurora on RDS.

## Basic Usage

#### Initial Deployments

#### Updates

#### Management

## Advanced Usage

There are other settings that you can define in your ZAPPA_SETTINGS
to change Zappa's behavior. Use these at your own risk!

```python
ZAPPA_SETTINGS = {
    'dev': {
        'aws_region': 'us-east-1', # AWS Region (default US East),
        'deploy_delay': 1, # Delay time while deploying, in seconds (default 1)
        'domain': 'yourapp.yourdomain.com', # Required if you\'re using a domain
        'http_methods': ['GET', 'POST'], # HTTP Methods to route,
        'integration_response_codes': [200, 301, 404, 500], # Integration response status codes to route
        'method_response_codes': [200, 301, 404, 500], # Method response status codes to route
        'parameter_depth': 10, # Size of URL depth to route. Defaults to 5.
        'role_name': "MyLambdaRole", # Lambda execution Role
        's3_bucket': 'dev-bucket', # Zappa zip bucket,
        'settings_file': '~/Projects/MyApp/settings/dev_settings.py', # Server side settings file location,
        'touch': False # GET the production URL upon initial deployment (default True)
    }
}
```

## TODO

This project is very young, so there is still plenty to be done. Contributions are more than welcome! Please file tickets before submitting patches, and submit your patches to the 'dev' branch.

Things that need work right now:

* Everything!
* Testing!
* Feedback!
* Real documentation / website!
