![Logo](http://i.imgur.com/vLflpND.gif)
# flask-zappa [![Build Status](https://travis-ci.org/Miserlou/flask-zappa.svg)](https://travis-ci.org/Miserlou/flask-zappa) [![Slack](https://img.shields.io/badge/chat-slack-ff69b4.svg)](https://slackautoinviter.herokuapp.com/)
#### Serverless Flask with AWS Lambda + API Gateway

**flask-zappa** makes it super easy to deploy Flask applications on AWS Lambda + API Gateway. Think of it as "serverless" web hosting for your Flask apps.

## Flask-Zappa is still under development! Look at the non-master branches to follow the progress! 

Serverless Flask means:

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

This branch is under development so the installation is a little quirky. Once it stabilizes this will improve:

    $ pip install git+https://github.com/Miserlou/Zappa
    $ pip install git+https://github.com/Miserlou/flask-zappa

## Configuration

There are a few settings that you must define before you deploy your application. First, you must have your AWS credentials stored in _~/.aws/credentials'_.

Finally, define a json file (e.g. `zappa_settings.json`) which maps your named deployment environments to deployed settings and an S3 bucket (which must already be created). These can be named anything you like, but you may wish to have seperate _dev_, _staging_ and _production_ environments in order to separate your data.

```javascript
{
    "development": {
       "s3_bucket": "my-flask-test-bucket",
       "settings_file": "production_settings.py",
       "project_name": "MyFlaskTestProject",
       "exclude": ["*.git*", "./static/*", "*.DS_Store", "tests/*", "*.zip"]
    },
    "staging": {
       "s3_bucket": "staging-bucket",
       "settings_file": "staging_settings.py",
       "project_name": "MyFlaskTestProject",
       "exclude": ["*.git*", "./static/*", "*.DS_Store", "tests/*", "*.zip"]
    }
}
```

Notice that each environment defines a path to a settings file. This file will be used as your _server-side_ settings file. This is a temporary bad hack which will change to in the near^TM future.

Currently the settings file requires two settings:

```python
APP_MODULE="test_app"
APP_OBJECT="app"
```

where the `APP_MODULE` defines the path of the module your flask-`app` object is defined in, and `APP_OBJECT` defines the name of the app-object.

## Basic Usage

Requirements:
* Stand in your project root.
* A virtualenv must be active. All packages which your flask-app requires must be installed, along with zappa and flask-zappa.

#### Initial Deployments

To deploy the code to AWS Lambda, and  AWS API-gateway issue:

    flask-zappa deploy <environment> zappa_settings.json

where _<environment>_ is an entry (e.g. _production_) in your settings file as described above.

#### Updates

After the initial deployment, the code can be updated with:

    flask-zappa update <environment> zappa_settings.json

#### Detailed Setting Up an Example app

This will be improve A LOT!

Make sure your credentials are located in `~/.aws/credentials` and you have set a default region in `~/.aws/config`.

    $ mkdir mytestapp
    $ cd mytestapp
    $ virtualenv venv
    $ source venv/bin/activate
    $ pip install git+https://github.com/Miserlou/Zappa
    $ pip install git+https://github.com/Miserlou/flask-zappa
    $ curl https://gist.githubusercontent.com/Doerge/0714d7dbd1c4fdf1484c/raw/0ebaa6ba57c240393ff11abfb1703eeabd522c1b/test_app.py -o test_app.py
    $ curl https://gist.githubusercontent.com/Doerge/3f65ffd74a7b17b49bed/raw/956031dd0f946dd25b86e207bb3d73fac29043a2/development_settings.py -o development_settings.py
    $ curl https://gist.githubusercontent.com/Doerge/194a01e61194d8021caa/raw/6bfd8908d09fa62a81674051648c52645e392ee8/test_settings.json -o test_settings.json

Edit `'bucket': '...'` in `test_settings.json`.

    $ flask-zappa deploy production test_settings.json

Visit the url printed in the terminal. You should see Hello, world! served from `test_app.py`. There are other endpoints defined in `test_app.py` which demonstrates that various standard HTTP methods and flask features work.

#### A Note About Databases

From django-zappa. Completely untested on flask-zappa:

Since Zappa requirements are called from a bundled version of your local environment and not from pip, and because we have no way to determine what platform our Zappa handler will be executing on, we need to make sure that we only use portable packages. So, instead of using the default MySQL engine, we will instead need to use _mysql-python-connector_.

Currently, Zappa only supports MySQL and Aurora on RDS.


## Advanced Usage

UNTESTED with flask-zappa.

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

## Known Issues

* Cookies work, but the client have no concept of expiration of them.

## TODO

This project is very young, so there is still plenty to be done. Contributions are more than welcome! Please file tickets before submitting patches, and submit your patches to the 'dev' branch.

Things that need work right now:

* Everything!
* Testing!
* Feedback!
* Real documentation / website!
