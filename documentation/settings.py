import base64
import datetime
import json
import random

from pathlib import Path

import arrow
import requests

from nacl.secret import SecretBox
from requests import Request

from django.utils import timezone

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/3.2/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'CHANGEME'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = False

# SETUP: Customize the line below with your publically-reachable URL hostname 
# that you will be using. Remember that this is for the enrollment server, NOT 
# the data export server!
ALLOWED_HOSTS = ['enrollment.example.com']

# SETUP: Configure with the name and e-mail address of the party who will be 
# receiving any server error e-mails.
ADMINS = [
    ('Admin User', 'admin@example.com')
]

# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'quicksilver',
    'simple_backup',
    'simple_data_export',
    'enrollment',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'webmunk_enrollment.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'webmunk_enrollment.wsgi.application'

# SETUP: Configure with the Postgres/PostGIS database created for this 
# project and the user credentials that will access the server.
DATABASES = {
    'default': {
        'ENGINE': 'django.contrib.gis.db.backends.postgis',
        'NAME':     'enroll_db',
        'USER':     'enroll_user',
        'PASSWORD': 'CHANGEME',
        'HOST': '127.0.0.1',
    }
}

# Password validation
# https://docs.djangoproject.com/en/3.2/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

LOGGING = {
   'version': 1,
   'disable_existing_loggers': False,
    'handlers': {
        'null': {
        'level': 'DEBUG',
        'class': 'logging.NullHandler',
        },
    },
   'loggers': {
       'django.security.DisallowedHost': {
           'handlers': ['null'],
           'propagate': False,
       },
   }
}

# Internationalization
# https://docs.djangoproject.com/en/3.2/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'America/New_York'

USE_I18N = True

USE_L10N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/3.2/howto/static-files/

STATIC_URL = '/static/'
STATIC_ROOT = Path.joinpath(BASE_DIR , 'static')

MEDIA_URL = '/media/'
MEDIA_ROOT = Path.joinpath(BASE_DIR , 'media')

SITE_URL = 'https://%s' % ALLOWED_HOSTS[0]

# SETUP: Configure with a Keepa API key to enable Keepa lookups.
KEEPA_API_KEY = 'CHANGEME'
KEEPA_API_SLEEP_SECONDS = 1

# SETUP: Generate by running the `generate_enrollment_key` Django management command.
ENROLLMENT_SECRET_KEY = 'CHANGEME'

SIMPLE_DATA_EXPORTER_SITE_NAME = 'Webmunk Enrollment'
SIMPLE_DATA_EXPORTER_OBFUSCATE_IDENTIFIERS = False
SIMPLE_DATA_EXPORT_DATA_SOURCES_PER_REPORT_JOB = 999999

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# SETUP: Set the from address for reminder e-mails.
AUTOMATED_EMAIL_FROM_ADDRESS = 'mystudy@example.com'


QUICKSILVER_MAX_TASK_RUNTIME_SECONDS = 60 * 60 * 4

# SETUP: Generate by `generate_backup_key` Django management command. Used to encrypt
# nightly incremental backups 
SIMPLE_BACKUP_KEY = 'L3HBfe1fBO/TOkm/S5gnIgGjSPdy8Z3PA7vhq+VIDgs='

# SETUP: Configure the fields below with the appropriate credentials and destination
# for nightly incremental backups.
SIMPLE_BACKUP_AWS_REGION = 'us-east-1'
SIMPLE_BACKUP_AWS_ACCESS_KEY_ID = 'CHANGEME'
SIMPLE_BACKUP_AWS_SECRET_ACCESS_KEY = 'CHANGEME'
SIMPLE_BACKUP_DESTINATIONS = (
    's3://my-enrollment-backup',
)

# SETUP: If synchronizing data collection status with the remote data collection 
# servers, enter the API token you generated on the data collection server here.
PDK_API_TOKEN = 'CHANGEME'

# SETUP: Enter the PDK URLs of the servers to be queried for status:
PDK_API_URLS = (
    'https://server-1.example.com/data/',
    'https://server-2.example.com/data/',
)

# SETUP: To query your own server for Keepa API data before using the KEEPA API,
# Enter the URLs of the data collection servers also gathering Keepa data.
FAUX_KEEPA_API_URLS = (
#    PDK_API_URL,
    'https://server-1.example.com/support/asin/',
    'https://server-2.example.com/support/asin/',
)

### Study-Specific Setup ###
#
# The fields below are used to customize your own Webmunk study.

WEBMUNK_DATA_FOLLOWUP_DAYS = 28
WEBMUNK_REMINDER_DAYS_INTERVAL = 1

