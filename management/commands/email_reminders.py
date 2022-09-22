# pylint: disable=no-member,line-too-long

from __future__ import print_function

import datetime
import json

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

        distant_future = now + datetime.timedelta(days=(100 * 365))

        for enrollment in Enrollment.objects.exclude(contact_after__gte=timezone.now()): # pylint: disable=too-many-nested-blocks
            raw_identifier = enrollment.current_raw_identifier()

            if '@' in raw_identifier:
                days_enrolled = (now - enrollment.enrolled).days

                if days_enrolled >= settings.WEBMUNK_STUDY_DAYS:
                    if (now - enrollment.last_fetched).days < 2:
                        request_email_subject = render_to_string('reminders/email_complete_subject.txt')
                        request_email_txt = render_to_string('reminders/email_complete_body.txt')

                        context = {
                            'settings': settings
                        }

                        request_email_html = render_to_string('reminders/email_complete_body_html.txt', context=context)

                        message = EmailMultiAlternatives(request_email_subject, request_email_txt, settings.AUTOMATED_EMAIL_FROM_ADDRESS, [raw_identifier])
                        message.attach_alternative(request_email_html, 'text/html')
                        message.send()

                        enrollment.contact_after = distant_future
                        enrollment.save()
                else:
                    tasks = enrollment.tasks.filter(completed=None, active__lte=now).order_by('active', 'task')

                    if tasks.count() > 0:
                        context = {
                            'identifier': enrollment.assigned_identifier,
                            'tasks': [],
                            'unsubscribe': '%s%s' % (settings.SITE_URL, reverse('unsubscribe_reminders', args=[enrollment.assigned_identifier]))
                        }

                        for task in tasks:
                            task_url = task.url

                            headers = {'Authorization': 'Bearer ' + settings.BITLY_ACCESS_CODE}

                            post_data = {'long_url': task.url}

                            fetch_url = 'https://api-ssl.bitly.com/v4/shorten'

                            fetch_request = requests.post(fetch_url, headers=headers, json=post_data, timeout=300)

                            if fetch_request.status_code >= 200 and fetch_request.status_code < 300:
                                task_url = fetch_request.json()['link']

                            if task.slug == 'upload-amazon-final':
                                task.task = 'Update your Amazon order history'
                                task.save()

                            context['tasks'].append({
                                'slug': task.slug,
                                'name': task.task,
                                'url': task_url
                            })

                        request_email_subject = render_to_string('reminders/email_reminder_subject.txt', context=context)
                        request_email = render_to_string('reminders/email_reminder_body.txt', context=context)

                        send_mail(request_email_subject, request_email, settings.AUTOMATED_EMAIL_FROM_ADDRESS, [raw_identifier], fail_silently=False)

                        enrollment.contact_after = timezone.now() + datetime.timedelta(days=settings.WEBMUNK_REMINDER_DAYS_INTERVAL)
                        enrollment.save()

                        print('Sent task reminder to %s (%d tasks): %s' % (enrollment.assigned_identifier, tasks.count(), json.dumps(context['tasks'], indent=2)))
