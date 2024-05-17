# -*- coding: utf-8 -*-
# pylint: disable=no-member,line-too-long

import io
import json
import time
import zipfile

import keepa
import requests

from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone


from ...models import NumpyEncoder

class Command(BaseCommand):
    help = 'Command for fetching data from Keepa and printing to command line.'

    def add_arguments(self, parser):
        parser.add_argument('asin', type=str)

    def handle(self, *args, **options): # pylint: disable=too-many-locals, too-many-branches, too-many-statements
        api = keepa.Keepa(settings.KEEPA_API_KEY)

        products = api.query(options['asin'], progress_bar=False, buybox=True)

        # logging.debug('%s: %s', self.asin, json.dumps(products, indent=2, cls=NumpyEncoder))

        product = None

        if len(products) > 0 and products[0] is not None:
            product = products[0]

        print(json.dumps(product, indent=2, cls=NumpyEncoder))
