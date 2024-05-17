# -*- coding: utf-8 -*-
# pylint: disable=no-member,line-too-long

import json

from django.core.management.base import BaseCommand

from ...models import AmazonASINItem

class Command(BaseCommand):
    help = 'Resets corrected Keepa titles'

    def add_arguments(self, parser):
        pass

    def handle(self, *args, **options): # pylint: disable=too-many-locals, too-many-branches, too-many-statements
        for asin_item_pk in AmazonASINItem.objects.filter(item_name__icontains=' (').order_by('pk').values_list('pk', flat=True):
            asin_item = AmazonASINItem.objects.get(pk=asin_item_pk)

            if asin_item.keepa_response is not None:
                keepa_response = json.loads(asin_item.keepa_response)

                keepa_title = keepa_response.get('title', None)

                if keepa_title is not None:
                    type_str = ' (%s)' % asin_item.fetch_item_type()

                    if keepa_title.endswith(type_str):
                        keepa_response['title'] = None

                        print('Reset %s -- %s' % (asin_item.asin, keepa_title))

                        asin_item.keepa_response = json.dumps(keepa_response, indent=2)
                        asin_item.save()
