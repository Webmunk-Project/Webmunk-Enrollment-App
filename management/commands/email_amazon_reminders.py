# pylint: disable=no-member,line-too-long

from __future__ import print_function

import datetime
import json

import arrow
import requests

from django.conf import settings
from django.core.mail import send_mail, EmailMultiAlternatives
from django.core.management.base import BaseCommand
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone

from ...models import Enrollment

class Command(BaseCommand):
    help = 'Sends reminders to participants with outstanding tasks.'

    def add_arguments(self, parser):
        pass

    def handle(self, *args, **options): # pylint: disable=too-many-locals
        now = timezone.now()

        index = 0

        for enrollment in Enrollment.objects.exclude(contact_after__gte=now): # pylint: disable=too-many-nested-blocks
            raw_identifier = enrollment.current_raw_identifier()

            metadata = enrollment.fetch_metadata()

            payment_eligible = metadata.get('payment_eligible', False)

            # Check to see if we've received data within the last 7 days

            latest_data_point = metadata.get('latest_data_point', 0)

            latest_received = arrow.get(latest_data_point)

            delta_days = (now - latest_received.datetime).days

            if payment_eligible and '@' in raw_identifier and delta_days < 7:
                active_tasks = enrollment.tasks.filter(completed=None, active__lte=now).order_by('active', 'task')

                uninstall_task = active_tasks.filter(slug='uninstall-extension').first()

                final_upload = active_tasks.filter(slug='amazon-fetch-final').first()
                final_survey = active_tasks.filter(slug='main-survey-final').first()

                # print('%s: final_upload: %s, final_survey: %s' % (enrollment, final_upload, final_survey))

                if final_upload is not None or final_survey is not None:
                    context = {
                        'identifier': enrollment.assigned_identifier,
                        'tasks': [],
                        'unsubscribe': '%s%s' % (settings.SITE_URL, reverse('unsubscribe_reminders', args=[enrollment.assigned_identifier]))
                    }

                    request_email_subject = render_to_string('reminders/email_amazon_reminder_subject.txt', context=context)
                    request_email = render_to_string('reminders/email_amazon_reminder_body.txt', context=context)

                    print('SEND[%s / %s / %s]: %s' % (index, raw_identifier, enrollment.assigned_identifier, delta_days))

                    index += 1

                    send_mail(request_email_subject, request_email, settings.AUTOMATED_EMAIL_FROM_ADDRESS, [raw_identifier], fail_silently=False)

                    enrollment.contact_after = now + datetime.timedelta(days=7)
                    enrollment.save()
