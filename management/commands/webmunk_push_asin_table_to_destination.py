# -*- coding: utf-8 -*-
# pylint: disable=no-member,line-too-long

import logging
import csv
import io
import os
import tempfile

import boto3
import pytz

from botocore.config import Config

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils import timezone

from ...models import AmazonASINItem

class Command(BaseCommand):
    help = 'Populates Amazon ASIN item metadata'

    def add_arguments(self, parser):
        parser.add_argument('--start_pk', type=int)

    def handle(self, *args, **options): # pylint: disable=too-many-branches, too-many-locals, too-many-statements
        asin_items_pks = AmazonASINItem.objects.all().order_by('pk').values_list('pk', flat=True)

        asins_uploaded = 0
        asins_total = len(asin_items_pks)

        here_tz = pytz.timezone(settings.TIME_ZONE)

        data_filename = tempfile.gettempdir() + os.path.sep + 'enroll-full.txt'

        with io.open(data_filename, 'w', encoding='utf-8') as outfile:
            writer = csv.writer(outfile, delimiter='\t')

            columns = [
                'ASIN',
                'Type',
                'Brand',
                'Manufacturer',
                'Size',
                'Seller',
                'Title',
                'Root Category',
                'Category Tree',
                'Category Tree IDs',
                'Date Added',
                'Date Updated',
                'Data URL',
                'File Path',
            ]

            writer.writerow(columns)

            for asin_item_pk in asin_items_pks:
                asin_item = AmazonASINItem.objects.get(pk=asin_item_pk)

                asin_item.populate()

                row = []

                if (asins_uploaded % 100) == 0:
                    print('%s / %s' % (asins_uploaded, asins_total))

                row.append(asin_item.asin)

                row.append(asin_item.fetch_item_type())
                row.append(asin_item.fetch_brand())
                row.append(asin_item.fetch_manufacturer())
                row.append(asin_item.fetch_size())

                row.append(asin_item.fetch_seller())
                row.append(asin_item.fetch_title())
                row.append(asin_item.fetch_root_category())
                row.append(asin_item.fetch_category())
                row.append(asin_item.fetch_category_ids())

                added = asin_item.fetched.astimezone(here_tz)
                updated = asin_item.fetched.astimezone(here_tz)

                row.append(added.isoformat())
                row.append(updated.isoformat())

                row.append('') # https://%s%s' % (settings.ALLOWED_HOSTS[0], asin_item.get_absolute_url()))

                asin_path = '' # asin_item.file_path()

                row.append(asin_path)

                writer.writerow(row)

                asins_uploaded += 1

        aws_config = Config(
            region_name=settings.SIMPLE_BACKUP_AWS_REGION,
            retries={'max_attempts': 10, 'mode': 'standard'}
        )

        upload_path = 'manual-export/enroll-full.txt'

        os.environ['AWS_ACCESS_KEY_ID'] = settings.SIMPLE_BACKUP_AWS_ACCESS_KEY_ID
        os.environ['AWS_SECRET_ACCESS_KEY'] = settings.SIMPLE_BACKUP_AWS_SECRET_ACCESS_KEY

        client = boto3.client('s3', config=aws_config)

        s3_bucket = 'webmunk-asin-files'

        client.upload_file(Filename=data_filename, Bucket=s3_bucket, Key=upload_path)
