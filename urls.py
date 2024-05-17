# pylint: disable=line-too-long, wrong-import-position

import sys

if sys.version_info[0] > 2:
    from django.urls import re_path as url # pylint: disable=no-name-in-module
else:
    from django.conf.urls import url

from .views import enroll, uninstall, enrollments, unsubscribe_reminders, enrollments_txt, \
                   update_group, privacy, amazon_fetched, mark_eligible, enrollment_upload_rewards, \
                   enrollments_rewards_json, enrollments_purchases_json, create_asin_lookup

urlpatterns = [
    url(r'^enroll.json$', enroll, name='enroll'),
    url(r'^uninstall$', uninstall, name='uninstall'),
    url(r'^privacy$', privacy, name='privacy'),
    url(r'^unsubscribe/(?P<identifier>.+)$', unsubscribe_reminders, name='unsubscribe_reminders'),
    url(r'^enrollments$', enrollments, name='enrollments'),
    url(r'^update_group.json$', update_group, name='update_group'),
    url(r'^amazon-fetched.json$', amazon_fetched, name='amazon_fetched'),
    url(r'^enrollments.txt$', enrollments_txt, name='enrollments_txt'),
    url(r'^thanks$', mark_eligible, name='mark_eligible'),
    url(r'^upload-rewards$', enrollment_upload_rewards, name='enrollment_upload_rewards'),
    url(r'^rewards.json$', enrollments_rewards_json, name='enrollments_rewards_json'),
    url(r'^purchases.json$', enrollments_purchases_json, name='enrollments_purchases_json'),
    url(r'^asin-lookup$', create_asin_lookup, name='create_asin_lookup'),
]
