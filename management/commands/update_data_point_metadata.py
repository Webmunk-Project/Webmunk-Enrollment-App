# -*- coding: utf-8 -*-
# pylint: disable=no-member,line-too-long

import json
import logging

import arrow

from django.conf import settings
from django.core.management.base import BaseCommand

from quicksilver.decorators import handle_lock, handle_schedule, add_qs_arguments

from ...vendor.pdk_client import PDKClient, PDKClientTimeout, PDKClientServerError

from ...models import Enrollment

class Command(BaseCommand):
    help = 'Adds relevent data point metadata to enrollments.'

    @add_qs_arguments
    def add_arguments(self, parser):
        pass

    @handle_lock
    @handle_schedule
    def handle(self, *args, **options): # pylint: disable=too-many-locals, too-many-branches
        for url in settings.PDK_API_URLS: # pylint: disable=too-many-nested-blocks
            client = PDKClient(site_url=url, token=settings.PDK_API_TOKEN)

            for enrollment in Enrollment.objects.all().order_by('assigned_identifier'):
                try:
                    metadata = json.loads(enrollment.metadata)

                    data_url = metadata.get('data_point_server', 'no-server')
                    skip_count = metadata.get('data_point_server_skip_count', False)

                    if skip_count is False and (data_url.startswith(url) or data_url == 'no-server'):
                        logging.info('SYNC[%s] %s', enrollment, data_url)

                        last_latest = arrow.get(metadata.get('latest_data_point', 0)).datetime

                        query = client.query_data_points(page_size=32)

                        last_points = query.filter(source=enrollment.assigned_identifier, created__gt=last_latest)

                        last_point = last_points.order_by('-created').first()

                        if last_point is not None:
                            created = last_point.get('passive-data-metadata', {}).get('pdk_server_created', None)

                            if created is not None:
                                metadata['latest_data_point'] = created

                                point_count = query.filter(source=enrollment.assigned_identifier).count()

                                metadata['data_point_count'] = point_count
                                metadata['data_point_server'] = url

                                logging.debug('%s - %s (%s)', enrollment.assigned_identifier, point_count, url)

                                enrollment.metadata = json.dumps(metadata, indent=2)
                                enrollment.save()
                except PDKClientTimeout:
                    logging.error('Server (%s) time out: %s', url, enrollment.assigned_identifier)
                except PDKClientServerError:
                    logging.error('Server error (%s): %s', url, enrollment.assigned_identifier)