# WEBMUNK_UPDATE_TASKS is called with a user's enrollment record each time the 
# browser extension requests an updated configuration or tasks. This function is
# INTENDED to be overridden to implement any custom scheduling or task-creation logic
# your study may require.
#
# The example below implements an multi-wave study, where participants enrolled before
# June 1, 2023 are flagged as not eligible for the next wave and their tasks are marked
# completed so that they will exit the study.
# 
# Participants who are marked eligible for partipation are assigned an initial survey to
# complete, as well as a task within the extension to upload their Amazon order history
# to the data collection server. Another data upload task is scheduled 7 weeks after 
# enrollment, and upon successful completion of that milestone, a final survey with 
# uninstall instructions is provide.
#
# If more than 80 days have elapsed since enrollment, the participant is prompted to
# uninstall the extension, regardless whether they completed any of the remaining
# milestones.
#
# WARNING - This implementation is provided AS AN EXAMPLE, and should only be used to
# illustrate the types of scheduling that can be done within this function. You are
# STRONGLY ENCOURAGED to write and test your own version that implements your own 
# study protocol instead of using this one verbatim.

def WEBMUNK_UPDATE_TASKS(enrollment, ScheduledTask): # Main study
    cutoff = datetime.date(2023, 6, 1)

    if enrollment.enrolled.date() < cutoff:

        incomplete = enrollment.tasks.filter(completed=None).exclude(slug='not-eligible')

        for task in incomplete:
            task.completed = task.active
            task.save()

        not_eligible = enrollment.tasks.filter(slug='not-eligible')

        if not_eligible.count() == 0:
            print('%s: Marking ineligible' % enrollment)

            task = 'Your email address does not match our records. If you think this is an error please reach out to the email address provided. Otherwise, click here to uninstall the extension.'

            final_url = 'https://enrollment.example.com/?webmunk_id=%s' % enrollment.assigned_identifier # This URL directs participants to uninstall instructions.

            ScheduledTask.objects.create(enrollment=enrollment, active=enrollment.enrolled, task=task, slug='not-eligible', url=final_url)
    else:
        metadata = enrollment.fetch_metadata()

        is_eligible = metadata.get('is_eligible', False)

        now = timezone.now()

        if is_eligible:
            enrollment.tasks.filter(slug='not-eligible').update(completed=now)

            if enrollment.tasks.filter(slug='amazon-fetch-initial').count() == 0:
                final_url = 'https://extension.webmunk.org/amazon-fetch'

                ScheduledTask.objects.create(enrollment=enrollment, active=now, task='Share Amazon order history', slug='amazon-fetch-initial', url=final_url)

                survey_url = 'https://survey.example.com/?webmunk_id=%s' % enrollment.assigned_identifier

                when = now - datetime.timedelta(seconds=300)

                ScheduledTask.objects.create(enrollment=enrollment, active=when, task='Complete Initial Survey', slug='main-survey-initial', url=survey_url)

                next_share = now + datetime.timedelta(days=55) # 8 weeks

                final_url = 'https://extension.webmunk.org/amazon-fetch'

                ScheduledTask.objects.create(enrollment=enrollment, active=next_share, task='Update Amazon order history', slug='amazon-fetch-final', url=final_url)

            while enrollment.tasks.filter(slug='amazon-fetch', completed=None, active__lte=now).count() > 1:
                open_task = enrollment.tasks.filter(slug='amazon-fetch', completed=None, active__lte=now).order_by('active').first()

                open_task.completed = now

                metadata = open_task.fetch_metadata()

                metadata['completion_reason'] = 'Closed due to newer duplicate becoming active'

                open_task.metadata = json.dumps(metadata, indent=2)
                open_task.save()

            if enrollment.tasks.filter(slug='main-survey-final').count() == 0 and enrollment.tasks.filter(slug='amazon-fetch-final').exclude(completed=None).count() > 0:
                survey_url = 'https://survey.example.com/?webmunk_id=%s' % enrollment.assigned_identifier

                ScheduledTask.objects.create(enrollment=enrollment, active=(now + datetime.timedelta(days=3)), task='Complete Final Survey', slug='main-survey-final', url=survey_url)

            if enrollment.tasks.filter(slug='uninstall-extension').count() == 0 and ((now - enrollment.enrolled).days >= 80 or (enrollment.tasks.filter(slug='main-survey-final').exclude(completed=None).count() > 0 and enrollment.tasks.filter(slug='amazon-fetch-final').exclude(completed=None).count() > 0)):
                survey_url = 'https://survey.example.com/?webmunk_id=%s' % enrollment.assigned_identifier

                ScheduledTask.objects.create(enrollment=enrollment, active=now, task='Uninstall Study Browser Extension', slug='uninstall-extension', url=survey_url)

        while enrollment.tasks.filter(slug__istartswith='upload-amazon-', completed=None, active__lte=now).count() > 1:
            open_task = enrollment.tasks.filter(slug__istartswith='upload-amazon-', completed=None, active__lte=now).order_by('active').first()

            open_task.completed = now

            metadata = open_task.fetch_metadata()

            metadata['completion_reason'] = 'Closed due to newer duplicate becoming active'

            open_task.metadata = json.dumps(metadata, indent=2)
            open_task.save()

        if enrollment.tasks.all().count() == 0: # New participant, not yet verified - Give 15 minutes before declaring ineligible
            if (now - enrollment.enrolled).total_seconds() > (60 * 15) and enrollment.tasks.filter(slug='not-eligible').count() == 0:
                task = 'Your email address does not match our records. If you think this is an error please reach out to the email address provided. Otherwise, click here to uninstall the extension.'

                final_url = 'https://survey.example.com/?webmunk_id=%s' % enrollment.assigned_identifier

                ScheduledTask.objects.create(enrollment=enrollment, active=enrollment.enrolled, task=task, slug='not-eligible', url=final_url)

