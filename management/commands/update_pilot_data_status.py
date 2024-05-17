# -*- coding: utf-8 -*-
# pylint: disable=no-member,line-too-long

import json
import traceback

import arrow

from django.conf import settings
from django.core.management.base import BaseCommand

from quicksilver.decorators import handle_lock, handle_schedule, add_qs_arguments

from ...models import Enrollment
from ...vendor.pdk_client import PDKClient

class Command(BaseCommand):
    help = 'Synchronizes pending data count w/ pilot server'

    @add_qs_arguments
    def add_arguments(self, parser):
        pass

    @handle_lock
    @handle_schedule
    def handle(self, *args, **options): # pylint: disable=too-many-locals, too-many-branches
        client = PDKClient(site_url=settings.PDK_API_URL, token=settings.PDK_API_TOKEN)

        for enrollment in Enrollment.objects.all().order_by('assigned_identifier'):
            try:
                query = client.query_data_points(page_size=1).filter(generator_identifier='pdk-system-status', source=enrollment.assigned_identifier).order_by('-created')

                if query.count() > 0:
                    latest = query[0]

                    when = arrow.get(latest.get('passive-data-metadata', {}).get('pdk_server_created', 0))

                    point_count = latest.get('pending_points', -1)

                    if point_count != -1:
                        metadata = json.loads(enrollment.metadata)

                        metadata['latest_pending_points_count'] = point_count
                        metadata['latest_pending_points_updated'] = when.datetime.isoformat()

                        enrollment.metadata = json.dumps(metadata, indent=2)
                        enrollment.save()
            except:
                traceback.print_exc()
