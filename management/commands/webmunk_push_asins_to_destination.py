# -*- coding: utf-8 -*-
# pylint: disable=no-member,line-too-long

import logging
import os

import boto3

from botocore.config import Config

from django.conf import settings
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

        for asin_item_pk in asin_items_pks:
            asin_item = AmazonASINItem.objects.get(pk=asin_item_pk)

            asin_item.populate()

            file_path = '%s/%s.json' % (asin_item.asin.replace('/', '_')[:4], asin_item.asin.replace('/', '_'))

            if file_path != '':
                upload_path = '%s/%s/%s' % ('asin_direct_uploads', settings.ALLOWED_HOSTS[0], file_path)

                if (asins_uploaded % 100) == 0:
                    logging.warning('Uploading %s (%s) [%s / %s / %s]...', upload_path, asin_item_pk, asins_uploaded, asins_total, timezone.now())

                aws_config = Config(
                    region_name=settings.SIMPLE_BACKUP_AWS_REGION,
                    retries={'max_attempts': 10, 'mode': 'standard'}
                )

                os.environ['AWS_ACCESS_KEY_ID'] = settings.SIMPLE_BACKUP_AWS_ACCESS_KEY_ID
                os.environ['AWS_SECRET_ACCESS_KEY'] = settings.SIMPLE_BACKUP_AWS_SECRET_ACCESS_KEY

                client = boto3.client('s3', config=aws_config)

                s3_bucket = 'webmunk-asin-files'

                client.put_object(Body=asin_item.keepa_response, Bucket=s3_bucket, Key=upload_path)

                asins_uploaded  += 1
            else:
                logging.warning('Skipping %s (%s). No content to upload.', asin_item.asin, asin_item_pk)