# This function is responsible for assigning new participants to a new extension 
# rule set that immplements a specific experimental condition.

def WEBMUNK_ASSIGN_RULES(found_enrollment, ExtensionRuleSet):
    if found_enrollment.rule_set is not None:
        return

    current_rulesets = [
        21, # Main Study (Amazon Treatment, Hide, Server 3)
        22, # Main Study (Control, No Hide or Highlight, Server 3)
        23, # Main Study (Random Treatment, Random Hide, Server 3)
    ]

    list_pk = random.choice(current_rulesets)

    selected_rules = ExtensionRuleSet.objects.filter(pk=list_pk).first()

    if selected_rules is not None:
        found_enrollment.rule_set = selected_rules
        found_enrollment.save()

# Used by the Webmunk Amazon study to also log visits to other e-commerce destinations.
# This information was passed along to the extension as its configuration that instructed
# the extension to listen for visits to these domains.
        
WEBMUNK_LOG_DOMAINS = (
    'anthropologie.com',
    'apple.com',
    'barnesandnoble.com',
    'bathandbodyworks.com',
    ...
    'zulily.com',
    'shop.app',
)

# Used by the Webmunk Amazon study to identify Amazon-affiliated brands on the site for 
# distinguishing between first- and third-party goods in the gathered dataset.

WEBMUNK_TARGETED_BRANDS = (
    'Amazon Aware',
    'Amazon Basic Care',
    ...
    # 'Strathwood',
    # 'Care Of By Puma',
)

# This function modified a configuration to be sent to the web browser extension before
# transmission to add new rules that would set up listeners for e-commerce sites specified
# in WEBMUNK_LOG_DOMAINS and to tag Amazon-affiliated brands with the webmunk-targeted-brand
# CSS class in the data.

def WEBMUNK_UPDATE_ALL_RULE_SETS(payload):
    if ('log-elements' in payload['rules']) is False:
        payload['rules']['log-elements'] = []

    for domain in WEBMUNK_LOG_DOMAINS:
        domain_rule = {
            'filters': {
                'hostEquals': domain,
                'hostSuffix': '.%s' % domain
            },
            'load': ['title'],
            'leave': ['title']
        }

        payload['rules']['log-elements'].append(domain_rule)

    payload['rules']['rules'].insert(0, {
        'match': '.webmunk-targeted-brand .webmunk-targeted-brand',
        'remove-class': 'webmunk-targeted-brand'
    })

    brands = []

    for brand in WEBMUNK_TARGETED_BRANDS:
        brands.append(brand)

    brand_rule = {
        'add-class': 'webmunk-targeted-brand',
        'match': '.s-result-item:has(*:webmunkContainsInsensitiveAny(%s)):visible' % json.dumps(brands)
    }

    payload['rules']['rules'].insert(0, brand_rule)

    brand_rule = {
        'add-class': 'webmunk-targeted-brand',
        'match': '.s-result-item:has(*:webmunkContainsInsensitiveAny(%s)):visible' % json.dumps(brands)
    }

    payload['rules']['rules'].insert(0, brand_rule)

    brand_rule = {
        'add-class': 'webmunk-targeted-brand',
        'match': '.s-inner-result-item:has(*:webmunkContainsInsensitiveAny(%s)):visible' % json.dumps(brands)
    }

    payload['rules']['rules'].insert(0, brand_rule)

    brand_rule = {
        'add-class': 'webmunk-targeted-brand',
        'match': '.a-carousel-card:not(:has([data-video-url])):visible:has(*:webmunkContainsInsensitiveAny(%s))' % json.dumps(brands)
    }

    payload['rules']['rules'].insert(0, brand_rule)

    brand_rule = {
        'remove-class': 'webmunk-targeted-brand',
        'match': '.a-carousel-card:not(:has([data-video-url])):visible:not(:has(*:webmunkContainsInsensitiveAny(%s)))' % json.dumps(brands)
    }

    payload['rules']['rules'].insert(0, brand_rule)

    brand_rule = {
        'add-class': 'webmunk-targeted-brand',
        'match': '#value-pick-ac:has(*:webmunkContainsInsensitiveAny(%s)):not(:has([data-video-url])):visible' % json.dumps(brands)
    }

    payload['rules']['rules'].insert(0, brand_rule)

    brand_rule = {
        'add-class': 'webmunk-targeted-brand',
        'match': '.webmunk-asin-item:visible:has(*:webmunkContainsInsensitiveAny(%s))' % json.dumps(brands)
    }

    payload['rules']['rules'].insert(0, brand_rule)

    brand_rule = {
        'add-class': 'webmunk-targeted-brand',
        'match': '.webmunk-asin-item:visible:has(*:webmunkImageAltTagContainsInsensitiveAny(%s))' % json.dumps(brands)
    }

    payload['rules']['rules'].insert(0, brand_rule)

