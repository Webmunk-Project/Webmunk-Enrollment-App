# -*- coding: utf-8 -*-
# pylint: disable=no-member,line-too-long

import datetime
import logging
import json
import time
import traceback

import keepa
import numpy
import pandas
import requests

from django.conf import settings
from django.core.management.base import BaseCommand

from ...models import AmazonPurchase

class NumpyEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, numpy.ndarray):
            return o.tolist()

        if isinstance(o, datetime.datetime):
            return o.isoformat()

        if isinstance(o, pandas.DataFrame):
            json_str = o.to_json()

            return json.loads(json_str)

        return json.JSONEncoder.default(self, o)

class Command(BaseCommand):
    help = 'Populates Amazon ASIN item metadata using Keepa API'

    def add_arguments(self, parser):
        pass

    def handle(self, *args, **options): # pylint: disable=too-many-branches, too-many-locals, too-many-statements
        verbosity = options.get('verbosity', 0)

        if verbosity == 0:
            level = logging.ERROR
        elif verbosity == 1:
            level = logging.WARN
        elif verbosity == 2:
            level = logging.INFO
        else:
            level = logging.DEBUG

        loggers = [logging.getLogger(name) for name in ('keepa.interface', 'keepa')]

        keepa_cache = {}

        for logger in loggers:
            logger.setLevel(level)

        api = keepa.Keepa(settings.KEEPA_API_KEY)

        for amazon_product in AmazonPurchase.objects.filter(metadata=None).order_by('enrollment__enrolled', 'purchase_date', 'item_name'): # pylint: disable=too-many-nested-blocks
            if len(amazon_product.asin()) <= 10:
                try:
                    products = keepa_cache.get(amazon_product.asin(), None)

                    if products is None:
                        for faux_keepa_api_url in settings.FAUX_KEEPA_API_URLS:
                            product_url = '%s%s.json' % (faux_keepa_api_url, amazon_product.asin())

                            response = requests.get(product_url, timeout=300)

                            if response.status_code == 200:
                                response_json = response.json()

                                cached_keepa = response_json.get('keepa', [])

                                if cached_keepa != 'Null item' and len(cached_keepa) > 0:
                                    first_keepa = cached_keepa[0]

                                    try:
                                        if first_keepa.get('title', None) is not None and first_keepa.get('categoryTree', None) is not None:
                                            keepa_cache[amazon_product.asin()] = cached_keepa

                                            products = cached_keepa

                                            break
                                    except AttributeError:
                                        traceback.print_exc()
                                        print('%s[%s]: GOT %s' % (amazon_product.item_name, amazon_product.asin(), first_keepa))

                    if products is None:
                        time.sleep(settings.KEEPA_API_SLEEP_SECONDS)

                        products = api.query(amazon_product.asin(), progress_bar=False)

                        if products != 'Null item' and len(products) > 0:
                            print('KEEPA[%s]: %s - %s' % (amazon_product.asin(), amazon_product.item_name, products[0].get('categoryTree', [])))

                            keepa_cache[amazon_product.asin()] = products

                    if products is not None and len(products) > 0 and products[0] is not None:
                        product = products[0]

                        if product['title'] is not None:
                            category = ''

                            if product.get('categoryTree', None) is not None:
                                for category_item in product.get('categoryTree', []):
                                    if category != '':
                                        category = category + ' > '

                                    category = category + category_item['name']

                                amazon_product.item_type = category

                            amazon_product.metadata = json.dumps(product, indent=2, cls=NumpyEncoder)
                            amazon_product.save()

                            print('[%s / %s / %s] %s -- %s' % (amazon_product.enrollment, amazon_product.asin(), amazon_product.enrollment.enrolled, amazon_product.item_name, amazon_product.item_type))
                        else:
                            print('NULL ITEM: %s - %s' % (amazon_product.asin(), amazon_product.item_name))

                            amazon_product.item_type = 'null'
                            amazon_product.metadata = 'null'
                            amazon_product.save()
                    else:
                        print('NOT FOUND: %s - %s' % (amazon_product.asin(), amazon_product.item_name))
                        # amazon_product.item_type = 'not-found'
                        # amazon_product.save()
                except: # pylint: disable=bare-except
                    traceback.print_exc()
                    print('Invalid identifier: %s - %s' % (amazon_product.asin(), amazon_product.item_name))
                    # amazon_product.item_type = 'invalid'
                    # amazon_product.save()
