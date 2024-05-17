# Webmunk Enrollment Django App

This repository contains the enrollment app intended to be installed into a larger Django project for the purposes of administering Webmunk projects. Unlike the [*data collection server*](https://github.com/Webmunk-Project/Webmunk-Django), this **does not** store data gathered by the browser extension in the field, **but** it does configure the extension and assign anonymized study identfiers to participants.


## Prerequisites

The Webmunk Enrollment App has been developed primarily on Unix-like platforms and generally assumes the existence of tools such as CRON and Apache.

Administrators seeking to install this app should be comfortable with [the Django web application framework](https://www.djangoproject.com/). This app uses Django-specific features extensively and intentionally, and not just as a database front-end.

This app targets LTS releases of Django (3.2.X, 4.2.X). It requires Python 3.6 and newer.

In addition to Django, the enrollment app relies extensively on the Postgres database support included with Django, including the PostGIS extensions needed to enable spatial data types within Postgres. PDK supports Postgres 9.5 and newer.

To make your server accessible to outside web browser extension clients, we typically configure Django with the Apache 2 webserver, using [mod_wsgi](https://modwsgi.readthedocs.io/) to facilitate communication between the front-end Apache web server and the Python application server. Typically, the bundled Apache server and mod_wsgi module that comes with your Unix distribution is more than sufficient to support Django.

This server assumes that local users are able to set up and run CRON jobs. This server uses CRON to kick-off [the Quicksilver job scheduler](https://github.com/audacious-software/Quicksilver-Django), which runs background tasks for the server.


## Installation

If you are operating in an environment that fulfills all of the requirements above, the first step to get started is to install the Django web application framework with Postgres and PostGIS enabled:

1. **(Strongly Recommended)** Before installing Django, [create a Python virtual environment](https://docs.python.org/3/library/venv.html) that will contain Django and all of the relevant dependencies separate from your host platform's own Python installation. Don't forget to activate your virtual environment before continuing!

2. Follow the instructions provided by the Django project to [install Django and its dependencies](https://docs.djangoproject.com/en/3.2/topics/install/). Remember to specify a Django LTS version, and not necessarily install the newest by default: `pip install Django==3.2.24`, **not** `pip install Django`.

3. After the base Django platform has been installed, enable GeoDjango and PostGIS by [following the instructions provided](https://docs.djangoproject.com/en/3.2/ref/contrib/gis/install/). Note that one some platforms (Red Hat Enterprise Linux, for one), the PostGIS packages may not be readily available. In that case, refer to [the PostGIS documentation for guidance](https://postgis.net/documentation/getting_started/) for your particular environment.

4. Once Django is fully installed, create a new Django project: `django-admin startproject myproject`. [Refer to the Django tutorial](https://docs.djangoproject.com/en/3.2/intro/tutorial01/) to understand how everything fits together.

5. Within your project, add the Quicksilver job scheduler by checking it out from Git: `git clone https://github.com/audacious-software/Quicksilver-Django.git quicksilver` (if you are not using Git to track changes yet) or `git submodule add hhttps://github.com/audacious-software/Quicksilver-Django.git quicksilver` (if you would like Quicksilver added as a submodule dependency).

6. Within your project, add the [Simple Backup app](https://github.com/audacious-software/Simple-Backup-Django/) by checking it out from Git: `git clone https://github.com/audacious-software/Simple-Backup-Django.git simple_backup` (if you are not using Git to track changes yet) or `git submodule add https://github.com/audacious-software/Simple-Backup-Django.git simple_backup` (if you would like Simple Backup added as a submodule dependency).

7. Within your project, add the [Simple Data Export app](https://github.com/audacious-software/Simple-Data-Export-Django) by checking it out from Git: `git clone https://github.com/audacious-software/Simple-Data-Export-Django.git simple_data_export` (if you are not using Git to track changes yet) or `git submodule add https://github.com/audacious-software/Simple-Data-Export-Django.git simple_data_export` (if you would like Simple Backup added as a submodule dependency).

8. Copy the `documentation/requirements.txt` file to the root of the project: 

    ```
    cp enrollment/documentation/requirements.txt requirements.txt
    ``` 

    Install the dependencies:

    ```
    pip install -U pip
    pip install wheel
    pip install -r requirements.txt
    ```

    Installing the `wheel` package first allows `pip` to install precompiled Python packages. This can be a significant time saver and may help you avoid the need to install a ton of extra platform dependencies to compile the Python packages.

   In the event that you encounter some version mismatches between app dependencies, this can be resolved by updating the conflicting dependencies with the latest versions available for your Python environment and updating `requirements.txt` files accordingly. Note that the all of these apps use [GitHub's Dependabot service](https://docs.github.com/en/code-security/dependabot) to try and keep all their dependencies as up-to-date as possible, usually on a weekly update schedule.

9. Once the relevant Python dependencies have been installed, enable the enrollment server by adding the following to the `INSTALLED_APPS` option in your settings:

    ```
    INSTALLED_APPS = [
        ...
        'quicksilver',
        'simple_backup',
        'simple_data_export',
        'enrollment',
        ...
    ]

    Also add update the project's main `urls.py` file:

    ```
    urlpatterns = [
        path('admin/', admin.site.urls),
        url(r'^quicksilver/', include('quicksilver.urls')),
        url(r'^export/', include('simple_data_export.urls')),
        url(r'^enroll/', include('enrollment.urls')),
    ]
    ```

    The `documentation` folder in this repository contain examples for `settings.py` and `urls.py` for your reference, including various customization and configuration points that you will need to adapt for your own studies.
    
10. Once the server has been enabled, initialize the database tables by making the local `manage.py` file executable, and running `./manage.py migrate`. You should see Django run through all the Django migrations and create the relevant tables.

11. After the database tables have been created, [configure your local Apache HTTP server](https://docs.djangoproject.com/en/3.2/howto/deployment/wsgi/modwsgi/) to connect to Django.

    We **strongly recommend** that your configure Django to be served over HTTPS ([obtain a Let's Encrypt certificate if needed](https://letsencrypt.org/)) and to forward any unencrypted HTTP requests to the HTTPS port using a `VirtualHost` definition like:

    ````
    <VirtualHost *:80>
        ServerName myserver.example.com

        RewriteEngine on
        RewriteRule    ^(.*)$    https://myserver.example.com$1    [R=301,L]
    </VirtualHost>
    ````

12. Once Apache is configured and running, create a Django superuser account (if you have not already): `./manage.py createsuperuser`. The command will prompt you for a username, password, and e-mail address. Once you have provided those, install the static file resources `./manage.py collectstatic`. Finally, log into the Django administrative backend: `https://myserver.example.com/admin/` (replacing `myserver.example.com` with your own host's name. You should see the standard Django tables.
    
Congratulations, you have (almost) successfully installed the Webmunk Enrollment Server.


## Background Jobs Setup

Before your site is ready for use by clients, we have one more **very** important step to complete: setting up the background CRON jobs. We've broken this out into its own section in order to explain precisely what each job does, so you know what's happening when you and your users are not looking.

To start setting up your CRON jobs, log into the server using a local account that has enough permissions to run the Django management commands without any `root` permissions or access.

Launch the interactive CRON editor by running `crontab -e`.

Before you start defining job schedules, set up the shell to be used and the e-mail address to be notified if a job fails for some reason (also be sure that your server has been configured to send e-mails from the command line):

```
MAILTO=me@example.com
SHELL=/bin/bash
```

In this case, should any of the following jobs fail, `me@example.com` will receive the output generated by the failed job for troubleshooting purposes.

The following lines will take the following format:

```
<SCHEDULE_DEFINITION>    source <PATH_TO_VIRTUAL_ENVIRONMENT>/bin/activate && python <PATH_TO_PROJECT>/manage.py <DJANGO_COMMAND>
```

The `<SCHEDULE_DEFINITION>` is defined by [the CRON scheduling format](https://en.wikipedia.org/wiki/Cron). The next component beginning with `source` is responsible for setting up your virtual environment (from Step #1 above), so that the remainder of the line (`&&` onwards) executes the Django management commands using the dependencies you installed. You'll need to substitute in the actual values for `<PATH_TO_VIRTUAL_ENVIRONMENT>` and `<PATH_TO_PROJECT>` based on where these files reside on the local filesystem(s).

For the remainder of this section, we'll use `/var/www/venv` for `<PATH_TO_VIRTUAL_ENVIRONMENT>` and `/var/www/myproject` for `<PATH_TO_PROJECT>`.

To simplify the setup of background jobs, please use the provided [example.crontab](documentation/example.crontab) file as a reference.

A description of the jobs in `example.crontab`...

### run_task_queue

`* * * * *    source /var/www/venv/bin/activate && python /var/www/myproject/manage.py run_task_queue`

This is the main job runner of the Quicksilver task scheduler. This executes tasks sequentially in a round-robin fashion as each task becomes due. Jobs that may take longer than desired are split out into their own execution queues by specifying the `--task-queue` option to start a dedicated named queue to run within its own process.

To install all the relevant Quicksilver tasks that come bundled with the enrollment server and the various dependencies, simply run the `install_quicksilver_tasks` Django management command, which will communicate with each installed package to determine which jobs to schedule for each.


### incremental_backup

`0 3 * * *    source /var/www/venv/bin/activate && python /var/www/myproject/manage.py incremental_backup`

Run once a day to create and upload an incremental backup to a destination such as Amazon S3 with updates made in during the past calendar day. See [Simple Backup](https://github.com/audacious-software/Simple-Backup-Django) for more details. 

### push_group_memberships

`*/15 * * * *    source /var/www/venv/bin/activate && python /var/www/myproject/manage.py push_group_memberships`

Small utility job that would communicate with Webmunk data collection servers (using the Passive Data Kit API) to synchronize participant group memberships across servers.

### webmunk_create_nightly_export_job

0 7 * * *    source /var/www/myproject/venv/bin/activate && python /var/www/myproject/webmunk_enrollment/manage.py webmunk_create_nightly_export_job

Created a nightly export jobs that generates enrollment-related reports to be uploaded to cloud storage for use in participant tracking, monitoring, and compensation. Provides custom-webmunk-specific reports that [Simple Data Export](https://github.com/audacious-software/Simple-Data-Export-Django) compiles and uploads to the cloud.

## License and Other Project Information

Copyright 2022-2024 The Fradkin Foundation and the President & Fellows of Harvard College

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