# This function implements custom logic to determine whether a task has been completed
# on a periodic basis. This is required for asynchronous interactions where a participant
# may be interacting with other resources. This implementation inspects whether the 
# participant uploaded their Amazon data to the data collection server.

def WEBMUNK_CHECK_TASK_COMPLETE(task):
    if task.slug in ('upload-amazon-start', 'upload-amazon-final'):
        pdk_ed_url  = 'https://pilot.webmunk.org/data/external/uploads/%s.json' % task.enrollment.assigned_identifier

        amazon_divider = task.enrollment.enrolled + datetime.timedelta(days=WEBMUNK_DATA_FOLLOWUP_DAYS)

        try:
            response = requests.get(pdk_ed_url)

            if response.status_code == 200:
                uploaded_items = response.json()

                for item in uploaded_items:
                    if item['source'] == 'amazon':
                        item_upload = arrow.get(item['uploaded']).datetime

                        if task.slug == 'upload-amazon-start' and item_upload < amazon_divider:
                            return True

                        if task.slug == 'upload-amazon-final' and item_upload > amazon_divider:
                            task.completed = item_upload

                            incomplete_amazon = task.enrollment.tasks.filter(slug='upload-amazon-start', completed=None).first()

                            if incomplete_amazon is not None:
                                incomplete_amazon.completed = timezone.now()

                                metadata = {}

                                if incomplete_amazon.metadata is not None and incomplete_amazon.metadata != '':
                                    metadata = json.loads(incomplete_amazon.metadata)

                                    metadata['summary'] = 'Did not upload first history file'

                                    incomplete_amazon.metadata = json.dumps(metadata, indent=2)

                                    incomplete_amazon.save()

                            return True
            else:
                print('RESP[%s]: %s -- %d' % (task.enrollment.assigned_identifier, pdk_ed_url, response.status_code))
        except requests.exceptions.ConnectionError:
            print('RESP[%s]: %s -- Unable to connect' % (task.enrollment.assigned_identifier, pdk_ed_url))

    return False

# The fields below allowed the enrollment server to check survey completions using the Qualtrics
# API.

WEBMUNK_QUALTRICS_API_TOKEN = 'CHANGEME'
WEBMUNK_QUALTRICS_BASE_URL = 'https://example.qualtrics.com'
WEBMUNK_QUALTRICS_SURVEY_IDS = (
    ('SURVEY_KEY', 'task-slug', 'https://example.qualtrics.com', 'QUALTRICS_API_KEY'),
    ('SURVEY_KEY', 'task-slug', 'https://example.qualtrics.com', 'QUALTRICS_API_KEY'),
)

WEBMUNK_QUALTRICS_ELIGIBILITY_SURVEY_IDS = (
    ('SURVEY_KEY', 'task-slug', 'https://example.qualtrics.com', 'QUALTRICS_API_KEY'),
)

WEBMUNK_QUALTRICS_WISHLIST_SURVEY_IDS = (
    ('SURVEY_KEY', 'task-slug', 'https://example.qualtrics.com', 'QUALTRICS_API_KEY'),
)

WEBMUNK_QUALTRICS_EXPORT_SURVEY_IDS = (
    ('SURVEY_KEY', 'task-slug', 'https://example.qualtrics.com', 'QUALTRICS_API_KEY'),
)
