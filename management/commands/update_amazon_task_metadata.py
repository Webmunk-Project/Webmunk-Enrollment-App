# -*- coding: utf-8 -*-
# pylint: disable=no-member,line-too-long

import json
import logging

from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone

from quicksilver.decorators import handle_lock, handle_schedule, add_qs_arguments

from ...models import ScheduledTask
from ...vendor.pdk_client import PDKClient, PDKClientTimeout, PDKClientServerError

class Command(BaseCommand):
    help = 'Adds relevent metadata for Amazon tasks.'

    @add_qs_arguments
    def add_arguments(self, parser):
        parser.add_argument('--force', action='store_true')

    @handle_lock
    @handle_schedule
    def handle(self, *args, **options): # pylint: disable=too-many-locals, too-many-branches
        amazon_tasks = ScheduledTask.objects.filter(slug__icontains='amazon-fetch', active__lte=timezone.now()).order_by('-enrollment__assigned_identifier', 'slug')

        for task in amazon_tasks: # pylint: disable=too-many-nested-blocks
            logging.info('%s', task)

            try:
                metadata = json.loads(task.enrollment.metadata)

                data_url = metadata.get('data_point_server', None)

                if data_url is not None:
                    logging.info('%s[%s]: Fetching...', task.enrollment.assigned_identifier, data_url)

                    client = PDKClient(site_url=data_url, token=settings.PDK_API_TOKEN)

                    metadata = json.loads(task.metadata)

                    order_count = '%s_order_count' % task.slug

                    completed_slug = '%s_completed' % task.slug

                    if options.get('force', False) or (order_count in metadata) is False or metadata.get(completed_slug, False) is False:
                        query = client.query_data_points(page_size=32)

                        amazon_orders = []

                        if task.slug == 'amazon-fetch-initial':
                            amazon_orders = query.filter(generator_identifier='webmunk-amazon-order', source=task.enrollment.assigned_identifier, created__lte=task.enrollment.enrolled)
                        else:
                            amazon_orders = query.filter(generator_identifier='webmunk-amazon-order', source=task.enrollment.assigned_identifier, created__gte=task.enrollment.enrolled).order_by('-recorded')

                        seen_orders = []

                        logging.info('%s[%s]: %s found', task.enrollment.assigned_identifier, task.slug, amazon_orders.count())

                        for order in amazon_orders:
                            order_number = order.get('order-number', None)

                            if order_number is not None and (order_number in seen_orders) is False:
                                seen_orders.append(order_number)

                        if len(seen_orders) > 0:
                            metadata[order_count] = len(seen_orders)
                            metadata['%s_summary' % task.slug] = '%d orders(s)' % metadata[order_count]
                            metadata['%s_completed' % task.slug] = (task.completed is not None)

                            task.metadata = json.dumps(metadata, indent=2)
                            task.save()

                    query = client.query_data_points(page_size=32)

                    amazon_order_counts = query.filter(generator_identifier='webmunk-amazon-order-count', source=task.enrollment.assigned_identifier, created__gte=task.active).order_by('created')

                    enrollment_metadata = task.enrollment.fetch_metadata()

                    logging.info('%s[%s]: %s orders', task.enrollment.assigned_identifier, data_url, amazon_order_counts.count())

                    for order_count in amazon_order_counts:
                        period = order_count.get('period', None)
                        period_count = order_count.get('count', None)

                        order_key = '%s_order_count' % period

                        if period is not None and period_count is not None:
                            logging.info(' %s - %s', period, period_count)

                            enrollment_metadata[order_key] = period_count
                        else:
                            if order_key in enrollment_metadata:
                                del enrollment_metadata[order_key]

                    task.enrollment.metadata = json.dumps(enrollment_metadata, indent=2)
                    task.enrollment.save()
            except PDKClientTimeout:
                logging.info('Timeout. Skipping %s', task.enrollment.assigned_identifier)

            except PDKClientServerError:
                logging.info('Server error. Skipping %s', task.enrollment.assigned_identifier)


#                   if item_count > 0:
#                       pdk_ed_url  = 'https://pilot.webmunk.org/data/external/uploads/%s.json' % task.enrollment.assigned_identifier
#
#                       amazon_divider = task.enrollment.enrolled + datetime.timedelta(days=settings.WEBMUNK_DATA_FOLLOWUP_DAYS)
#
#                       try:
#                           response = requests.get(pdk_ed_url, timeout=300)
#
#                           if response.status_code == 200:
#                               uploaded_items = response.json()
#
#                               for item in uploaded_items:
#                                   if item['source'] == 'amazon':
#                                       item_upload = arrow.get(item['uploaded']).datetime
#
#                                       if task.slug == 'upload-amazon-start' and item_upload < amazon_divider:
#                                           task.completed = item_upload
#                                           break
#
#                                       if task.slug == 'upload-amazon-final' and item_upload > amazon_divider:
#                                           task.completed = item_upload
#
#                                           for amazon_task in amazon_tasks:
#                                               if amazon_task.enrollment == task.enrollment and amazon_task.slug == 'upload-amazon-start' and amazon_task.completed is None:
#                                                   amazon_task.completed = item_upload
#                                                   amazon_task.save()
#
#                                           break
#                           else:
#                               print('RESP[%s]: %s -- %d' % (task.enrollment.assigned_identifier, pdk_ed_url, response.status_code))
#                       except requests.exceptions.ConnectionError:
#                           print('RESP[%s]: %s -- Unable to connect' % (task.enrollment.assigned_identifier, pdk_ed_url))
