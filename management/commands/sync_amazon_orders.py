# -*- coding: utf-8 -*-
# pylint: disable=no-member,line-too-long

import logging

import arrow

from django.conf import settings
from django.core.management.base import BaseCommand

from quicksilver.decorators import handle_lock, handle_schedule, add_qs_arguments, touch_lock

from ...models import Enrollment, AmazonPurchase
from ...vendor.pdk_client import PDKClient, PDKClientTimeout, PDKClientServerError

class Command(BaseCommand):
    help = 'Records Amazon item purchases to local database'

    @add_qs_arguments
    def add_arguments(self, parser):
        pass

    @handle_lock
    @handle_schedule
    def handle(self, *args, **options): # pylint: disable=too-many-locals, too-many-branches
        urls = list(settings.PDK_API_URLS)

        for url in urls: # pylint: disable=too-many-nested-blocks
            client = PDKClient(site_url=url, token=settings.PDK_API_TOKEN, max_retry_duration=120)

            for enrollment in Enrollment.objects.all().order_by('assigned_identifier'):
                try:
                    logging.info('FETCH[%s] %s', url, enrollment.assigned_identifier)

                    order_query = client.query_data_points(page_size=32, max_retry_duration=5).filter(generator_identifier='webmunk-amazon-order', source=enrollment.assigned_identifier)

                    logging.info('ORDERS[%s] %s - %s', url, enrollment.assigned_identifier, order_query.count())

                    for order in order_query:
                        order_date_str = order.get('order-date', None)

                        if order_date_str is not None:
                            ordered = arrow.get(order_date_str)

                            for item in order.get('items', []):
                                if AmazonPurchase.objects.filter(enrollment=enrollment, item_url=item.get('url', None), order_url=order.get('url', None)).first() is None:
                                    purchase = AmazonPurchase(enrollment=enrollment, item_url=item.get('url', None), order_url=order.get('url', None))

                                    purchase.item_name = item.get('title', None)
                                    purchase.purchase_date = ordered.datetime.date()

                                    purchase.save()
                except PDKClientTimeout:
                    pass
                except PDKClientServerError:
                    pass

                touch_lock(options)
