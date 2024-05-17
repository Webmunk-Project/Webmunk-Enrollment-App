# -*- coding: utf-8 -*-
# pylint: disable=no-member,line-too-long

import io
import json
import time
import zipfile

import arrow
import requests

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db.models import Q
from django.db.utils import IntegrityError
from django.utils import timezone

from quicksilver.decorators import handle_lock, handle_schedule, add_qs_arguments

from ...models import ScheduledTask, Enrollment

class Command(BaseCommand):
    help = 'Verifies whether scheduled Qualtrics surveys have been completed'

    @add_qs_arguments
    def add_arguments(self, parser):
        pass

    @handle_lock
    @handle_schedule
    def handle(self, *args, **options): # pylint: disable=too-many-locals, too-many-branches, too-many-statements
        now = timezone.now()

        # start_final_window = now - datetime.timedelta(days=70)
        # end_final_window = now - datetime.timedelta(days=42)

        # for enrollment in Enrollment.objects.filter(enrolled__lt=end_final_window):
        #    if ScheduledTask.objects.filter(enrollment=enrollment, slug='qualtrics-final').count() == 0:
        #        final_url = 'https://hbs.qualtrics.com/jfe/form/SV_6mObnu4EcTzvE0K?webmunk_id=%s' % enrollment.assigned_identifier
        #
        #        ScheduledTask.objects.create(enrollment=enrollment, active=now, task='Complete final survey', slug='qualtrics-final', url=final_url)

        query = Q(completed=None, active__lte=now)

        query = query & (Q(slug__startswith='qualtrics') | Q(slug='wishlist-task'))

        pending_tasks = ScheduledTask.objects.filter(query)
        pending_tasks.update(last_check=now)

        if pending_tasks.count() > 0: # pylint: disable=too-many-nested-blocks
            for survey_id in settings.WEBMUNK_QUALTRICS_SURVEY_IDS:
                start_url = '%s/API/v3/surveys/%s/export-responses' % (survey_id[2], survey_id[0])

                data = { 'format': 'json' }

                headers = {
                    'Content-type': 'application/json',
                    'Accept': 'text/plain',
                    'X-API-TOKEN':  survey_id[3]
                }

                response = requests.post(start_url, data=json.dumps(data), headers=headers, timeout=300)

                if response.status_code == 200:
                    response_json = response.json()

                    progress_id = response_json.get('result', {}).get('progressId', None)

                    if progress_id is not None:
                        progress_url = '%s/API/v3/surveys/%s/export-responses/%s' % (survey_id[2], survey_id[0], progress_id)

                        headers = {
                            'X-API-TOKEN':  survey_id[3]
                        }

                        status = 'inProgress'
                        file_id = None

                        while status == 'inProgress':
                            time.sleep(15)

                            progress_response = requests.get(progress_url, headers=headers, timeout=300)

                            if progress_response.status_code == 200:
                                progress_json = progress_response.json()

                                status = progress_json.get('result', {}).get('status', 'failed')
                                file_id = progress_json.get('result', {}).get('fileId', None)
                            else:
                                print('PROGRESS NON-200 HTTP CODE: %d -- %s' % (progress_response.status_code, progress_url))
                                status = '404'

                        if status == 'complete' and file_id is not None:
                            download_url = '%s/API/v3/surveys/%s/export-responses/%s/file' % (survey_id[2], survey_id[0], file_id)

                            headers = {
                                'X-API-TOKEN':  survey_id[3]
                            }

                            file_response = requests.get(download_url, headers=headers, timeout=300)

                            with io.BytesIO(file_response.content) as zip_in:
                                with zipfile.ZipFile(zip_in) as zip_file:
                                    for name in zip_file.namelist():
                                        if name.endswith('.json'):
                                            with zip_file.open(name) as export_file:
                                                response_file = json.load(export_file)

                                                for survey_response in response_file.get('responses', []): # pylint: disable=too-many-nested-blocks
                                                    if survey_response.get('values', {}).get('finished', 0) == 1:
                                                        webmunk_id = survey_response.get('values', {}).get('webmunk_id', None)

                                                        if webmunk_id is not None:
                                                            enrollment = Enrollment.objects.filter(assigned_identifier=webmunk_id).first()

                                                            if enrollment is not None:
                                                                recorded = survey_response.get('values', {}).get('recordedDate', None)

                                                                if recorded is not None:
                                                                    completed_date = arrow.get(recorded).datetime

                                                                    if enrollment.tasks.filter(slug=survey_id[1]).count() > 0:
                                                                        enrollment.tasks.filter(completed=None, active__lte=now, slug=survey_id[1]).update(completed=completed_date)

                                                                        enrollment.tasks.filter(completed__lt=completed_date, active__lte=now, slug=survey_id[1]).update(completed=completed_date)
                                                                    else:
                                                                        task_name = 'Qualtrics (%s)' % survey_id[1]

                                                                        try:
                                                                            ScheduledTask.objects.create(enrollment=enrollment, slug='qualtric-created-%s' % survey_id[1], task=task_name, completed=completed_date, active=now, last_check=now)
                                                                        except IntegrityError:
                                                                            print('Error: Task %s already exists for %s. Skipping.' % ('qualtric-created-%s' % survey_id[1], enrollment))
                else:
                    print('START NON-200 HTTP CODE: %d -- %s: %s' % (response.status_code, start_url, response.text))
